from datetime import datetime, timedelta
from bson import ObjectId
from typing import Union, List
from src.database.database import user_events_table, writing_table
from src.models.user_event import UserEvent, EventType, VocabularyEvent, WritingEvent, PyramidEvent
from src.models.pyramid import (
    PyramidShrinkItem,
    PyramidExpandItem,
    PyramidReplaceItem,
    PyramidParaphItem,
)
from src.models.writing import WritingQuestionResponse, DetailedWritingResponse, WritingEvaluationDetails
from src.services.xp_service import update_xp, get_xp

# Type alias for pyramid items
PyramidItem = Union[
    PyramidShrinkItem, PyramidExpandItem, PyramidReplaceItem, PyramidParaphItem
]


def log_user_event(event: UserEvent) -> dict:
    """Log a user event to the database"""
    event_dict = event.model_dump()

    # Insert the event
    result = user_events_table.insert_one(event_dict)

    # Return the created event with its ID
    if result.inserted_id:
        event_dict["_id"] = str(result.inserted_id)
        return event_dict
    return None


def log_login(user_id: str) -> dict:
    """Log a user login event"""
    event = UserEvent(
        user_id=user_id,
        event_type=EventType.LOGIN,
    )
    return log_user_event(event)


def log_logout(user_id: str) -> dict:
    """Log a user logout event"""
    event = UserEvent(user_id=user_id, event_type=EventType.LOGOUT)
    return log_user_event(event)


def log_refresh_token(user_id: str) -> dict:
    """Log a refresh token event"""
    event = UserEvent(user_id=user_id, event_type=EventType.REFRESH_TOKEN)
    return log_user_event(event)


def log_learning_activity(
    user_id: str, event_type: EventType, activity_id: str = None, details: dict = None
) -> dict:
    """Log a learning activity event"""
    event = UserEvent(
        user_id=user_id, event_type=event_type, event_id=activity_id, details=details
    )
    return log_user_event(event)


def get_user_events(
    user_id: str, event_type: EventType = None, limit: int = 50
) -> list:
    """Get user events, optionally filtered by event type"""
    query = {"user_id": user_id}
    if event_type:
        query["event_type"] = event_type

    events = list(user_events_table.find(query).sort("timestamp", -1).limit(limit))

    # Convert ObjectId to string
    for event in events:
        event["_id"] = str(event["_id"])

    return events


def log_app_open(user_id: str) -> dict:
    """Log when the application is opened by a user"""
    event = UserEvent(user_id=user_id, event_type=EventType.APP_OPEN)
    return log_user_event(event)


def get_recent_learning_events(user_id: str, days: int = 5) -> list:
    """
    Son belirli gün sayısı içindeki öğrenme etkinliklerini getirir
    (PYRAMID, VOCABULARY, WRITING, EMAIL tipindeki eventler)

    Args:
        user_id (str): Kullanıcı ID
        days (int, optional): Kaç günlük veri getirileceği. Varsayılan 5.

    Returns:
        list: Event listesi, timestamp'e göre azalan sırada
    """
    # Son 'days' günün timestamp'ini hesapla
    cutoff_date = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=days)

    # Öğrenme event tipleri
    learning_event_types = [
        EventType.PYRAMID.value,
        EventType.VOCABULARY.value,
        EventType.WRITING.value,
        EventType.EMAIL.value,
    ]

    # MongoDB sorgusu
    query = {
        "user_id": user_id,
        "event_type": {"$in": learning_event_types},
        "timestamp": {"$gte": cutoff_date},
    }

    events = list(user_events_table.find(query).sort("timestamp", -1))

    # ObjectId'leri string'e çevir
    for event in events:
        event["_id"] = str(event["_id"])

    return events


##########################################
###### Vocabulary Event Functions ########
##########################################


def create_vocabulary_event(user_id: str, vocabulary_list_id: str, words: list) -> dict:
    """
    Create a new vocabulary event when a user starts working on a vocabulary list

    Args:
        user_id (str): User ID
        vocabulary_list_id (str): ID of the vocabulary list
        words (list): List of words in the vocabulary list

    Returns:
        dict: Created event
    """
    vocab_event = VocabularyEvent(
        user_id=user_id, vocabulary_list_id=vocabulary_list_id, words=words
    )

    return log_user_event(vocab_event)


