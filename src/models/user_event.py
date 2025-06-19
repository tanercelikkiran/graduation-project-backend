from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List


class EventType(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REFRESH_TOKEN = "refresh_token"
    APP_OPEN = "app_open"
    PYRAMID = "pyramid"
    VOCABULARY = "vocabulary"
    WRITING = "writing"
    EMAIL = "email"


class UserEvent(BaseModel):
    user_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_id: Optional[str] = None  # For activity-specific IDs
    details: Optional[Dict[str, Any]] = None  # For additional event-specific data

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VocabularyEvent(UserEvent):
    """
    Model for tracking vocabulary activity statistics for a specific list
    """
    # Remove field annotations from class definition since they are accessed via properties
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        # Add configuration to exclude property accessors during serialization
        exclude = {
            'vocabulary_list_id', 'words', 'duration_seconds', 
            'letter_hints_used', 'relevant_word_hints_used', 'emoji_hints_used',
            'total_hints', 'correct_answers', 'incorrect_answers', 
            'accuracy_rate', 'completed', 'xp_earned'
        }
    
    def __init__(self, **data):
        # Initialize details if not provided
        if 'details' not in data:
            data['details'] = {}
            
        # Store vocabulary-specific fields in details
        for field in ['vocabulary_list_id', 'words', 'duration_seconds', 
                     'letter_hints_used', 'relevant_word_hints_used', 'emoji_hints_used',
                     'total_hints', 'correct_answers', 'incorrect_answers', 
                     'accuracy_rate', 'completed', 'xp_earned']:
            if field in data:
                data['details'][field] = data.pop(field)
                
        # Set event_type to VOCABULARY
        data['event_type'] = EventType.VOCABULARY
        
        # Set event_id to vocabulary_list_id if provided
        if 'details' in data and 'vocabulary_list_id' in data['details']:
            data['event_id'] = data['details']['vocabulary_list_id']
            
        super().__init__(**data)
    
    # Override the model_dump method to exclude properties from serialization
    def model_dump(self):
        # First get the base UserEvent fields
        data = super().model_dump()
        
        # Make sure we don't include the property accessor methods
        # This will fix the MongoDB serialization error
        fields_to_remove = [
            'vocabulary_list_id', 'words', 'duration_seconds', 
            'letter_hints_used', 'relevant_word_hints_used', 'emoji_hints_used',
            'total_hints', 'correct_answers', 'incorrect_answers', 
            'accuracy_rate', 'completed', 'xp_earned'
        ]
        
        for field in fields_to_remove:
            if field in data:
                del data[field]
                
        return data
    
    @property
    def vocabulary_list_id(self) -> str:
        return self.details.get('vocabulary_list_id', '')
    
    @property
    def words(self) -> List[str]:
        return self.details.get('words', [])
        
    @property
    def duration_seconds(self) -> int:
        return self.details.get('duration_seconds', 0)
    
    @duration_seconds.setter
    def duration_seconds(self, value: int):
        self.details['duration_seconds'] = value
        
    @property
    def letter_hints_used(self) -> int:
        return self.details.get('letter_hints_used', 0)
    
    @letter_hints_used.setter
    def letter_hints_used(self, value: int):
        self.details['letter_hints_used'] = value
        
    @property
    def relevant_word_hints_used(self) -> int:
        return self.details.get('relevant_word_hints_used', 0)
    
    @relevant_word_hints_used.setter
    def relevant_word_hints_used(self, value: int):
        self.details['relevant_word_hints_used'] = value
        
    @property
    def emoji_hints_used(self) -> int:
        return self.details.get('emoji_hints_used', 0)
    
    @emoji_hints_used.setter
    def emoji_hints_used(self, value: int):
        self.details['emoji_hints_used'] = value
        
    @property
    def total_hints(self) -> int:
        return self.details.get('total_hints', 0)
    
    @total_hints.setter
    def total_hints(self, value: int):
        self.details['total_hints'] = value
        
    @property
    def correct_answers(self) -> int:
        return self.details.get('correct_answers', 0)
    
    @correct_answers.setter
    def correct_answers(self, value: int):
        self.details['correct_answers'] = value
        
    @property
    def incorrect_answers(self) -> int:
        return self.details.get('incorrect_answers', 0)
    
    @incorrect_answers.setter
    def incorrect_answers(self, value: int):
        self.details['incorrect_answers'] = value
        
    @property
    def accuracy_rate(self) -> float:
        return self.details.get('accuracy_rate', 0.0)
    
    @accuracy_rate.setter
    def accuracy_rate(self, value: float):
        self.details['accuracy_rate'] = value
        
    @property
    def completed(self) -> bool:
        return self.details.get('completed', False)
    
    @completed.setter
    def completed(self, value: bool):
        self.details['completed'] = value
        
    @property
    def xp_earned(self) -> int:
        return self.details.get('xp_earned', 0)
    
    @xp_earned.setter
    def xp_earned(self, value: int):
        self.details['xp_earned'] = value

    def calculate_accuracy(self):
        # Access the values directly from details dictionary instead of using properties
        correct = self.details.get('correct_answers', 0)
        incorrect = self.details.get('incorrect_answers', 0)
        total_attempts = correct + incorrect
        
        if total_attempts > 0:
            # Set accuracy_rate directly in the details dictionary
            self.details['accuracy_rate'] = correct / total_attempts
        
        return self.details.get('accuracy_rate', 0.0)

    def calculate_xp(self):
        """Calculate XP based on performance if the list is completed"""
        if not self.details.get('completed', False):
            return 0

        # Access values directly from details dictionary
        words = self.details.get('words', [])
        accuracy_rate = self.details.get('accuracy_rate', 0.0)
        total_hints = self.details.get('total_hints', 0)
        
        # Base XP per word
        base_xp = len(words) * 5

        # Accuracy bonus: Up to 50% bonus for 100% accuracy
        accuracy_bonus = int(base_xp * 0.5 * accuracy_rate)

        # Efficiency bonus: Less hints used means more XP
        total_possible_hints = len(words) * 3  # 3 types of hints per word
        hint_ratio = (
            total_hints / total_possible_hints if total_possible_hints > 0 else 1
        )
        hint_penalty = int(
            base_xp * 0.3 * hint_ratio
        )  # Up to 30% penalty for using all hints

        # Calculate final XP and store directly in details dictionary
        earned_xp = max(base_xp + accuracy_bonus - hint_penalty, len(words))
        self.details['xp_earned'] = earned_xp
        
        return earned_xp


class WritingEvent(UserEvent):
    """
    Model for tracking writing activity statistics for a specific question
    """
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        # Add configuration to exclude property accessors during serialization
        exclude = {
            'question_id', 'question_text', 'level', 'session_start', 'session_end',
            'duration_seconds', 'word_count', 'character_count', 'revision_count',
            'final_answer', 'ai_feedback', 'xp_earned', 'completed'
        }
    
    def __init__(self, **data):
        # Initialize details if not provided
        if 'details' not in data:
            data['details'] = {}
            
        # Store writing-specific fields in details
        for field in ['question_id', 'question_text', 'level', 'session_start', 'session_end',
                     'duration_seconds', 'word_count', 'character_count', 'revision_count',
                     'final_answer', 'ai_feedback', 'xp_earned', 'completed']:
            if field in data:
                data['details'][field] = data.pop(field)
                
        # Set event_type to WRITING
        data['event_type'] = EventType.WRITING
        
        # Set event_id to question_id if provided
        if 'details' in data and 'question_id' in data['details']:
            data['event_id'] = data['details']['question_id']
            
        super().__init__(**data)
    
    # Override the model_dump method to exclude properties from serialization
    def model_dump(self):
        # First get the base UserEvent fields
        data = super().model_dump()
        
        # Make sure we don't include the property accessor methods
        fields_to_remove = [
            'question_id', 'question_text', 'level', 'session_start', 'session_end',
            'duration_seconds', 'word_count', 'character_count', 'revision_count',
            'final_answer', 'ai_feedback', 'xp_earned', 'completed'
        ]
        
        for field in fields_to_remove:
            if field in data:
                del data[field]
                
        return data
    
    @property
    def question_id(self) -> str:
        return self.details.get('question_id', '')
    
    @property
    def question_text(self) -> str:
        return self.details.get('question_text', '')
        
    @property
    def level(self) -> str:
        return self.details.get('level', '')
    
    @property
    def session_start(self) -> Optional[datetime]:
        start_str = self.details.get('session_start')
        if start_str:
            if isinstance(start_str, str):
                return datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            return start_str
        return None
    
    @session_start.setter
    def session_start(self, value: datetime):
        self.details['session_start'] = value.isoformat()
        
    @property
    def session_end(self) -> Optional[datetime]:
        end_str = self.details.get('session_end')
        if end_str:
            if isinstance(end_str, str):
                return datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            return end_str
        return None
    
    @session_end.setter
    def session_end(self, value: datetime):
        self.details['session_end'] = value.isoformat()
        
    @property
    def duration_seconds(self) -> int:
        return self.details.get('duration_seconds', 0)
    
    @duration_seconds.setter
    def duration_seconds(self, value: int):
        self.details['duration_seconds'] = value
        
    @property
    def word_count(self) -> int:
        return self.details.get('word_count', 0)
    
    @word_count.setter
    def word_count(self, value: int):
        self.details['word_count'] = value
        
    @property
    def character_count(self) -> int:
        return self.details.get('character_count', 0)
    
    @character_count.setter
    def character_count(self, value: int):
        self.details['character_count'] = value
        
    @property
    def revision_count(self) -> int:
        return self.details.get('revision_count', 0)
    
    @revision_count.setter
    def revision_count(self, value: int):
        self.details['revision_count'] = value
        
    @property
    def final_answer(self) -> str:
        return self.details.get('final_answer', '')
    
    @final_answer.setter
    def final_answer(self, value: str):
        self.details['final_answer'] = value
        
    @property
    def ai_feedback(self) -> Dict[str, Any]:
        return self.details.get('ai_feedback', {})
    
    @ai_feedback.setter
    def ai_feedback(self, value: Dict[str, Any]):
        self.details['ai_feedback'] = value
        
    @property
    def completed(self) -> bool:
        return self.details.get('completed', False)
    
    @completed.setter
    def completed(self, value: bool):
        self.details['completed'] = value
        
    @property
    def xp_earned(self) -> int:
        return self.details.get('xp_earned', 0)
    
    @xp_earned.setter
    def xp_earned(self, value: int):
        self.details['xp_earned'] = value

    def calculate_session_duration(self):
        """Calculate session duration from start and end times"""
        if self.session_start and self.session_end:
            duration = self.session_end - self.session_start
            self.duration_seconds = int(duration.total_seconds())
        return self.duration_seconds

    def calculate_xp(self):
        """Calculate XP based on performance if the session is completed"""
        if not self.completed:
            return 0

        # Access values directly from details dictionary
        ai_feedback = self.details.get('ai_feedback', {})
        total_score = ai_feedback.get('total_score', 0)
        duration_seconds = self.details.get('duration_seconds', 0)
        word_count = self.details.get('word_count', 0)
        
        # Base XP calculation (same as existing writing service)
        base_xp = total_score * 20  # Max 300 XP for perfect score of 15
        
        # Bonus for length and engagement
        word_bonus = min(word_count // 10, 50)  # 1 XP per 10 words, max 50 bonus
        
        # Time-based efficiency bonus (bonus for focused writing)
        if duration_seconds > 0 and word_count > 0:
            words_per_minute = (word_count / duration_seconds) * 60
            if 10 <= words_per_minute <= 30:  # Optimal writing speed
                efficiency_bonus = 25
            elif 5 <= words_per_minute < 10 or 30 < words_per_minute <= 50:
                efficiency_bonus = 10
            else:
                efficiency_bonus = 0
        else:
            efficiency_bonus = 0
        
        # Calculate final XP and store directly in details dictionary
        earned_xp = base_xp + word_bonus + efficiency_bonus
        self.details['xp_earned'] = earned_xp
        
        return earned_xp


class PyramidEvent(UserEvent):
    """
    Model for tracking pyramid activity statistics for a specific pyramid exercise
    """
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        # Add configuration to exclude property accessors during serialization
        exclude = {
            'pyramid_id', 'session_start', 'session_end', 'duration_seconds',
            'total_steps', 'completed_steps', 'step_types', 'steps_detail',
            'accuracy_rate', 'avg_time_per_step', 'completed', 'xp_earned'
        }
    
    def __init__(self, **data):
        # Initialize details if not provided
        if 'details' not in data:
            data['details'] = {}
            
        # Store pyramid-specific fields in details
        for field in ['pyramid_id', 'session_start', 'session_end', 'duration_seconds',
                     'total_steps', 'completed_steps', 'step_types', 'steps_detail',
                     'accuracy_rate', 'avg_time_per_step', 'completed', 'xp_earned']:
            if field in data:
                data['details'][field] = data.pop(field)
                
        # Set event_type to PYRAMID
        data['event_type'] = EventType.PYRAMID
        
        # Set event_id to pyramid_id if provided
        if 'details' in data and 'pyramid_id' in data['details']:
            data['event_id'] = data['details']['pyramid_id']
            
        super().__init__(**data)
    
    # Override the model_dump method to exclude properties from serialization
    def model_dump(self):
        # First get the base UserEvent fields
        data = super().model_dump()
        
        # Make sure we don't include the property accessor methods
        fields_to_remove = [
            'pyramid_id', 'session_start', 'session_end', 'duration_seconds',
            'total_steps', 'completed_steps', 'step_types', 'steps_detail',
            'accuracy_rate', 'avg_time_per_step', 'completed', 'xp_earned'
        ]
        
        for field in fields_to_remove:
            if field in data:
                del data[field]
                
        return data
    
    @property
    def pyramid_id(self) -> str:
        return self.details.get('pyramid_id', '')
    
    @property
    def session_start(self) -> Optional[datetime]:
        start_str = self.details.get('session_start')
        if start_str:
            if isinstance(start_str, str):
                return datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            return start_str
        return None
    
    @session_start.setter
    def session_start(self, value: datetime):
        self.details['session_start'] = value.isoformat()
        
    @property
    def session_end(self) -> Optional[datetime]:
        end_str = self.details.get('session_end')
        if end_str:
            if isinstance(end_str, str):
                return datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            return end_str
        return None
    
    @session_end.setter
    def session_end(self, value: datetime):
        self.details['session_end'] = value.isoformat()
        
    @property
    def duration_seconds(self) -> int:
        return self.details.get('duration_seconds', 0)
    
    @duration_seconds.setter
    def duration_seconds(self, value: int):
        self.details['duration_seconds'] = value
        
    @property
    def total_steps(self) -> int:
        return self.details.get('total_steps', 0)
    
    @total_steps.setter
    def total_steps(self, value: int):
        self.details['total_steps'] = value
        
    @property
    def completed_steps(self) -> int:
        return self.details.get('completed_steps', 0)
    
    @completed_steps.setter
    def completed_steps(self, value: int):
        self.details['completed_steps'] = value
        
    @property
    def step_types(self) -> List[str]:
        return self.details.get('step_types', [])
    
    @step_types.setter
    def step_types(self, value: List[str]):
        self.details['step_types'] = value
        
    @property
    def steps_detail(self) -> List[Dict[str, Any]]:
        return self.details.get('steps_detail', [])
    
    @steps_detail.setter
    def steps_detail(self, value: List[Dict[str, Any]]):
        self.details['steps_detail'] = value
        
    @property
    def accuracy_rate(self) -> float:
        return self.details.get('accuracy_rate', 0.0)
    
    @accuracy_rate.setter
    def accuracy_rate(self, value: float):
        self.details['accuracy_rate'] = value
        
    @property
    def avg_time_per_step(self) -> float:
        return self.details.get('avg_time_per_step', 0.0)
    
    @avg_time_per_step.setter
    def avg_time_per_step(self, value: float):
        self.details['avg_time_per_step'] = value
        
    @property
    def completed(self) -> bool:
        return self.details.get('completed', False)
    
    @completed.setter
    def completed(self, value: bool):
        self.details['completed'] = value
        
    @property
    def xp_earned(self) -> int:
        return self.details.get('xp_earned', 0)
    
    @xp_earned.setter
    def xp_earned(self, value: int):
        self.details['xp_earned'] = value

    def calculate_session_duration(self):
        """Calculate session duration from start and end times"""
        if self.session_start and self.session_end:
            duration = self.session_end - self.session_start
            self.duration_seconds = int(duration.total_seconds())
        return self.duration_seconds

    def calculate_accuracy(self):
        """Calculate accuracy rate based on completed steps vs total steps"""
        total_steps = self.details.get('total_steps', 0)
        completed_steps = self.details.get('completed_steps', 0)
        
        if total_steps > 0:
            self.details['accuracy_rate'] = completed_steps / total_steps
        else:
            self.details['accuracy_rate'] = 0.0
            
        return self.details.get('accuracy_rate', 0.0)

    def calculate_avg_time_per_step(self):
        """Calculate average time per step"""
        duration = self.details.get('duration_seconds', 0)
        completed_steps = self.details.get('completed_steps', 0)
        
        if completed_steps > 0:
            self.details['avg_time_per_step'] = duration / completed_steps
        else:
            self.details['avg_time_per_step'] = 0.0
            
        return self.details.get('avg_time_per_step', 0.0)

    def calculate_xp(self):
        """Calculate XP based on performance if the pyramid is completed"""
        if not self.completed:
            return 0

        # Access values directly from details dictionary
        total_steps = self.details.get('total_steps', 0)
        completed_steps = self.details.get('completed_steps', 0)
        duration_seconds = self.details.get('duration_seconds', 0)
        accuracy_rate = self.details.get('accuracy_rate', 0.0)
        
        # Base XP calculation: 25 base + 5 per step (same as current system)
        base_xp = 25 + (completed_steps * 5)
        
        # Accuracy bonus: Up to 50% bonus for 100% accuracy
        accuracy_bonus = int(base_xp * 0.5 * accuracy_rate)
        
        # Speed bonus: Bonus for completing steps efficiently
        if duration_seconds > 0 and completed_steps > 0:
            avg_time_per_step = duration_seconds / completed_steps
            # Bonus for completing steps in reasonable time (30-120 seconds per step)
            if 30 <= avg_time_per_step <= 120:
                speed_bonus = int(base_xp * 0.25)  # 25% bonus
            elif 15 <= avg_time_per_step < 30 or 120 < avg_time_per_step <= 180:
                speed_bonus = int(base_xp * 0.1)   # 10% bonus
            else:
                speed_bonus = 0
        else:
            speed_bonus = 0
        
        # Calculate final XP and store directly in details dictionary
        earned_xp = base_xp + accuracy_bonus + speed_bonus
        self.details['xp_earned'] = earned_xp
        
        return earned_xp
