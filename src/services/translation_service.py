from typing import Optional, Dict, List
import logging
import os
import hashlib
from datetime import datetime, timedelta
from src.settings import TRANSLATE_KEY
from src.database.database import translation_cache_table
from src.models.translation_cache import TranslationCache, WritingQuestionCache

# Set up logging
logger = logging.getLogger(__name__)

# Debug: Check if TRANSLATE_KEY is loaded
logger.info(f"TRANSLATE_KEY loaded: {'Yes' if TRANSLATE_KEY else 'No'}")
if TRANSLATE_KEY:
    logger.info(f"TRANSLATE_KEY length: {len(TRANSLATE_KEY)}")

# Use requests for Google Translate API (simpler with API key)
import requests

# Google Translate API endpoint
TRANSLATE_API_URL = "https://translation.googleapis.com/language/translate/v2"


def _translate_with_google_api(
    text: str, target_lang: str, source_lang: str = "en"
) -> Optional[str]:
    """Use Google Translate API via HTTP requests"""
    try:
        if not TRANSLATE_KEY:
            logger.error("TRANSLATE_KEY not found in environment")
            return None

        payload = {
            "q": text,
            "target": target_lang,
            "source": source_lang,
            "format": "text",
            "key": TRANSLATE_KEY,
        }

        response = requests.post(TRANSLATE_API_URL, data=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["translations"][0]["translatedText"]

    except Exception as e:
        logger.error(f"Google Translate API error: {str(e)}")
        return None


# Language code mapping for common languages
LANGUAGE_CODES = {
    "english": "en",
    "spanish": "es",
    "turkish": "tr",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "chinese": "zh",
    "japanese": "ja",
    "korean": "ko",
    "arabic": "ar",
}


def get_language_code(language_name: str) -> str:
    """
    Get language code from language name

    Args:
        language_name: Language name (e.g., "English", "Spanish")

    Returns:
        Language code (e.g., "en", "es")
    """
    return LANGUAGE_CODES.get(language_name.lower(), language_name.lower())


def _generate_text_hash(text: str, source_lang: str, target_lang: str) -> str:
    """
    Generate a hash for text translation caching
    
    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        MD5 hash string for cache lookup
    """
    cache_string = f"{text}|{source_lang}|{target_lang}"
    return hashlib.md5(cache_string.encode('utf-8')).hexdigest()


def _get_cached_translation(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    """
    Get cached translation if available
    
    Args:
        text: Original text
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        Cached translation or None if not found
    """
    try:
        text_hash = _generate_text_hash(text, source_lang, target_lang)
        
        cached_translation = translation_cache_table.find_one({
            "text_hash": text_hash,
            "source_language": source_lang,
            "target_language": target_lang
        })
        
        if cached_translation:
            # Update last_used and usage_count
            translation_cache_table.update_one(
                {"_id": cached_translation["_id"]},
                {
                    "$set": {"last_used": datetime.utcnow()},
                    "$inc": {"usage_count": 1}
                }
            )
            
            logger.info(f"Using cached translation for text hash: {text_hash}")
            return cached_translation["translated_text"]
            
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving cached translation: {str(e)}")
        return None


def _cache_translation(text: str, translated_text: str, source_lang: str, target_lang: str) -> None:
    """
    Cache a translation for future use
    
    Args:
        text: Original text
        translated_text: Translated text
        source_lang: Source language code
        target_lang: Target language code
    """
    try:
        text_hash = _generate_text_hash(text, source_lang, target_lang)
        
        # Check if translation already exists
        existing = translation_cache_table.find_one({
            "text_hash": text_hash,
            "source_language": source_lang,
            "target_language": target_lang
        })
        
        if existing:
            # Update existing cache entry
            translation_cache_table.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "translated_text": translated_text,
                        "last_used": datetime.utcnow()
                    },
                    "$inc": {"usage_count": 1}
                }
            )
        else:
            # Create new cache entry
            cache_entry = TranslationCache(
                original_text=text,
                translated_text=translated_text,
                source_language=source_lang,
                target_language=target_lang,
                text_hash=text_hash
            )
            
            translation_cache_table.insert_one(cache_entry.model_dump())
            
        logger.info(f"Cached translation for text hash: {text_hash}")
        
    except Exception as e:
        logger.error(f"Error caching translation: {str(e)}")


