from .api import gemini_client
from src.models.pyramid import (
    PyramidReplaceItem,
    PyramidShrinkItem,
    PyramidExpandItem,
    PyramidParaphItem,
)
import time
from typing import Optional, List
from google.genai import types


def expand_sentence(
    sentence: str,
    learning_language: str = "Turkish",
    system_language: str = "English",
    purpose: str = "General Knowledge",
    user_level: str = "A1",
    excluded_words: List[str] = None,
    max_retries: int = 3,
) -> Optional[PyramidExpandItem]:
    """Generate 3 alternative sentences by adding one element to the original sentence."""

    # Prepare excluded words section
    excluded_words_section = ""
    if excluded_words:
        excluded_words_str = ", ".join(excluded_words)
        excluded_words_section = f"""
**IMPORTANT - AVOID REPETITION:**
- DO NOT use any of these words that have been used in previous steps: {excluded_words_str}
- Generate completely different words/phrases that haven't been used before.
- Be creative and come up with fresh alternatives that avoid these previously used words.
"""

    prompt = f"""
**CRITICAL LANGUAGE REQUIREMENTS:**
- ALL generated sentences MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language for sentences.
- ALL added words/phrases MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language for added elements.
- ALL meanings/translations MUST be written EXCLUSIVELY in {system_language}. Do NOT use any other language for meanings.
- DO NOT mix languages within a single field. Each field must contain content in only one specified language.
- Verify language accuracy: {learning_language} content must follow {learning_language} spelling, grammar, and vocabulary conventions.
- Verify language accuracy: {system_language} translations must follow {system_language} spelling, grammar, and vocabulary conventions.
{excluded_words_section}
Task: Create three alternative sentences by adding exactly one word or phrase to the original sentence. Each alternative sentence:
- Must be grammatically correct and meaningful in {learning_language}.
- Must have a similar, but slightly different, meaning to the original sentence.
- Added word or phrase must be a single word or a short phrase.
- Result sentence difficulty should be appropriate for {user_level} level learners.
- Result sentences should be relevant to the purpose: {purpose}.
- The added word or phrase should be relevant to the context of the original sentence.
- The added element should not change the core meaning of the original sentence, but rather enhance or specify it.

For each alternative sentence, the following must be provided:
- Alternative sentence (in {learning_language})
- Added word or phrase (in {learning_language})
- Meaning of the alternative sentence (translation in {system_language})

In addition, the original sentence and its meaning must be given in {system_language}.

Note the following rules:
- Each alternative sentence must be unique in terms of the added word or phrase.
- The added element must be clearly stated.
- Translations must be correct and natural in {system_language}.

Format the output as a JSON object adhering to the structure defined by the `PyramidExpandItem` Pydantic model:

{{
  "initial_sentence": "original sentence (in {learning_language})",
  "initial_sentence_meaning": "meaning of original sentence (in {system_language})",
  "options": [
    {{
      "sentence": "alternative sentence 1 (in {learning_language})",
      "expand_word": "added word or phrase 1 (in {learning_language})",
      "meaning": "meaning of alternative sentence 1 (in {system_language})"
    }},
    {{
      "sentence": "alternative sentence 2 (in {learning_language})",
      "expand_word": "added word or phrase 2 (in {learning_language})",
      "meaning": "meaning of alternative sentence 2 (in {system_language})"
    }},
    {{
      "sentence": "alternative sentence 3 (in {learning_language})",
      "expand_word": "added word or phrase 3 (in {learning_language})",
      "meaning": "meaning of alternative sentence 3 (in {system_language})"
    }}
  ]
}}

Example:
If the original sentence is "She reads books" ({learning_language}, {system_language}), the output should be:


{{
  "initial_sentence": "She reads books",
  "initial_sentence_meaning": "O kitap okur",
  "options": [
    {{
      "sentence": "She often reads books",
      "expand_word": "often",
      "meaning": "O sık sık kitap okur"
    }},
    {{
      "sentence": "She reads interesting books",
      "expand_word": "interesting",
      "meaning": "O ilginç kitaplar okur"
    }},    {{
      "sentence": "She reads books in the evening",
      "expand_word": "in the evening",
      "meaning": "O akşamları kitap okur"
    }}
  ]
}}

Now, create three alternative sentences for the given sentence: "{sentence}"

**LANGUAGE COMPLIANCE CHECK:** Before finalizing your response, verify that:
1. Every sentence is written ONLY in {learning_language}
2. Every expand_word is written ONLY in {learning_language}
3. Every meaning is written ONLY in {system_language}
4. No fields contain mixed languages or incorrect language usage """

    retry_count = 0
    while retry_count < max_retries:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PyramidExpandItem,
                ),
            )
            return response.parsed
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(
                    f"Error in expand_sentence after {max_retries} attempts: {str(e)}"
                )
                return None
            time.sleep(1)