def update_vocabulary_event(event_id: str, update_data: dict) -> dict:
    """
    Update an existing vocabulary event with new statistics

    Args:
        event_id (str): Vocabulary event ID
        update_data (dict): Dictionary with fields to update

    Returns:
        dict: Updated event or None if not found
    """
    if not ObjectId.is_valid(event_id):
        return None

    # Create the update dictionary for the details field
    details_update = {}
    for key, value in update_data.items():
        details_update[f"details.{key}"] = value

    # Update the event
    result = user_events_table.update_one(
        {"_id": ObjectId(event_id)}, {"$set": details_update}
    )

    if result.modified_count > 0:
        # Get the updated event
        updated_event = user_events_table.find_one({"_id": ObjectId(event_id)})
        if updated_event:
            updated_event["_id"] = str(updated_event["_id"])
            return updated_event
    return None


def get_vocabulary_event(event_id: str) -> dict:
    """
    Get a vocabulary event by ID

    Args:
        event_id (str): Vocabulary event ID

    Returns:
        dict: Event data or None if not found
    """
    if not ObjectId.is_valid(event_id):
        return None

    event = user_events_table.find_one(
        {"_id": ObjectId(event_id), "event_type": EventType.VOCABULARY}
    )

    if event:
        event["_id"] = str(event["_id"])
        return event
    return None


def get_vocabulary_event_by_list_id(user_id: str, vocabulary_list_id: str) -> dict:
    """
    Get the most recent vocabulary event for a specific list and user

    Args:
        user_id (str): User ID
        vocabulary_list_id (str): Vocabulary list ID

    Returns:
        dict: Most recent event or None if not found
    """
    # Get the most recent event for this list
    event = user_events_table.find_one(
        {
            "user_id": user_id,
            "event_type": EventType.VOCABULARY,
            "event_id": vocabulary_list_id,
        },
        sort=[("timestamp", -1)],
    )

    if event:
        event["_id"] = str(event["_id"])
        return event
    return None


async def complete_vocabulary_event(event_id: str) -> dict:
    """
    Mark a vocabulary event as completed and calculate XP

    Args:
        event_id (str): Vocabulary event ID

    Returns:
        dict: Updated event with XP calculation
    """
    if not ObjectId.is_valid(event_id):
        return None

    # Get the current event
    event = user_events_table.find_one(
        {"_id": ObjectId(event_id), "event_type": EventType.VOCABULARY}
    )

    if not event:
        return None

    # Create a VocabularyEvent object to use its methods
    # Convert the MongoDB document to a VocabularyEvent
    event_copy = event.copy()
    event_copy["_id"] = str(event_copy["_id"])  # Convert ObjectId to string

    # Move details fields to top-level for the VocabularyEvent constructor
    if "details" in event_copy and isinstance(event_copy["details"], dict):
        for key, value in event_copy["details"].items():
            event_copy[key] = value

    vocab_event = VocabularyEvent(**event_copy)

    # Calculate accuracy
    vocab_event.calculate_accuracy()

    # Mark as completed
    vocab_event.completed = True

    # Calculate XP
    earned_xp = vocab_event.calculate_xp()

    # Update the event in the database
    updated_data = {
        "details.accuracy_rate": vocab_event.accuracy_rate,
        "details.completed": True,
        "details.xp_earned": earned_xp,
    }

    result = user_events_table.update_one(
        {"_id": ObjectId(event_id)}, {"$set": updated_data}
    )

    if result.modified_count > 0:
        # Add XP to user
        if earned_xp > 0:
            user_id = event["user_id"]
            current_xp = await get_xp(user_id)
            if current_xp:
                await update_xp(user_id, current_xp["xp"] + earned_xp)

        # Log a learning activity summary event
        log_learning_activity(
            user_id=event["user_id"],
            event_type=EventType.VOCABULARY,
            activity_id=event["event_id"],
            details={
                "completed": True,
                "accuracy_rate": vocab_event.accuracy_rate,
                "xp_earned": earned_xp,
                "duration_seconds": vocab_event.duration_seconds,
                "total_hints": vocab_event.total_hints,
                "summary": True,  # Flag to indicate this is a summary event
            },
        )

        # Return the updated event
        updated_event = user_events_table.find_one({"_id": ObjectId(event_id)})
        if updated_event:
            updated_event["_id"] = str(updated_event["_id"])
            return updated_event

    return None


