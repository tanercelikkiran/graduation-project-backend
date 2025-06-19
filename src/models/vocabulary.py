from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class VocabularyItem(BaseModel):
    word: str
    meaning: str
    relevantWords: List[str]
    emoji: str


class VocabularyList(BaseModel):
    words: List[VocabularyItem]


class SaveVocabularyRequest(BaseModel):
    word: str
    meaning: str
    relevantWords: List[str]
    emoji: str
    system_language: Optional[str] = None


class VocabularyStatistics(BaseModel):
    """Model for tracking statistics for a specific word for a user"""

    user_id: str
    word: str
    meaning: str
    system_language: Optional[str] = None  # Changed from default "English" to None

    # Added relevant words and emoji fields
    relevantWords: List[str] = Field(default_factory=list)
    emoji: str = (
        "📚"  # Added default value to prevent validation errors with older records
    )

    # Hint usage counts
    letter_hints: int = 0
    relevant_word_hints: int = 0
    emoji_hints: int = 0

    # Success tracking
    successful_attempts: int = 0
    failed_attempts: int = 0

    # Timestamps
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    last_attempt: datetime = Field(default_factory=datetime.utcnow)

    # Difficulty score (calculated field, not stored)
    difficulty_score: float = 0.0

    def calculate_difficulty_score(self) -> float:
        """
        Calculate a difficulty score for this word based on hint usage and success rate
        Higher score = more difficult word
        """
        # Base score from hint usage (letter hints weighted higher)
        hint_score = (
            (self.letter_hints * 1.5) + self.relevant_word_hints + self.emoji_hints
        )

        # Adjust for success/failure ratio
        total_attempts = self.successful_attempts + self.failed_attempts
        if total_attempts > 0:
            success_rate = self.successful_attempts / total_attempts
            # Inverse of success rate - lower success rate means higher difficulty
            success_factor = 1 - success_rate
            hint_score = hint_score * (1 + success_factor)

        # Time decay factor - more recent words get higher priority
        # (This won't be used in storage, just in the calculation)
        self.difficulty_score = hint_score
        return hint_score


class HintUsageRequest(BaseModel):
    word: str
    meaning: str
    hint_type: str  # "letter", "relevant_word", or "emoji"
    system_language: Optional[str] = None  # Changed from default "English" to None


class AttemptResult(BaseModel):
    word: str
    meaning: str
    success: bool  # True if the attempt was successful, False otherwise
    system_language: Optional[str] = None  # Changed from default "English" to None
