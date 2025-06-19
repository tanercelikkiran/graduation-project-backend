from fastapi import APIRouter, Depends, HTTPException, Query
from src.services.authentication_service import verify_token
from src.services.content_check_service import check_user_content
from src.models.writing import (
    DetailedWritingResponse, 
    WritingEvaluationRequest, 
    WritingAnswerRequest,
    WritingAnswerResponse,
    WritingQuestionsResponse,
    WritingScenarioAnswerRequest,
    WritingScenarioAnswerResponse
)
from src.models.user import UserOut
from src.services.writing_service import (
    evaluate_writing_submission, 
    answer_writing_question,
    answer_writing_question_with_scenarios,
    get_user_question_response,
    get_all_writing_levels,
    get_user_writing_progress,
    get_writing_questions_with_status,
    get_first_unsolved_question
)
from src.services.event_service import (
    create_writing_event,
    get_writing_event,
    get_writing_event_by_question_id,
    update_writing_progress,
    complete_writing_event,
    get_recent_completed_writing_events
)
from typing import Optional

router = APIRouter(prefix="/writing", tags=["Writing Evaluation"])

@router.post("/evaluate", response_model=DetailedWritingResponse)
async def evaluate_writing(
    request: WritingEvaluationRequest,
    user: Optional[UserOut] = Depends(verify_token),
):
    """
    Evaluate a piece of writing using Gemini AI.
    
    This endpoint accepts a text to evaluate along with an optional question/prompt.
    If the user is authenticated, they will earn XP based on their score.
    """
    try:
        # Check content appropriateness for user text only
        if request.text:
            check_user_content(request.text, "writing", str(user.id) if user else None)
        
        # Get user_id if user is authenticated
        user_id = str(user.id) if user else None
        
        # Use writing service to evaluate text
        result = await evaluate_writing_submission(
            user_text=request.text,
            question=request.question,
            user_id=user_id,
            learning_language=user.learning_language if user else "English",
            system_language=user.system_language if user else "English"
        )
        
        return result
    except Exception as e:
        print(f"Error in writing evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to evaluate writing")

@router.post("/evaluate/guest", response_model=DetailedWritingResponse)
async def evaluate_writing_guest(request: WritingEvaluationRequest):
    """
    Evaluate a piece of writing for guest users (no XP awarded).
    
    This endpoint doesn't require authentication and is suitable for demo purposes
    or users who haven't yet registered.
    """
    try:
        # Check content appropriateness for user text only
        if request.text:
            check_user_content(request.text, "writing")
        
        # Use writing service to evaluate text without user_id (no XP awarded)
        # For guest users, default to English for both languages
        result = await evaluate_writing_submission(
            user_text=request.text,
            question=request.question,
            learning_language="English",
            system_language="English"
        )
        
        return result
    except Exception as e:
        print(f"Error in guest writing evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to evaluate writing")

@router.post("/answer", response_model=WritingAnswerResponse)
async def answer_writing_question_endpoint(
    request: WritingAnswerRequest,
    user: UserOut = Depends(verify_token)
):
    """
    Submit an answer to a specific writing question.
    
    The question will be presented in user's system language,
    and the answer will be evaluated based on the learning language.
    
    Parameters:
    - request: Contains question_id, level, and answer text
    """
    try:
        # Check content appropriateness
        if request.answer:
            check_user_content(request.answer, "writing", str(user.id))
        
        result = await answer_writing_question(
            user_id=str(user.id),
            question_id=request.question_id,
            level=request.level,
            answer=request.answer,
            system_language=user.system_language,
            learning_language=user.learning_language
        )
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail="Question not found or could not process answer"
            )
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error answering writing question: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process writing answer")

