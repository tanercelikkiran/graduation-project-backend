from fastapi import APIRouter, Depends, Body
from src.services.saved_sentence_service import (
    save_sentence,
    unsave_sentence,
    get_saved_sentences,
    is_sentence_saved,
    get_saved_sentences_count
)
from src.services.authentication_service import verify_token
from src.services.content_check_service import check_user_content
from src.models.saved_sentence import (
    SaveSentenceRequest,
    DeleteSavedSentenceRequest,
    CheckSavedSentenceRequest
)

router = APIRouter(prefix="/saved-sentences", tags=["Saved Sentences"])


@router.post("/save")
async def save_sentence_endpoint(
    save_data: SaveSentenceRequest, current_user=Depends(verify_token)
):
    """
    Save a sentence to the user's saved sentences list
    """
    # Check content appropriateness
    if save_data.sentence:
        check_user_content(save_data.sentence, "sentence", str(current_user.id))
    if save_data.meaning:
        check_user_content(save_data.meaning, "sentence", str(current_user.id))
    if save_data.source_sentence:
        check_user_content(save_data.source_sentence, "sentence", str(current_user.id))
    
    return save_sentence(current_user.id, save_data)


@router.delete("/delete")
async def delete_saved_sentence_endpoint(
    delete_data: DeleteSavedSentenceRequest, current_user=Depends(verify_token)
):
    """
    Remove a saved sentence from the user's saved sentences list
    """
    return unsave_sentence(
        current_user.id, 
        delete_data.sentence, 
        delete_data.meaning
    )


@router.get("/get")
async def get_saved_sentences_endpoint(current_user=Depends(verify_token)):
    """
    Get all saved sentences for a user
    """
    return get_saved_sentences(current_user.id)


@router.post("/check")
async def check_saved_sentence_endpoint(
    check_data: CheckSavedSentenceRequest, current_user=Depends(verify_token)
):
    """
    Check if a sentence is saved by the user
    """
    return is_sentence_saved(
        current_user.id,
        check_data.sentence,
        check_data.meaning
    )


@router.get("/count")
async def get_saved_sentences_count_endpoint(current_user=Depends(verify_token)):
    """
    Get the count of saved sentences for a user
    """
    count = get_saved_sentences_count(current_user.id)
    return {
        "status": "success",
        "count": count
    }