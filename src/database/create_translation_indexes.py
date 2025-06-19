"""
Create database indexes for translation cache to improve performance
"""

from src.database.database import translation_cache_table
import logging

logger = logging.getLogger(__name__)

def create_translation_cache_indexes():
    """
    Create indexes on translation cache collection for optimal performance
    """
    try:
        # Index for text translation lookups
        translation_cache_table.create_index([
            ("text_hash", 1),
            ("source_language", 1),
            ("target_language", 1)
        ], name="text_translation_lookup")
        
        # Index for question cache lookups
        translation_cache_table.create_index([
            ("cache_key", 1)
        ], name="question_cache_lookup")
        
        # Index for cache cleanup (by last_used date)
        translation_cache_table.create_index([
            ("last_used", 1)
        ], name="cache_cleanup")
        
        # Index for question-specific cache clearing
        translation_cache_table.create_index([
            ("question_id", 1)
        ], name="question_cache_clear")
        
        # Index for language-specific cache clearing
        translation_cache_table.create_index([
            ("target_language", 1)
        ], name="language_cache_clear")
        
        # Index for usage statistics
        translation_cache_table.create_index([
            ("usage_count", -1)
        ], name="usage_stats")
        
        logger.info("Successfully created translation cache indexes")
        
    except Exception as e:
        logger.error(f"Error creating translation cache indexes: {str(e)}")

if __name__ == "__main__":
    create_translation_cache_indexes()