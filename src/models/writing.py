from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal
from datetime import datetime, timezone

# Request model for writing evaluation endpoints
class WritingEvaluationRequest(BaseModel):
    text: str
    question: Optional[str] = ""

# Request model for answering writing questions
class WritingAnswerRequest(BaseModel):
    question_id: str
    level: str
    answer: str

# Model for individual scenario answer
class ScenarioAnswer(BaseModel):
    scenario_index: int = Field(description="Index of the scenario (0-based)")
    scenario_text: str = Field(description="The scenario question text")
    answer: str = Field(description="User's answer to this scenario")

# Request model for answering writing questions with multiple scenarios
class WritingScenarioAnswerRequest(BaseModel):
    question_id: str
    level: str
    scenario_answers: List[ScenarioAnswer] = Field(description="List of answers for each scenario")

# Evaluation details model - corresponds to frontend WritingEvaluationDetails
class WritingEvaluationDetails(BaseModel):
    content_score: int = Field(description="Score for content quality (1-5 scale)")
    organization_score: int = Field(description="Score for organization and structure (1-5 scale)")
    language_score: int = Field(description="Score for language usage (1-5 scale)")
    total_score: int = Field(description="Sum of all scores (max 15)")
    xp_earned: Optional[int] = Field(default=None, description="XP awarded to user (total_score × 10)")

# Corresponds to WritingCriteria in frontend
class WritingCriteriaCategory(BaseModel):
    description: str
    factors: List[str]

class WritingCriteria(BaseModel):
    content: WritingCriteriaCategory
    organization: WritingCriteriaCategory
    language: WritingCriteriaCategory

# Feedback item model for specific writing corrections
class WritingFeedbackItem(BaseModel):
    type: Literal["Spelling", "Grammar", "Punctuation", "Style"]
    error: str
    suggestion: str

# Simple writing response (basic feedback)
class WritingResponse(BaseModel):
    score: int
    feedback: str

# Detailed writing response with breakdown
class DetailedWritingResponse(WritingResponse):
    details: WritingEvaluationDetails
    criteria: Optional[WritingCriteria] = None
    feedback_items: Optional[List[WritingFeedbackItem]] = None

# Database model for storing user responses to specific questions
class WritingQuestionResponse(BaseModel):
    user_id: str
    question_id: str
    level: str
    question_text: str
    user_answer: str  # Combined answer for backward compatibility
    scenario_answers: Optional[List[ScenarioAnswer]] = None  # Individual scenario answers
    score: int
    feedback: str
    content_score: int
    organization_score: int
    language_score: int
    total_score: int
    xp_earned: Optional[int] = None
    feedback_items: Optional[List[WritingFeedbackItem]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    @classmethod
    def from_evaluation(cls, user_id: str, question_id: str, level: str, question_text: str, 
                       user_answer: str, evaluation: DetailedWritingResponse, 
                       scenario_answers: Optional[List[ScenarioAnswer]] = None):
        """Create a WritingQuestionResponse from evaluation"""
        return cls(
            user_id=user_id,
            question_id=question_id,
            level=level,
            question_text=question_text,
            user_answer=user_answer,
            scenario_answers=scenario_answers,
            score=evaluation.score,
            feedback=evaluation.feedback,
            content_score=evaluation.details.content_score,
            organization_score=evaluation.details.organization_score,
            language_score=evaluation.details.language_score,
            total_score=evaluation.details.total_score,
            xp_earned=evaluation.details.xp_earned,
            feedback_items=evaluation.feedback_items,
        )

# Response model for returning user answers with evaluation
class WritingAnswerResponse(BaseModel):
    question_id: str
    question_text: str
    user_answer: str
    evaluation: DetailedWritingResponse

# Response model for scenario-based answers with evaluation
class WritingScenarioAnswerResponse(BaseModel):
    question_id: str
    question_text: str
    scenario_answers: List[ScenarioAnswer]
    combined_answer: str  # Combined text for evaluation
    evaluation: DetailedWritingResponse

# Models for writing questions
class WritingQuestion(BaseModel):
    id: str = Field(description="Question identifier (e.g., B1, E1, I1, A1)")
    name: str = Field(description="Short name of the question")
    full_name: str = Field(description="Full question text with emoji")
    scenarios: List[str] = Field(description="List of scenario descriptions")
    solved: bool = Field(default=False, description="Whether the user has solved this question")
    level: str = Field(description="Question level (beginner, elementary, intermediate, advanced)")

class WritingQuestionsResponse(BaseModel):
    level: str
    title: str
    questions: List[WritingQuestion]
    total_questions: int