def shrink_sentence(
    sentence: str,
    learning_language: str = "Turkish",
    system_language: str = "English",
    user_level: str = "A1 - Beginner",
    purpose: str = "General Knowledge",
    excluded_words: List[str] = None,
    max_retries: int = 3,
) -> Optional[PyramidShrinkItem]:
    """Generate 3 alternative sentences by removing one element from the original sentence."""

    # Prepare excluded words section
    excluded_words_section = ""
    if excluded_words:
        excluded_words_str = ", ".join(excluded_words)
        excluded_words_section = f"""
**IMPORTANT - AVOID REPETITION:**
- DO NOT remove any of these words that have been used in previous steps: {excluded_words_str}
- Generate completely different words/phrases for removal that haven't been used before.
- Be creative and come up with fresh alternatives that avoid these previously used words.
"""

    prompt = f"""
**CRITICAL LANGUAGE REQUIREMENTS:**
- ALL generated sentences MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language for sentences.
- ALL removed words/phrases MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language for removed elements.
- ALL meanings/translations MUST be written EXCLUSIVELY in {system_language}. Do NOT use any other language for meanings.
- DO NOT mix languages within a single field. Each field must contain content in only one specified language.
- Verify language accuracy: {learning_language} content must follow {learning_language} spelling, grammar, and vocabulary conventions.
- Verify language accuracy: {system_language} translations must follow {system_language} spelling, grammar, and vocabulary conventions.
{excluded_words_section}
Task: Create three alternative sentences by removing exactly one word or phrase from the original sentence. Each alternative sentence:
- Must be grammatically correct and meaningful in {learning_language}.
- Must maintain proper grammatical structure after word removal (subject-verb agreement, correct tenses, proper syntax).
- Must be semantically coherent and make logical sense in the target language.
- Must have a similar, but slightly different, meaning to the original sentence.
- Shrinked word or phrase must be a single word or a short phrase.
- Result sentence difficulty should be appropriate for {user_level} level learners.
- Result sentences should be relevant to the purpose: {purpose}.
- Each shortened sentence must preserve the core grammatical integrity of the original sentence.

For each alternative sentence, the following must be provided:
- Alternative sentence (in {learning_language})
- Omitted word or phrase (in {learning_language})
- Meaning of the alternative sentence (translation in {system_language})

In addition, the original sentence and its meaning must be given in {system_language}.

Note the following rules:
- Each alternative sentence must be unique in terms of the omitted word or phrase.
- The omitted element must be clearly stated.
- Translations must be correct and natural in {system_language}.

Format the output as a JSON object strictly following this structure, which aligns with the provided Pydantic models:
{{
  "initial_sentence": "...", // original sentence (in {learning_language})
  "initial_sentence_meaning": "...", // meaning of original sentence (in {system_language})
  "options": [ // a list of three alternative sentences
    {{
      "sentence": "...", // alternative sentence (in {learning_language})
      "removed_word": "...", // removed word or phrase (in {learning_language})
      "meaning": "..." // meaning of alternative sentence (in {system_language})
    }},
    {{
      "sentence": "...",
      "removed_word": "...",
      "meaning": "..."
    }},
    {{
      "sentence": "...",
      "removed_word": "...",
      "meaning": "..."
    }}
  ]
}}

Example:
If the original sentence is "I go to school by bus every day" ({learning_language} = English, {system_language} = English), the output should be:
{{
  "initial_sentence": "I go to school by bus every day",
  "initial_sentence_meaning": "I go to school by bus every day",
  "options": [
    {{
      "sentence": "I go to school by bus",
      "removed_word": "every day",
      "meaning": "I go to school by bus"
    }},
    {{
      "sentence": "I go to school every day",
      "removed_word": "by bus",
      "meaning": "I go to school every day"
    }},
    {{
      "sentence": "I go by bus every day",
      "removed_word": "to school",      "meaning": "I go by bus every day"
    }}
  ]
}}

Now, create three alternative sentences for the given sentence: "{sentence}"

**LANGUAGE COMPLIANCE CHECK:** Before finalizing your response, verify that:
1. Every sentence is written ONLY in {learning_language}
2. Every removed_word is written ONLY in {learning_language}
3. Every meaning is written ONLY in {system_language}
4. No fields contain mixed languages or incorrect language usage """

    retry_count = 0
    while retry_count < max_retries:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PyramidShrinkItem,
                ),
            )
            return response.parsed

        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(
                    f"Error in shrink_sentence after {max_retries} attempts: {str(e)}"
                )
                return None
            time.sleep(1)  # Wait before retrying