@router.post("/answer-scenarios", response_model=WritingScenarioAnswerResponse)
async def answer_writing_question_scenarios_endpoint(
    request: WritingScenarioAnswerRequest,
    user: UserOut = Depends(verify_token)
):
    """
    Submit answers to multiple scenarios in a writing question.
    
    The question will be presented in user's learning language,
    and the answers will be evaluated as a combined response.
    
    Parameters:
    - request: Contains question_id, level, and list of scenario answers
    """
    try:
        # Check content appropriateness for all scenario answers
        if request.scenario_answers:
            for scenario_answer in request.scenario_answers:
                if scenario_answer.answer:
                    check_user_content(scenario_answer.answer, "writing", str(user.id))
        
        print(f"DEBUG: Received scenario answer request for question {request.question_id}, level {request.level}")
        print(f"DEBUG: Number of scenario answers: {len(request.scenario_answers)}")
        result = await answer_writing_question_with_scenarios(
            user_id=str(user.id),
            request=request,
            system_language=user.system_language,
            learning_language=user.learning_language
        )
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail="Question not found or could not process scenario answers"
            )
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error answering writing question with scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process writing scenario answers")

@router.get("/answer/{level}/{question_id}")
async def get_user_answer(
    level: str,
    question_id: str,
    user: UserOut = Depends(verify_token)
):
    """
    Get user's previous answer to a specific writing question.
    
    Parameters:
    - level: The question level
    - question_id: The ID of the question
    """
    try:
        response = get_user_question_response(
            user_id=str(user.id),
            question_id=question_id,
            level=level
        )
        
        if not response:
            raise HTTPException(
                status_code=404, 
                detail="No answer found for this question"
            )
            
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving user answer: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve answer")


@router.get("/questions/{level}", response_model=WritingQuestionsResponse)
async def get_questions_by_level(
    level: str,
    user: UserOut = Depends(verify_token)
):
    """
    Get writing questions for a specific level in user's learning language with solved status.
    
    Available levels: beginner, elementary, intermediate, advanced
    
    Parameters:
    - level: The user's proficiency level
    """
    try:
        questions = get_writing_questions_with_status(str(user.id), level, user.learning_language)
        
        if not questions:
            raise HTTPException(
                status_code=404, 
                detail=f"No questions found for level: {level}"
            )
            
        return questions
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving writing questions for level {level}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve writing questions")


@router.get("/levels")
async def get_available_levels():
    """
    Get all available writing question levels.
    
    Returns:
        List of available levels
    """
    try:
        levels = get_all_writing_levels()
        return {"levels": levels}
    except Exception as e:
        print(f"Error retrieving writing levels: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve writing levels")


@router.get("/progress/{level}")
async def get_writing_progress(
    level: str,
    user: UserOut = Depends(verify_token)
):
    """
    Get user's writing progress for a specific level.
    
    Returns:
        Dictionary with solved questions count and total questions count
    """
    try:
        progress = get_user_writing_progress(str(user.id), level)
        return progress
    except Exception as e:
        print(f"Error retrieving writing progress for level {level}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve writing progress")


@router.get("/suggested-question")
async def get_suggested_question(
    user: UserOut = Depends(verify_token)
):
    """
    Get the first unsolved question for the user, scanning from beginner to advanced.
    
    Returns:
        Dictionary with question details or null if all questions are solved
    """
    try:
        question = get_first_unsolved_question(str(user.id), user.learning_language)
        return {"question": question}
    except Exception as e:
        print(f"Error retrieving suggested question: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve suggested question")


# Writing Event Endpoints
@router.post("/event/create")
async def create_writing_session_event(
    question_id: str = Query(..., description="Writing question ID"),
    level: str = Query(..., description="Question difficulty level"),
    user: UserOut = Depends(verify_token)
):
    """
    Create a new writing session event when user starts writing.
    
    Parameters:
    - question_id: The ID of the writing question
    - level: The difficulty level of the question
    """
    try:
        # Get question details to store in event
        from src.services.writing_service import get_writing_question_by_id
        question = get_writing_question_by_id(level, question_id, user.learning_language)
        
        if not question:
            raise HTTPException(
                status_code=404,
                detail="Question not found"
            )
        
        # Create writing event
        event = create_writing_event(
            user_id=str(user.id),
            question_id=question_id,
            question_text=question.full_name,
            level=level
        )
        
        return {"event_id": event["_id"], "message": "Writing session started"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating writing event: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create writing session")


@router.get("/event/{question_id}")
async def get_writing_session_event(
    question_id: str,
    user: UserOut = Depends(verify_token)
):
    """
    Get the current writing session event for a specific question.
    
    Parameters:
    - question_id: The ID of the writing question
    """
    try:
        event = get_writing_event_by_question_id(str(user.id), question_id)
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail="No active writing session found for this question"
            )
        
        return event
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving writing event: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve writing session")