def get_recent_completed_vocabulary_events(user_id: str, days: int = 5) -> list:
    """
    Get completed vocabulary events for a user within the specified number of days

    Args:
        user_id (str): User ID
        days (int): Number of days to look back

    Returns:
        list: List of completed vocabulary events
    """
    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Query for completed events
    query = {
        "user_id": user_id,
        "event_type": EventType.VOCABULARY,
        "details.completed": True,
        "timestamp": {"$gte": cutoff_date},
    }

    events = list(user_events_table.find(query).sort("timestamp", -1))

    # Convert ObjectId to string
    for event in events:
        event["_id"] = str(event["_id"])

    return events


##########################################
######## Pyramid Event Functions #########
##########################################


def create_pyramid_event(user_id: str, pyramid_id: str) -> dict:
    """
    Create a new pyramid event when a user starts working on a pyramid

    Args:
        user_id (str): User ID
        pyramid_id (str): ID of the pyramid

    Returns:
        dict: Created event
    """
    pyramid_event = PyramidEvent(
        user_id=user_id,
        pyramid_id=pyramid_id,
        session_start=datetime.utcnow(),
        completed=False,
        total_steps=0,
        completed_steps=0,
        step_types=[],
        steps_detail=[],
        accuracy_rate=0.0,
        avg_time_per_step=0.0,
        duration_seconds=0,
        xp_earned=0
    )

    return log_user_event(pyramid_event)


def add_pyramid_step(event_id: str, step: PyramidItem, step_type: str) -> dict:
    """
    Add a pyramid step to an existing pyramid event

    Args:
        event_id (str): Pyramid event ID
        step (PyramidItem): Pyramid item to add to steps
        step_type (str): Type of step (shrink, expand, replace, paraphrase)

    Returns:
        dict: Updated event or None if not found
    """
    if not ObjectId.is_valid(event_id):
        return None

    # Convert the step to dict for storage
    step_dict = step.model_dump() if hasattr(step, "model_dump") else step
    
    # Add timestamp to step
    step_dict["timestamp"] = datetime.utcnow().isoformat()

    # Add the step to the steps array and increment counters
    result = user_events_table.update_one(
        {"_id": ObjectId(event_id)},
        {
            "$push": {
                "details.steps_detail": step_dict,
                "details.step_types": step_type
            },
            "$inc": {
                "details.total_steps": 1,
                "details.completed_steps": 1
            },
            "$set": {
                "details.last_step_timestamp": int(datetime.utcnow().timestamp())
            },
        },
    )

    if result.modified_count > 0:
        # Get the updated event
        updated_event = user_events_table.find_one({"_id": ObjectId(event_id)})
        if updated_event:
            updated_event["_id"] = str(updated_event["_id"])
            return updated_event
    return None


def update_pyramid_event(event_id: str, update_data: dict) -> dict:
    """
    Update an existing pyramid event with new statistics

    Args:
        event_id (str): Pyramid event ID
        update_data (dict): Dictionary with fields to update

    Returns:
        dict: Updated event or None if not found
    """
    if not ObjectId.is_valid(event_id):
        return None

    # Create the update dictionary for the details field
    details_update = {}
    for key, value in update_data.items():
        details_update[f"details.{key}"] = value

    # Update the event
    result = user_events_table.update_one(
        {"_id": ObjectId(event_id)}, {"$set": details_update}
    )

    if result.modified_count > 0:
        # Get the updated event
        updated_event = user_events_table.find_one({"_id": ObjectId(event_id)})
        if updated_event:
            updated_event["_id"] = str(updated_event["_id"])
            return updated_event
    return None


def get_pyramid_event(event_id: str) -> dict:
    """
    Get a pyramid event by ID

    Args:
        event_id (str): Pyramid event ID

    Returns:
        dict: Event data or None if not found
    """
    if not ObjectId.is_valid(event_id):
        return None

    event = user_events_table.find_one(
        {"_id": ObjectId(event_id), "event_type": EventType.PYRAMID}
    )

    if event:
        event["_id"] = str(event["_id"])
        return event
    return None