def replace_word(
    sentence: str,
    learning_language: str = "Turkish",
    system_language: str = "English",
    user_level: str = "A1 - Beginner",
    purpose: str = "General Knowledge",
    excluded_words: List[str] = None,
    max_retries: int = 3,
) -> Optional[PyramidReplaceItem]:
    """Generate 3 alternative sentences by replacing one element in the original sentence."""

    # Prepare excluded words section
    excluded_words_section = ""
    if excluded_words:
        excluded_words_str = ", ".join(excluded_words)
        excluded_words_section = f"""
**IMPORTANT - AVOID REPETITION:**
- DO NOT use any of these words that have been used in previous steps: {excluded_words_str}
- Generate completely different words for replacement that haven't been used before.
- Be creative and come up with fresh alternatives that avoid these previously used words.
"""

    prompt = f"""
**CRITICAL LANGUAGE REQUIREMENTS:**
- ALL generated sentences MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language for sentences.
- ALL replaced words and new words MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language for word replacements.
- ALL meanings/translations MUST be written EXCLUSIVELY in {system_language}. Do NOT use any other language for meanings.
- DO NOT mix languages within a single field. Each field must contain content in only one specified language.
- Verify language accuracy: {learning_language} content must follow {learning_language} spelling, grammar, and vocabulary conventions.
- Verify language accuracy: {system_language} translations must follow {system_language} spelling, grammar, and vocabulary conventions.
{excluded_words_section}
Task: Create three alternative sentences by replacing exactly one word in the original sentence with a new word. Each alternative sentence:
- Must be grammatically correct and semantically meaningful in {learning_language}.
- Must have a different meaning compared to the original sentence due to the replacement.
- Replaced word or phrase must be a single word or a short phrase.
- Result sentence difficulty should be appropriate for {user_level} level learners.
- Result sentences should be relevant to the purpose: {purpose}.

For each alternative sentence, the following must be provided:
- The alternative sentence (in {learning_language}).
- The word from the original sentence that was replaced (in {learning_language}).
- The new word used for replacement (in {learning_language}).
- The meaning of the alternative sentence (translation in {system_language}).

In addition, the original sentence and its meaning must be given in {system_language}.

Note the following rules:
- Each alternative sentence must be unique in terms of the word being replaced or the new word used for replacement.
- The replaced word and the new word must be clearly stated.
- Translations must be correct and natural in {system_language}.
- The replacement should be a single word for a single word.

Format the output as a JSON object with the following structure, aligning with the PyramidReplaceItem and PyramidReplaceOptions Pydantic models:
{{
  "initial_sentence": "original sentence (in {learning_language})",
  "initial_sentence_meaning": "meaning of original sentence (in {system_language})",
  "options": [
    {{
      "sentence": "alternative sentence 1 (in {learning_language})",
      "replaced_word": "original word replaced 1 (in {learning_language})",
      "changed_word": "new word used 1 (in {learning_language})",
      "meaning": "meaning of alternative sentence 1 (in {system_language})"
    }},
    {{
      "sentence": "alternative sentence 2 (in {learning_language})",
      "replaced_word": "original word replaced 2 (in {learning_language})",
      "changed_word": "new word used 2 (in {learning_language})",
      "meaning": "meaning of alternative sentence 2 (in {system_language})"
    }},
    {{
      "sentence": "alternative sentence 3 (in {learning_language})",
      "replaced_word": "original word replaced 3 (in {learning_language})",
      "changed_word": "new word used 3 (in {learning_language})",
      "meaning": "meaning of alternative sentence 3 (in {system_language})"
    }}
  ]
}}

Example:
If the original sentence is "I go to school by bus every day" ({learning_language} = English), the output would be as follows:
{{
  "initial_sentence": "I go to school by bus every day",
  "initial_sentence_meaning": "I go to school by bus every day",
  "options": [
    {{
      "sentence": "I go to park by bus every day",
      "replaced_word": "school",
      "changed_word": "park",
      "meaning": "I go to the park by bus every day"
    }},
    {{
      "sentence": "We go to school by bus every day",
      "replaced_word": "I",
      "changed_word": "We",
      "meaning": "We go to school by bus every day"
    }},
    {{
      "sentence": "I go to school by car every day",
      "replaced_word": "bus",
      "changed_word": "car",
      "meaning": "I go to school by car every day"
    }}
  ]
}}

Now, create three alternative sentences for the given sentence: "{sentence}"

**LANGUAGE COMPLIANCE CHECK:** Before finalizing your response, verify that:
1. Every sentence is written ONLY in {learning_language}
2. Every replaced_word is written ONLY in {learning_language}
3. Every changed_word is written ONLY in {learning_language}
4. Every meaning is written ONLY in {system_language}
5. No fields contain mixed languages or incorrect language usage """

    retry_count = 0
    while retry_count < max_retries:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PyramidReplaceItem,
                ),
            )
            return response.parsed

        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"Error in replace_word after {max_retries} attempts: {str(e)}")
                return None
            time.sleep(1)  # Wait before retrying


