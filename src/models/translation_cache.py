from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TranslationCache(BaseModel):
    """Model for caching translations to avoid repeated API calls"""
    
    original_text: str = Field(..., description="Original text to be translated")
    translated_text: str = Field(..., description="Translated text")
    source_language: str = Field(..., description="Source language code")
    target_language: str = Field(..., description="Target language code")
    text_hash: str = Field(..., description="Hash of original text for fast lookup")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the translation was cached")
    last_used: datetime = Field(default_factory=datetime.utcnow, description="When the translation was last accessed")
    usage_count: int = Field(default=1, description="Number of times this translation has been used")
    
    class Config:
        # Allow arbitrary field names for MongoDB compatibility
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True


class WritingQuestionCache(BaseModel):
    """Model for caching translated writing questions"""
    
    question_id: str = Field(..., description="Unique identifier for the question")
    target_language: str = Field(..., description="Target language for the translation")
    translated_data: dict = Field(..., description="Complete translated question data")
    original_data: dict = Field(..., description="Original question data for reference")
    cache_key: str = Field(..., description="Unique cache key for fast lookup")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the question was cached")
    last_used: datetime = Field(default_factory=datetime.utcnow, description="When the cache was last accessed")
    usage_count: int = Field(default=1, description="Number of times this cache has been used")
    
    class Config:
        # Allow arbitrary field names for MongoDB compatibility
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True