def get_pyramid_event_by_id(user_id: str, pyramid_id: str) -> dict:
    """
    Get the most recent pyramid event for a specific pyramid and user

    Args:
        user_id (str): User ID
        pyramid_id (str): Pyramid ID

    Returns:
        dict: Most recent event or None if not found
    """
    # Get the most recent event for this pyramid
    event = user_events_table.find_one(
        {"user_id": user_id, "event_type": EventType.PYRAMID, "event_id": pyramid_id},
        sort=[("timestamp", -1)],
    )

    if event:
        event["_id"] = str(event["_id"])
        return event
    return None


async def complete_pyramid_event(event_id: str) -> dict:
    """
    Mark a pyramid event as completed and calculate XP

    Args:
        event_id (str): Pyramid event ID

    Returns:
        dict: Updated event with XP calculation
    """
    if not ObjectId.is_valid(event_id):
        return None

    # Get the current event
    event = user_events_table.find_one(
        {"_id": ObjectId(event_id), "event_type": EventType.PYRAMID}
    )

    if not event:
        return None

    # Create a PyramidEvent object to use its methods
    # Convert the MongoDB document to a PyramidEvent
    event_copy = event.copy()
    event_copy["_id"] = str(event_copy["_id"])  # Convert ObjectId to string

    # Move details fields to top-level for the PyramidEvent constructor
    if "details" in event_copy and isinstance(event_copy["details"], dict):
        for key, value in event_copy["details"].items():
            event_copy[key] = value

    pyramid_event = PyramidEvent(**event_copy)

    # Set completion data
    pyramid_event.session_end = datetime.utcnow()
    pyramid_event.completed = True

    # Calculate session duration
    pyramid_event.calculate_session_duration()

    # Calculate accuracy (completed steps vs total steps)
    pyramid_event.calculate_accuracy()

    # Calculate average time per step
    pyramid_event.calculate_avg_time_per_step()

    # Calculate XP
    earned_xp = pyramid_event.calculate_xp()

    # Update the event in the database
    updated_data = {
        "details.session_end": pyramid_event.session_end.isoformat(),
        "details.completed": True,
        "details.duration_seconds": pyramid_event.duration_seconds,
        "details.accuracy_rate": pyramid_event.accuracy_rate,
        "details.avg_time_per_step": pyramid_event.avg_time_per_step,
        "details.xp_earned": earned_xp,
    }

    result = user_events_table.update_one(
        {"_id": ObjectId(event_id)}, {"$set": updated_data}
    )

    if result.modified_count > 0:
        # Add XP to user
        if earned_xp > 0:
            user_id = event["user_id"]
            current_xp = await get_xp(user_id)
            if current_xp:
                await update_xp(user_id, current_xp["xp"] + earned_xp)

        # Log a learning activity summary event
        log_learning_activity(
            user_id=event["user_id"],
            event_type=EventType.PYRAMID,
            activity_id=event["event_id"],
            details={
                "completed": True,
                "xp_earned": earned_xp,
                "duration_seconds": pyramid_event.duration_seconds,
                "accuracy_rate": pyramid_event.accuracy_rate,
                "avg_time_per_step": pyramid_event.avg_time_per_step,
                "total_steps": pyramid_event.total_steps,
                "completed_steps": pyramid_event.completed_steps,
                "step_types": pyramid_event.step_types,
                "summary": True,  # Flag to indicate this is a summary event
            },
        )

        # Return the updated event
        updated_event = user_events_table.find_one({"_id": ObjectId(event_id)})
        if updated_event:
            updated_event["_id"] = str(updated_event["_id"])
            return updated_event
    return None


def get_recent_completed_pyramid_events(user_id: str, days: int = 5) -> list:
    """
    Get completed pyramid events for a user within the specified number of days

    Args:
        user_id (str): User ID
        days (int): Number of days to look back

    Returns:
        list: List of completed pyramid events
    """
    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Query for completed events
    query = {
        "user_id": user_id,
        "event_type": EventType.PYRAMID,
        "details.completed": True,
        "timestamp": {"$gte": cutoff_date},
    }

    events = list(user_events_table.find(query).sort("timestamp", -1))

    # Convert ObjectId to string
    for event in events:
        event["_id"] = str(event["_id"])

    return events