def paraphrase_sentence(
    sentence: str,
    learning_language: str = "Turkish",
    system_language: str = "English",
    user_level: str = "A1 - Beginner",
    purpose: str = "General Knowledge",
    excluded_words: List[str] = None,
    max_retries: int = 3,
) -> Optional[PyramidParaphItem]:
    """Generate 3 alternative paraphrased sentences expressing the same meaning."""

    # Prepare excluded words section
    excluded_words_section = ""
    if excluded_words:
        excluded_words_str = ", ".join(excluded_words)
        excluded_words_section = f"""
**IMPORTANT - AVOID REPETITION:**
- DO NOT use any of these words/phrases that have been used in previous steps: {excluded_words_str}
- Generate completely different paraphrased sentences that haven't been used before.
- Be creative and come up with fresh alternatives that avoid these previously used words.
"""

    prompt = f"""
**CRITICAL LANGUAGE REQUIREMENTS:**
- ALL generated paraphrased sentences MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language for sentences.
- ALL meanings/translations MUST be written EXCLUSIVELY in {system_language}. Do NOT use any other language for meanings.
- DO NOT mix languages within a single field. Each field must contain content in only one specified language.
- Verify language accuracy: {learning_language} content must follow {learning_language} spelling, grammar, and vocabulary conventions.
- Verify language accuracy: {system_language} translations must follow {system_language} spelling, grammar, and vocabulary conventions.
{excluded_words_section}
Task: Create three alternative paraphrased sentences for the original sentence. Each alternative sentence:
- Must be grammatically correct and semantically meaningful in {learning_language}.
- Must maintain the original meaning of the sentence.
- Must be a unique paraphrase of the original sentence.
- Result sentence difficulty should be appropriate for {user_level} level learners.
- Must use vocabulary and grammar structures that match or are slightly below the user's {user_level} proficiency level.
- Should avoid complex terminology or advanced grammatical constructions that exceed the user's knowledge level.
- Result sentences should be relevant to the purpose: {purpose}.

For each alternative sentence, the following must be provided:
- The paraphrased sentence (in {learning_language}).
- The meaning of the alternative sentence (translation in {system_language}).

In addition, the original sentence and its meaning must be given in {system_language}.

Note the following rules:
- Each alternative sentence must be a unique paraphrase of the original sentence.
- Translations must be correct and natural in {system_language}.

Format the output as a JSON object with the following structure, aligning with the PyramidParaphItem and PyramidParaphOptions Pydantic models:
{{
  "initial_sentence": "original sentence (in {learning_language})",
  "initial_sentence_meaning": "meaning of original sentence (in {system_language})",
  "options": [
    {{
      "paraphrased_sentence": "paraphrased sentence 1 (in {learning_language})",
      "meaning": "meaning of paraphrased sentence 1 (in {system_language})"
    }},
    {{
      "paraphrased_sentence": "paraphrased sentence 2 (in {learning_language})",
      "meaning": "meaning of paraphrased sentence 2 (in {system_language})"
    }},
    {{
      "paraphrased_sentence": "paraphrased sentence 3 (in {learning_language})",
      "meaning": "meaning of paraphrased sentence 3 (in {system_language})"
    }}
  ]
}}

Example:
If the original sentence is "The quick brown fox jumps over the lazy dog" ({learning_language} = English), the output would be as follows:
```json
{{
  "initial_sentence": "The quick brown fox jumps over the lazy dog",
  "initial_sentence_meaning": "The quick brown fox jumps over the lazy dog",
  "options": [
    {{
      "paraphrased_sentence": "A speedy brown fox leaps over the sluggish canine",
      "meaning": "A speedy brown fox leaps over the sluggish canine"
    }},
    {{
      "paraphrased_sentence": "Jumping over the idle dog was the swift brown fox",
      "meaning": "Jumping over the idle dog was the swift brown fox"
    }},
    {{
      "paraphrased_sentence": "The brown fox, which was quick, jumped over the dog that was lazy",
      "meaning": "The brown fox, which was quick, jumped over the dog that was lazy"
    }}
  ]
}} 

Now, create three alternative paraphrased sentences for the given sentence: "{sentence}"

**LANGUAGE COMPLIANCE CHECK:** Before finalizing your response, verify that:
1. Every paraphrased_sentence is written ONLY in {learning_language}
2. Every meaning is written ONLY in {system_language}
3. No fields contain mixed languages or incorrect language usage """

    retry_count = 0
    while retry_count < max_retries:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PyramidParaphItem,
                ),
            )
            return response.parsed
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(
                    f"Error in paraphrase_sentence after {max_retries} attempts: {str(e)}"
                )
                return None
            time.sleep(1)


