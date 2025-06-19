from fastapi import APIRouter, Depends, Body
from src.services.vocabulary_service import (
    create_vocabulary,
    return_test_data,
    track_hint_usage,
    track_attempt_result,
    get_difficult_words,
    get_word_statistics,
    save_vocabulary,
    unsave_vocabulary,
    get_saved_vocabularies,
    is_vocabulary_saved,
    get_user_vocabulary_lists,
    rework_vocabulary_list,
    delete_vocabulary_list,
    get_popular_vocabularies,
)
from src.services.authentication_service import verify_token
from src.services.content_check_service import check_user_content
from src.models.vocabulary import HintUsageRequest, AttemptResult, SaveVocabularyRequest
from src.services.event_service import (
    create_vocabulary_event,
    update_vocabulary_event,
    get_vocabulary_event,
    get_vocabulary_event_by_list_id,
    complete_vocabulary_event,
)
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/vocabulary", tags=["Vocabulary"])


@router.post("/create")
def create_vocabulary_endpoint(
    data: dict = Body(...), current_user=Depends(verify_token)
):
    system_language = data.get(
        "system_language", "English"
    )  # Default to English if not provided
    return create_vocabulary(current_user.id, system_language)


@router.get("/test")
def test_vocabulary_endpoint(current_user=Depends(verify_token)):
    return return_test_data(current_user.id)


@router.post("/track-hint")
def track_hint_endpoint(
    hint_data: HintUsageRequest, current_user=Depends(verify_token)
):
    """
    Track when a user uses a hint (letter, relevant word, or emoji)
    to identify words they're struggling with
    """
    return track_hint_usage(current_user.id, hint_data)


@router.post("/track-attempt")
def track_attempt_endpoint(
    attempt_data: AttemptResult, current_user=Depends(verify_token)
):
    """
    Track when a user attempts to answer a word (success or failure)
    """
    return track_attempt_result(current_user.id, attempt_data)


@router.get("/difficult-words")
def get_difficult_words_endpoint(current_user=Depends(verify_token)):
    """
    Get a list of words the user has had difficulty with
    """
    difficult_words = get_difficult_words(current_user.id)

    # Ensure each word has relevantWords and emoji fields
    for word in difficult_words:
        if "relevantWords" not in word or not word["relevantWords"]:
            word["relevantWords"] = [
                "related1",
                "related2",
                "related3",
                "related4",
                "related5",
            ]
        if "emoji" not in word or not word["emoji"]:
            word["emoji"] = "📚"

    return difficult_words


@router.get("/statistics")
def get_word_statistics_endpoint(current_user=Depends(verify_token)):
    """
    Get statistics for all words a user has interacted with
    """
    return get_word_statistics(current_user.id)


@router.post("/save")
def save_vocabulary_endpoint(
    save_data: SaveVocabularyRequest, current_user=Depends(verify_token)
):
    """
    Save a vocabulary word to the user's saved_vocabularies list
    """
    # Check content appropriateness
    if save_data.word:
        check_user_content(save_data.word, "vocabulary", str(current_user.id))
    if save_data.meaning:
        check_user_content(save_data.meaning, "vocabulary", str(current_user.id))
    if save_data.relevantWords:
        for relevant_word in save_data.relevantWords:
            if relevant_word:
                check_user_content(relevant_word, "vocabulary", str(current_user.id))
    
    return save_vocabulary(current_user.id, save_data)


@router.delete("/delete/saved")
def unsave_vocabulary_endpoint(
    data: dict = Body(...), current_user=Depends(verify_token)
):
    """
    Remove a saved vocabulary word from the user's saved_vocabularies list
    """
    word = data.get("word")
    meaning = data.get("meaning")

    if not word or not meaning:
        return {"status": "error", "message": "Word and meaning are required"}

    return unsave_vocabulary(current_user.id, word, meaning)


@router.get("/get/saved")
def get_saved_vocabularies_endpoint(current_user=Depends(verify_token)):
    """
    Get all saved vocabularies for a user
    """
    return get_saved_vocabularies(current_user.id)


@router.post("/check/saved")
def check_saved_vocabulary_endpoint(
    data: dict = Body(...), current_user=Depends(verify_token)
):
    """
    Check if a vocabulary word is saved (bookmarked) by the user
    """
    word = data.get("word")
    meaning = data.get("meaning")

    if not word or not meaning:
        return {
            "status": "error",
            "message": "Word and meaning are required",
            "isBookmarked": False,
        }

    return is_vocabulary_saved(current_user.id, word, meaning)


@router.get("/user-lists")
def get_user_vocabulary_lists_endpoint(current_user=Depends(verify_token)):
    """
    Get all vocabulary lists created by a user
    """
    return get_user_vocabulary_lists(current_user.id)


# Define models for the vocabulary event endpoints
class CreateVocabEventRequest(BaseModel):
    vocabulary_list_id: str
    words: List[str]