##########################################
####### Writing Event Functions #########
##########################################


def create_writing_event(user_id: str, question_id: str, question_text: str, level: str) -> dict:
    """
    Create a new writing event when a user starts working on a writing question

    Args:
        user_id (str): User ID
        question_id (str): ID of the writing question
        question_text (str): Text of the writing question
        level (str): Difficulty level of the question

    Returns:
        dict: Created event
    """
    writing_event = WritingEvent(
        user_id=user_id,
        question_id=question_id,
        question_text=question_text,
        level=level,
        session_start=datetime.utcnow(),
        completed=False,
        word_count=0,
        character_count=0,
        revision_count=0,
        duration_seconds=0,
        xp_earned=0
    )

    return log_user_event(writing_event)


def update_writing_event(event_id: str, update_data: dict) -> dict:
    """
    Update an existing writing event with new statistics

    Args:
        event_id (str): Writing event ID
        update_data (dict): Dictionary with fields to update

    Returns:
        dict: Updated event or None if not found
    """
    if not ObjectId.is_valid(event_id):
        return None

    # Create the update dictionary for the details field
    details_update = {}
    for key, value in update_data.items():
        details_update[f"details.{key}"] = value

    # Update the event
    result = user_events_table.update_one(
        {"_id": ObjectId(event_id)}, {"$set": details_update}
    )

    if result.modified_count > 0:
        # Get the updated event
        updated_event = user_events_table.find_one({"_id": ObjectId(event_id)})
        if updated_event:
            updated_event["_id"] = str(updated_event["_id"])
            return updated_event
    return None


def get_writing_event(event_id: str) -> dict:
    """
    Get a writing event by ID

    Args:
        event_id (str): Writing event ID

    Returns:
        dict: Event data or None if not found
    """
    if not ObjectId.is_valid(event_id):
        return None

    event = user_events_table.find_one(
        {"_id": ObjectId(event_id), "event_type": EventType.WRITING}
    )

    if event:
        event["_id"] = str(event["_id"])
        return event
    return None


def get_writing_event_by_question_id(user_id: str, question_id: str) -> dict:
    """
    Get the most recent writing event for a specific question and user

    Args:
        user_id (str): User ID
        question_id (str): Writing question ID

    Returns:
        dict: Most recent event or None if not found
    """
    # Get the most recent event for this question
    event = user_events_table.find_one(
        {
            "user_id": user_id,
            "event_type": EventType.WRITING,
            "event_id": question_id,
        },
        sort=[("timestamp", -1)],
    )

    if event:
        event["_id"] = str(event["_id"])
        return event
    return None