def get_first_sentence(
    learning_language: str = "Turkish",
    system_language: str = "English",
    user_level: str = "A1 - Beginner",
    purpose: str = "General Knowledge",
    max_retries: int = 3,
) -> Optional[str]:
    """Generate a first sentence in the learning language for the pyramid exercise."""

    prompt = f"""
**CRITICAL LANGUAGE REQUIREMENTS:**
- The generated sentence MUST be written EXCLUSIVELY in {learning_language}. Do NOT use any other language.
- Verify language accuracy: The sentence must follow {learning_language} spelling, grammar, and vocabulary conventions.
- The sentence must contain ONLY {learning_language} words and grammar structures.

Task: Create a simple, grammatically correct sentence in {learning_language}. The sentence should be useful for language learning.
- The sentence should be practical and culturally relevant.
- The sentence should be appropriate for {user_level} level learners.
- The sentence should be relevant to the purpose: {purpose}.
- The sentence should not be too complex or difficult to understand.
- The sentence should not contain any idiomatic expressions or complex structures.
- The sentence should not be a common phrase or idiom.
- The sentence should be 4-12 words in length. Give shorter sentences for lower levels and longer sentences for higher levels.
- The sentence should use common vocabulary but include 1-2 less common words.
- The sentence should include at least one conjunction or transition word.
- The sentence should be in {learning_language}.
- The sentence should be clear and easy to understand for language learners.
- The sentence should be unique and not a common phrase or idiom.
- The sentence should not contain any slang or informal language.

**LANGUAGE COMPLIANCE CHECK:** Before finalizing your response, verify that:
1. The generated sentence is written ONLY in {learning_language}
2. No words from other languages are included
3. The sentence follows {learning_language} grammar and spelling conventions """

    retry_count = 0
    while retry_count < max_retries:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=str,
                ),
            )
            return response.parsed
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(
                    f"Error in get_first_sentence after {max_retries} attempts: {str(e)}"
                )
                return None
            time.sleep(1)  # Wait before retrying
