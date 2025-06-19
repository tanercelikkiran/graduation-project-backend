from src.models.vocabulary import VocabularyList
from .api import gemini_client
import logging
import time
from typing import List, Optional, Dict, Set
from pydantic import ValidationError
from google.genai import types

# Set up logging
logger = logging.getLogger(__name__)


def create_vocabulary_list(
    purpose: str,
    level: str,
    learning_language: str,
    system_language: str = "English",
    excluded_words: List[Dict[str, str]] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> VocabularyList:
    """
    Generate a vocabulary list for language learning.

    Args:
        purpose: The purpose for learning (e.g., "travel", "business")
        level: Proficiency level (e.g., "beginner", "intermediate", "advanced")
        learning_language: The target language being learned
        system_language: The user's native/system language for translations
        excluded_words: List of words to avoid suggesting (previously seen words)
        max_retries: Maximum number of retry attempts on failure
        retry_delay: Delay between retries in seconds

    Returns:
        VocabularyList: A list of vocabulary items with words, meanings, related words, and emojis

    Raises:
        ValueError: If input parameters are invalid
        Exception: If vocabulary generation fails after all retries
    """
    # Input validation
    if not purpose or not isinstance(purpose, str):
        raise ValueError("Purpose must be a non-empty string")
    if not level or not isinstance(level, str):
        raise ValueError("Level must be a non-empty string")
    if not learning_language or not isinstance(learning_language, str):
        raise ValueError("Learning language must be a non-empty string")
    if not system_language or not isinstance(system_language, str):
        raise ValueError("System language must be a non-empty string")

    # Initialize with empty string as default
    excluded_words_str = ""

    if excluded_words and len(excluded_words) > 0:
        # Extract words to avoid
        words_to_avoid = [
            item.get("word", "").strip().lower()
            for item in excluded_words
            if "word" in item
        ]
        word_roots_to_avoid = _extract_word_roots(words_to_avoid)

        if word_roots_to_avoid:
            # Convert set to list before slicing
            word_roots_list = list(word_roots_to_avoid)
            # Format the excluded words list for the prompt
            excluded_words_str = ", ".join(
                word_roots_list[:50]
            )  # Limit to 50 to avoid too long prompts

    # Modify the prompt template based on whether we have excluded words
    exclusion_text = (
        f"Avoid suggesting any of these words or their variations that the user has already seen: {excluded_words_str}. Generate completely different vocabulary."
        if excluded_words_str
        else ""
    )

    prompt = f"""
    **CRITICAL LANGUAGE REQUIREMENTS:**
    - ALL vocabulary words MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language for the words.
    - ALL meanings MUST be written EXCLUSIVELY in {system_language}. Do NOT use any other language for meanings.
    - ALL relevant words MUST be written EXCLUSIVELY in {system_language}. Do NOT use any other language for relevant words.
    - DO NOT mix languages within a single field. Each field must contain content in only one specified language.
    - Verify language accuracy: {learning_language} words must follow {learning_language} spelling, grammar, and vocabulary conventions.
    - Verify language accuracy: {system_language} translations must follow {system_language} spelling, grammar, and vocabulary conventions.
    
    Generate between 25 and 35 useful words for a {level} level learner studying {learning_language} for {purpose}.
    {exclusion_text}
    Each word should be relevant to the purpose and level specified.
    All texts should be lowercase. 
    Provide each word in the 'word' field (in {learning_language} ONLY), its meaning in the 'meaning' (in {system_language} ONLY) field, and exactly 5 related words (in {system_language} ONLY) under 'relevantWords'. 
    For each word, also provide one relevant emoji in the 'emoji' field that represents the word visually. Do not include example sentences. 
    Ensure all fields are properly filled for every word.
    Ensure that the vocabulary list is diverse and covers a range of topics related to the purpose.
    Ensure that meanings are clear and concise.
    Ensure that meanings are not sentences or contains any punctuation. Meanings should be a single word or a short phrase.
    
    **LANGUAGE COMPLIANCE CHECK:** Before finalizing your response, verify that:
    1. Every 'word' field contains text ONLY in {learning_language}
    2. Every 'meaning' field contains text ONLY in {system_language}
    3. Every 'relevantWords' field contains text ONLY in {system_language}
    4. No fields contain mixed languages or incorrect language usage
    """

    # Initialize retry counter and success flag
    retries = 0
    success = False
    last_error = None

    # Retry loop
    while retries < max_retries and not success:
        try:
            logger.info(
                f"Attempting vocabulary generation (attempt {retries+1}/{max_retries})"
            )

            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VocabularyList,
                ),
            )

            output = response.parsed

            # Validate the response structure and content
            if not output or not hasattr(output, "words") or not output.words:
                raise ValueError("API returned empty vocabulary list")

            # Ensure minimum word count
            if len(output.words) < 10:
                raise ValueError(
                    f"Insufficient words returned: {len(output.words)} (minimum 10 required)"
                )

            # Validate individual words
            for item in output.words:
                if (
                    not item.word
                    or not item.meaning
                    or not item.relevantWords
                    or len(item.relevantWords) != 5
                ):
                    logger.warning(f"Incomplete vocabulary item detected: {item}")
                    # Fix missing relevant words if needed
                    if not item.relevantWords or len(item.relevantWords) < 5:
                        item.relevantWords = _ensure_five_relevant_words(
                            item.relevantWords
                        )

            success = True
            logger.info(
                f"Successfully generated vocabulary list with {len(output.words)} words"
            )

        except ValidationError as e:
            logger.error(f"Pydantic validation error: {str(e)}")
            last_error = e
            retries += 1

        except ValueError as e:
            logger.error(f"Value error in vocabulary generation: {str(e)}")
            last_error = e
            retries += 1

        except Exception as e:
            logger.error(f"Error generating vocabulary: {str(e)}")
            last_error = e
            retries += 1

        # Only delay if we're going to retry
        if not success and retries < max_retries:
            # Exponential backoff
            sleep_time = retry_delay * (2 ** (retries - 1))
            logger.info(f"Retrying in {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

    # If we couldn't generate valid vocabulary after all retries
    if not success:
        logger.error("Failed to generate vocabulary list after all retries")
        # Instead of using fallback, raise an exception
        raise Exception(f"Failed to generate vocabulary list: {str(last_error)}")

    return output


def _ensure_five_relevant_words(relevant_words: Optional[List[str]]) -> List[str]:
    """Ensure there are exactly 5 relevant words"""
    if not relevant_words:
        relevant_words = []

    # If we have more than 5, trim the list
    if len(relevant_words) > 5:
        return relevant_words[:5]

    # If we have less than 5, add placeholders
    while len(relevant_words) < 5:
        relevant_words.append(f"related_word_{len(relevant_words)+1}")

    return relevant_words


def _extract_word_roots(words: List[str]) -> Set[str]:
    """
    Extract word roots to help identify similar word variations.
    This is a simplified implementation that could be improved with
    language-specific stemming algorithms.
    """
    roots = set()
    for word in words:
        if not word:
            continue

        # Basic stemming for common suffixes
        # Note: For a production application, use a proper stemming library
        # like nltk.stem or language-specific stemmers
        word = word.lower().strip()

        # Remove very common suffixes (this is a simplified approach)
        for suffix in ["ing", "ed", "s", "es", "er", "est", "ly"]:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                word = word[: -len(suffix)]
                break

        # Add both the original word and the simplified root
        roots.add(word)

    return roots