async def complete_writing_event(event_id: str, final_answer: str, ai_feedback: dict) -> dict:
    """
    Mark a writing event as completed and calculate XP

    Args:
        event_id (str): Writing event ID
        final_answer (str): User's final answer text
        ai_feedback (dict): AI evaluation feedback

    Returns:
        dict: Updated event with XP calculation
    """
    if not ObjectId.is_valid(event_id):
        return None

    # Get the current event
    event = user_events_table.find_one(
        {"_id": ObjectId(event_id), "event_type": EventType.WRITING}
    )

    if not event:
        return None

    # Create a WritingEvent object to use its methods
    # Convert the MongoDB document to a WritingEvent
    event_copy = event.copy()
    event_copy["_id"] = str(event_copy["_id"])  # Convert ObjectId to string

    # Move details fields to top-level for the WritingEvent constructor
    if "details" in event_copy and isinstance(event_copy["details"], dict):
        for key, value in event_copy["details"].items():
            event_copy[key] = value

    writing_event = WritingEvent(**event_copy)

    # Set completion data
    writing_event.session_end = datetime.utcnow()
    writing_event.completed = True
    writing_event.final_answer = final_answer
    writing_event.ai_feedback = ai_feedback
    
    # Calculate word and character counts
    writing_event.word_count = len(final_answer.split())
    writing_event.character_count = len(final_answer)

    # Calculate session duration
    writing_event.calculate_session_duration()

    # Calculate XP
    earned_xp = writing_event.calculate_xp()

    # Update the event in the database
    updated_data = {
        "details.session_end": writing_event.session_end.isoformat(),
        "details.completed": True,
        "details.final_answer": final_answer,
        "details.ai_feedback": ai_feedback,
        "details.word_count": writing_event.word_count,
        "details.character_count": writing_event.character_count,
        "details.duration_seconds": writing_event.duration_seconds,
        "details.xp_earned": earned_xp,
    }

    result = user_events_table.update_one(
        {"_id": ObjectId(event_id)}, {"$set": updated_data}
    )

    if result.modified_count > 0:
        # Add XP to user
        if earned_xp > 0:
            user_id = event["user_id"]
            current_xp = await get_xp(user_id)
            if current_xp:
                await update_xp(user_id, current_xp["xp"] + earned_xp)

        # Save question response to writing_table to mark as solved
        try:
            # Create a DetailedWritingResponse from the ai_feedback
            evaluation_details = WritingEvaluationDetails(
                content_score=ai_feedback.get("content_score", 0),
                organization_score=ai_feedback.get("organization_score", 0), 
                language_score=ai_feedback.get("language_score", 0),
                total_score=ai_feedback.get("total_score", 0),
                xp_earned=earned_xp
            )
            
            evaluation = DetailedWritingResponse(
                score=int((ai_feedback.get("total_score", 0) / 15) * 100),  # Convert to 0-100 scale
                feedback=ai_feedback.get("feedback", ""),
                details=evaluation_details
            )
            
            # Create question response record
            question_response = WritingQuestionResponse.from_evaluation(
                user_id=event["user_id"],
                question_id=writing_event.question_id,
                level=writing_event.level,
                question_text=writing_event.question_text or "",
                user_answer=final_answer,
                evaluation=evaluation
            )
            
            # Save to writing_table to mark question as solved
            question_response_dict = question_response.model_dump()
            writing_table.replace_one(
                {"user_id": event["user_id"], "question_id": writing_event.question_id, "level": writing_event.level},
                question_response_dict,
                upsert=True
            )
        except Exception as e:
            print(f"Warning: Failed to save writing question response: {str(e)}")
            # Don't fail the entire function if this fails

        # Log a learning activity summary event
        log_learning_activity(
            user_id=event["user_id"],
            event_type=EventType.WRITING,
            activity_id=event["event_id"],
            details={
                "completed": True,
                "xp_earned": earned_xp,
                "duration_seconds": writing_event.duration_seconds,
                "word_count": writing_event.word_count,
                "level": writing_event.level,
                "summary": True,  # Flag to indicate this is a summary event
            },
        )

        # Return the updated event
        updated_event = user_events_table.find_one({"_id": ObjectId(event_id)})
        if updated_event:
            updated_event["_id"] = str(updated_event["_id"])
            return updated_event

    return None


def get_recent_completed_writing_events(user_id: str, days: int = 5) -> list:
    """
    Get completed writing events for a user within the specified number of days

    Args:
        user_id (str): User ID
        days (int): Number of days to look back

    Returns:
        list: List of completed writing events
    """
    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Query for completed events
    query = {
        "user_id": user_id,
        "event_type": EventType.WRITING,
        "details.completed": True,
        "timestamp": {"$gte": cutoff_date},
    }

    events = list(user_events_table.find(query).sort("timestamp", -1))

    # Convert ObjectId to string
    for event in events:
        event["_id"] = str(event["_id"])

    return events


def update_writing_progress(event_id: str, word_count: int, character_count: int, revision_count: int) -> dict:
    """
    Update writing progress during an active session

    Args:
        event_id (str): Writing event ID
        word_count (int): Current word count
        character_count (int): Current character count
        revision_count (int): Number of revisions made

    Returns:
        dict: Updated event or None if not found
    """
    if not ObjectId.is_valid(event_id):
        return None

    # Update the progress data
    update_data = {
        "details.word_count": word_count,
        "details.character_count": character_count,
        "details.revision_count": revision_count,
        "details.last_activity": datetime.utcnow().isoformat(),
    }

    result = user_events_table.update_one(
        {"_id": ObjectId(event_id)}, {"$set": update_data}
    )

    if result.modified_count > 0:
        # Get the updated event
        updated_event = user_events_table.find_one({"_id": ObjectId(event_id)})
        if updated_event:
            updated_event["_id"] = str(updated_event["_id"])
            return updated_event
    return None