def _generate_question_cache_key(question_id: str, target_language: str) -> str:
    """
    Generate a cache key for a writing question
    
    Args:
        question_id: Question ID
        target_language: Target language
        
    Returns:
        Cache key string
    """
    return f"question_{question_id}_{target_language.lower()}"


def _get_cached_question(question_id: str, target_language: str) -> Optional[Dict]:
    """
    Get cached translated question if available
    
    Args:
        question_id: Question ID
        target_language: Target language
        
    Returns:
        Cached question data or None if not found
    """
    try:
        cache_key = _generate_question_cache_key(question_id, target_language)
        
        cached_question = translation_cache_table.find_one({
            "cache_key": cache_key
        })
        
        if cached_question:
            # Update last_used and usage_count
            translation_cache_table.update_one(
                {"_id": cached_question["_id"]},
                {
                    "$set": {"last_used": datetime.utcnow()},
                    "$inc": {"usage_count": 1}
                }
            )
            
            logger.info(f"Using cached question for: {cache_key}")
            return cached_question["translated_data"]
            
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving cached question: {str(e)}")
        return None


def _cache_question(question_id: str, target_language: str, original_data: Dict, translated_data: Dict) -> None:
    """
    Cache a translated question for future use
    
    Args:
        question_id: Question ID
        target_language: Target language
        original_data: Original question data
        translated_data: Translated question data
    """
    try:
        cache_key = _generate_question_cache_key(question_id, target_language)
        
        # Check if question cache already exists
        existing = translation_cache_table.find_one({
            "cache_key": cache_key
        })
        
        if existing:
            # Update existing cache entry
            translation_cache_table.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "translated_data": translated_data,
                        "last_used": datetime.utcnow()
                    },
                    "$inc": {"usage_count": 1}
                }
            )
        else:
            # Create new cache entry
            cache_entry = WritingQuestionCache(
                question_id=question_id,
                target_language=target_language,
                translated_data=translated_data,
                original_data=original_data,
                cache_key=cache_key
            )
            
            translation_cache_table.insert_one(cache_entry.model_dump())
            
        logger.info(f"Cached question for: {cache_key}")
        
    except Exception as e:
        logger.error(f"Error caching question: {str(e)}")


def translate_text(
    text: str, target_language: str, source_language: str = "en"
) -> Optional[str]:
    """
    Translate text using Google Translate API with caching

    Args:
        text: Text to translate
        target_language: Target language name or code
        source_language: Source language code (default: "en")

    Returns:
        Translated text or None if translation fails
    """
    try:
        # Get language codes
        target_code = get_language_code(target_language)
        source_code = get_language_code(source_language)

        # Skip translation if target is same as source
        if target_code == source_code:
            return text

        # Check cache first
        cached_translation = _get_cached_translation(text, source_code, target_code)
        if cached_translation:
            return cached_translation

        # Translate text using Google API
        translated_text = _translate_with_google_api(text, target_code, source_code)
        
        # Cache the translation if successful
        if translated_text and translated_text != text:
            _cache_translation(text, translated_text, source_code, target_code)
        
        return translated_text

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text  # Return original text if translation fails


def translate_writing_question(question_data: Dict, target_language: str) -> Dict:
    """
    Translate writing question data to target language with caching

    Args:
        question_data: Question dictionary with id, name, fullName, scenarios
        target_language: Target language for translation

    Returns:
        Translated question data
    """
    try:
        if target_language.lower() == "english":
            return question_data  # No translation needed

        # Check for question-level cache first
        question_id = str(question_data.get("id", ""))
        if question_id:
            cached_question = _get_cached_question(question_id, target_language)
            if cached_question:
                return cached_question

        translated_data = question_data.copy()

        # Translate name and fullName
        if "name" in translated_data:
            translated_data["name"] = (
                translate_text(translated_data["name"], target_language)
                or translated_data["name"]
            )

        if "fullName" in translated_data:
            translated_data["fullName"] = (
                translate_text(translated_data["fullName"], target_language)
                or translated_data["fullName"]
            )

        # Translate scenarios
        if "scenarios" in translated_data:
            translated_scenarios = []
            for scenario in translated_data["scenarios"]:
                translated_scenario = (
                    translate_text(scenario, target_language) or scenario
                )
                translated_scenarios.append(translated_scenario)
            translated_data["scenarios"] = translated_scenarios

        # Cache the translated question if we have an ID
        if question_id:
            _cache_question(question_id, target_language, question_data, translated_data)

        return translated_data

    except Exception as e:
        logger.error(f"Error translating question: {str(e)}")
        return question_data  # Return original if translation fails


