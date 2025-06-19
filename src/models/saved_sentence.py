from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SavedSentence(BaseModel):
    """Model for saved sentences from pyramid exercises"""
    
    user_id: str
    sentence: str  # The sentence that was saved (could be original or transformed)
    meaning: str  # The meaning/translation of the sentence
    transformation_type: str  # "expand", "shrink", "paraphrase", "replace", or "original"
    source_sentence: str  # The original sentence before transformation
    pyramid_id: Optional[str] = None  # Reference to the pyramid this came from
    step_number: Optional[int] = None  # Which step in the pyramid
    saved_at: datetime = Field(default_factory=datetime.utcnow)


class SaveSentenceRequest(BaseModel):
    """Request model for saving a sentence"""
    
    sentence: str
    meaning: str
    transformation_type: str
    source_sentence: str
    pyramid_id: Optional[str] = None
    step_number: Optional[int] = None


class DeleteSavedSentenceRequest(BaseModel):
    """Request model for deleting a saved sentence"""
    
    sentence: str
    meaning: str


class CheckSavedSentenceRequest(BaseModel):
    """Request model for checking if a sentence is saved"""
    
    sentence: str
    meaning: str