class UpdateVocabEventRequest(BaseModel):
    event_id: str
    hint_type: Optional[str] = None
    duration_seconds: Optional[int] = None
    is_correct: Optional[bool] = None


@router.post("/event/create")
def create_vocabulary_event_endpoint(
    event_data: CreateVocabEventRequest, current_user=Depends(verify_token)
):
    """
    Create a new vocabulary event to track user progress through a vocabulary list
    """
    event = create_vocabulary_event(
        user_id=current_user.id,
        vocabulary_list_id=event_data.vocabulary_list_id,
        words=event_data.words,
    )

    if not event:
        return {"status": "error", "message": "Failed to create vocabulary event"}

    return {"status": "success", "event": event}


@router.post("/event/update")
def update_vocabulary_event_endpoint(
    update_data: UpdateVocabEventRequest, current_user=Depends(verify_token)
):
    """
    Update a vocabulary event with new statistics
    """
    # Get the current event
    event = get_vocabulary_event(update_data.event_id)
    if not event or event.get("user_id") != current_user.id:
        return {"status": "error", "message": "Vocabulary event not found"}

    # Create update dictionary
    update_dict = {}

    # Update duration if provided
    if update_data.duration_seconds is not None:
        update_dict["duration_seconds"] = update_data.duration_seconds

    # Update hint counts if provided
    if update_data.hint_type:
        if update_data.hint_type == "letter":
            update_dict["letter_hints_used"] = event.get("letter_hints_used", 0) + 1
            update_dict["total_hints"] = event.get("total_hints", 0) + 1
        elif update_data.hint_type == "relevant_word":
            update_dict["relevant_word_hints_used"] = (
                event.get("relevant_word_hints_used", 0) + 1
            )
            update_dict["total_hints"] = event.get("total_hints", 0) + 1
        elif update_data.hint_type == "emoji":
            update_dict["emoji_hints_used"] = event.get("emoji_hints_used", 0) + 1
            update_dict["total_hints"] = event.get("total_hints", 0) + 1

    # Update attempt counts if provided
    if update_data.is_correct is not None:
        if update_data.is_correct:
            update_dict["correct_answers"] = event.get("correct_answers", 0) + 1
        else:
            update_dict["incorrect_answers"] = event.get("incorrect_answers", 0) + 1

    # If there's nothing to update, return success
    if not update_dict:
        return {"status": "success", "message": "No updates provided"}

    # Update the event
    updated_event = update_vocabulary_event(update_data.event_id, update_dict)
    if not updated_event:
        return {"status": "error", "message": "Failed to update vocabulary event"}

    return {"status": "success", "event": updated_event}


@router.post("/event/complete")
async def complete_vocabulary_event_endpoint(
    data: dict = Body(...), current_user=Depends(verify_token)
):
    """
    Mark a vocabulary event as completed, calculate XP, and add it to the user's XP
    """
    event_id = data.get("event_id")
    if not event_id:
        return {"status": "error", "message": "Event ID is required"}

    # Get the event to verify ownership
    event = get_vocabulary_event(event_id)
    if not event or event.get("user_id") != current_user.id:
        return {"status": "error", "message": "Vocabulary event not found"}

    # Complete the event
    completed_event = await complete_vocabulary_event(event_id)
    if not completed_event:
        return {"status": "error", "message": "Failed to complete vocabulary event"}

    return {
        "status": "success",
        "event": completed_event,
        "xp_earned": completed_event.get("xp_earned", 0),
    }


@router.get("/event/{vocabulary_list_id}")
def get_vocabulary_event_endpoint(
    vocabulary_list_id: str, current_user=Depends(verify_token)
):
    """
    Get the most recent vocabulary event for a specific vocabulary list
    """
    event = get_vocabulary_event_by_list_id(current_user.id, vocabulary_list_id)
    if not event:
        return {"status": "error", "message": "Vocabulary event not found"}

    return {"status": "success", "event": event}


@router.post("/rework/{vocabulary_list_id}")
def rework_vocabulary_list_endpoint(
    vocabulary_list_id: str, current_user=Depends(verify_token)
):
    """
    Rework a vocabulary list and return the shuffled words
    """
    try:
        result = rework_vocabulary_list(vocabulary_list_id, current_user.id)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@router.delete("/delete/{vocabulary_list_id}")
def delete_vocabulary_list_endpoint(
    vocabulary_list_id: str, current_user=Depends(verify_token)
):
    """
    Delete a vocabulary list and remove it from the user's list
    """
    try:
        result = delete_vocabulary_list(vocabulary_list_id, current_user.id)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@router.get("/popular")
def get_popular_vocabularies_endpoint(current_user=Depends(verify_token)):
    """
    Get popular vocabulary lists based on user's learning and system languages
    """
    return get_popular_vocabularies(current_user.id)