def translate_questions_list(
    questions_list: List[Dict], target_language: str
) -> List[Dict]:
    """
    Translate a list of writing questions to target language

    Args:
        questions_list: List of question dictionaries
        target_language: Target language for translation

    Returns:
        List of translated question dictionaries
    """
    try:
        if target_language.lower() == "english":
            return questions_list  # No translation needed

        translated_questions = []
        for question in questions_list:
            translated_question = translate_writing_question(question, target_language)
            translated_questions.append(translated_question)

        return translated_questions

    except Exception as e:
        logger.error(f"Error translating questions list: {str(e)}")
        return questions_list  # Return original if translation fails


def translate_feedback(feedback_text: str, target_language: str) -> str:
    """
    Translate feedback text to target language

    Args:
        feedback_text: Feedback text to translate
        target_language: Target language for translation

    Returns:
        Translated feedback text
    """
    try:
        if target_language.lower() == "english":
            return feedback_text

        translated = translate_text(feedback_text, target_language)
        return translated or feedback_text

    except Exception as e:
        logger.error(f"Error translating feedback: {str(e)}")
        return feedback_text


# Cache Management Functions

def clear_translation_cache(older_than_days: int = 30) -> int:
    """
    Clear old translation cache entries
    
    Args:
        older_than_days: Clear entries older than this many days
        
    Returns:
        Number of entries cleared
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        result = translation_cache_table.delete_many({
            "last_used": {"$lt": cutoff_date}
        })
        
        logger.info(f"Cleared {result.deleted_count} old translation cache entries")
        return result.deleted_count
        
    except Exception as e:
        logger.error(f"Error clearing translation cache: {str(e)}")
        return 0


def get_cache_stats() -> Dict:
    """
    Get translation cache statistics
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        total_entries = translation_cache_table.count_documents({})
        
        # Count by type
        text_translations = translation_cache_table.count_documents({
            "text_hash": {"$exists": True}
        })
        
        question_translations = translation_cache_table.count_documents({
            "cache_key": {"$exists": True}
        })
        
        # Get usage statistics
        high_usage = translation_cache_table.count_documents({
            "usage_count": {"$gte": 10}
        })
        
        # Get recent activity
        last_week = datetime.utcnow() - timedelta(days=7)
        recent_activity = translation_cache_table.count_documents({
            "last_used": {"$gte": last_week}
        })
        
        return {
            "total_entries": total_entries,
            "text_translations": text_translations,
            "question_translations": question_translations,
            "high_usage_entries": high_usage,
            "recent_activity": recent_activity
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return {}


def clear_question_cache(question_id: str) -> int:
    """
    Clear cache entries for a specific question
    
    Args:
        question_id: Question ID to clear cache for
        
    Returns:
        Number of entries cleared
    """
    try:
        result = translation_cache_table.delete_many({
            "question_id": question_id
        })
        
        logger.info(f"Cleared {result.deleted_count} cache entries for question {question_id}")
        return result.deleted_count
        
    except Exception as e:
        logger.error(f"Error clearing question cache: {str(e)}")
        return 0


def clear_language_cache(target_language: str) -> int:
    """
    Clear cache entries for a specific target language
    
    Args:
        target_language: Target language to clear cache for
        
    Returns:
        Number of entries cleared
    """
    try:
        target_code = get_language_code(target_language)
        
        result = translation_cache_table.delete_many({
            "$or": [
                {"target_language": target_code},
                {"target_language": target_language}
            ]
        })
        
        logger.info(f"Cleared {result.deleted_count} cache entries for language {target_language}")
        return result.deleted_count
        
    except Exception as e:
        logger.error(f"Error clearing language cache: {str(e)}")
        return 0