@router.put("/event/{event_id}/progress")
async def update_writing_session_progress(
    event_id: str,
    word_count: int = Query(..., description="Current word count"),
    character_count: int = Query(..., description="Current character count"),
    revision_count: int = Query(default=0, description="Number of revisions made"),
    user: UserOut = Depends(verify_token)
):
    """
    Update the progress of an active writing session.
    
    Parameters:
    - event_id: The ID of the writing event
    - word_count: Current number of words written
    - character_count: Current number of characters written
    - revision_count: Number of times user has revised their text
    """
    try:
        # Verify the event belongs to the user
        event = get_writing_event(event_id)
        if not event or event["user_id"] != str(user.id):
            raise HTTPException(
                status_code=404,
                detail="Writing session not found or access denied"
            )
        
        # Update progress
        updated_event = update_writing_progress(
            event_id=event_id,
            word_count=word_count,
            character_count=character_count,
            revision_count=revision_count
        )
        
        if not updated_event:
            raise HTTPException(
                status_code=500,
                detail="Failed to update writing progress"
            )
        
        return {"message": "Progress updated successfully", "event": updated_event}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating writing progress: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update writing progress")


@router.put("/event/{event_id}/complete")
async def complete_writing_session(
    event_id: str,
    final_answer: str = Query(..., description="User's final answer text"),
    user: UserOut = Depends(verify_token)
):
    """
    Complete a writing session and calculate XP.
    
    Parameters:
    - event_id: The ID of the writing event
    - final_answer: The user's final written response
    """
    try:
        # Check content appropriateness
        if final_answer:
            check_user_content(final_answer, "writing", str(user.id))
        
        # Verify the event belongs to the user
        event = get_writing_event(event_id)
        if not event or event["user_id"] != str(user.id):
            raise HTTPException(
                status_code=404,
                detail="Writing session not found or access denied"
            )
        
        # Get AI feedback by evaluating the final answer
        from src.services.writing_service import evaluate_writing_submission
        evaluation = await evaluate_writing_submission(
            user_text=final_answer,
            question=event.get("details", {}).get("question_text", ""),
            user_id=None,  # Don't award XP here, we'll do it in the event
            learning_language=user.learning_language,
            system_language=user.system_language
        )
        
        # Convert evaluation to dict for storage
        ai_feedback = {
            "total_score": evaluation.details.total_score if hasattr(evaluation.details, 'total_score') else 0,
            "content_score": evaluation.details.content_score if hasattr(evaluation.details, 'content_score') else 0,
            "organization_score": evaluation.details.organization_score if hasattr(evaluation.details, 'organization_score') else 0,
            "language_score": evaluation.details.language_score if hasattr(evaluation.details, 'language_score') else 0,
            "feedback": evaluation.feedback
        }
        
        # Complete the writing event with AI feedback
        completed_event = await complete_writing_event(
            event_id=event_id,
            final_answer=final_answer,
            ai_feedback=ai_feedback
        )
        
        if not completed_event:
            raise HTTPException(
                status_code=500,
                detail="Failed to complete writing session"
            )
        
        return {
            "message": "Writing session completed successfully",
            "event": completed_event,
            "evaluation": evaluation,
            "xp_earned": completed_event.get("details", {}).get("xp_earned", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing writing session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to complete writing session")


@router.get("/events/recent")
async def get_recent_writing_events(
    days: int = Query(default=7, description="Number of days to look back"),
    user: UserOut = Depends(verify_token)
):
    """
    Get recent completed writing events for the user.
    
    Parameters:
    - days: Number of days to look back (default: 7)
    """
    try:
        events = get_recent_completed_writing_events(str(user.id), days)
        
        return {
            "events": events,
            "total_events": len(events),
            "days": days
        }
    except Exception as e:
        print(f"Error retrieving recent writing events: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent writing events")
