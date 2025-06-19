from typing import Optional, List
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import json
import os

from src.api_clients.writing_prompts import (
    create_writing_prompt,
    send_writing_prompt_to_gemini,
)
from src.models.writing import (
    DetailedWritingResponse,
    WritingAnswerResponse,
    WritingQuestionResponse,
    WritingQuestion,
    WritingQuestionsResponse,
    ScenarioAnswer,
    WritingScenarioAnswerRequest,
    WritingScenarioAnswerResponse,
)
from src.services.xp_service import get_xp, update_xp
from src.services.translation_service import translate_questions_list, translate_writing_question, translate_feedback
from src.database.database import writing_table, writing_answer_table


async def evaluate_writing_submission(
    user_text: str, question: str = "", user_id: Optional[str] = None,
    learning_language: str = "English", system_language: str = "English"
) -> DetailedWritingResponse:
    """
    Evaluate a writing submission and calculate XP if a user is authenticated

    Args:
        user_text: The text submitted by the user for evaluation
        question: The question or prompt that the user is responding to
        user_id: Optional user ID for authenticated users (XP will be awarded via events)
        learning_language: The language the user is learning/writing in
        system_language: The user's preferred language for feedback

    Returns:
        DetailedWritingResponse with evaluation details and feedback
    """
    # Send to Gemini for evaluation with language context
    result = send_writing_prompt_to_gemini(
        user_text=user_text, 
        question=question,
        learning_language=learning_language,
        system_language=system_language
    )

    # XP is now handled by the event system, not directly here
    # Store potential XP in the result for reference
    if hasattr(result.details, "total_score"):
        result.details.xp_earned = result.details.total_score * 20

    # Note: For question-specific responses, use answer_writing_question instead

    return result

async def get_writing_prompt(user_text: str, question: str = "") -> str:
    """
    Get the formatted prompt for writing evaluation

    Args:
        user_text: The text submitted by the user for evaluation
        question: The question or prompt that the user is responding to

    Returns:
        Formatted prompt string ready to send to Gemini
    """
    return create_writing_prompt(user_text, question)


async def answer_writing_question(
    user_id: str, question_id: str, level: str, answer: str, 
    system_language: str = "English", learning_language: str = "English"
) -> Optional[WritingAnswerResponse]:
    """
    Save user's answer to a specific writing question and evaluate it

    Args:
        user_id: The ID of the user answering the question
        question_id: The ID of the question being answered
        level: The level of the question
        answer: The user's answer text
        system_language: Language for UI/feedback (default: "English")
        learning_language: Language being learned for questions (default: "English")

    Returns:
        WritingAnswerResponse with evaluation if successful, None otherwise
    """
    try:
        # Get the question details (in learning language)
        question = get_writing_question_by_id(level, question_id, learning_language)
        if not question:
            print(f"Question {question_id} not found for level {level}")
            return None

        # Evaluate the answer
        evaluation = await evaluate_writing_submission(
            user_text=answer,
            question=question.full_name,
            user_id=user_id,
            learning_language=learning_language,
            system_language=system_language
        )
        
        # Feedback should now be generated directly in the correct language by AI
        # No additional translation needed

        # Create question response for database
        question_response = WritingQuestionResponse.from_evaluation(
            user_id=user_id,
            question_id=question_id,
            level=level,
            question_text=question.full_name,
            user_answer=answer,
            evaluation=evaluation
        )

        # Save to database (replace existing answer if any)
        question_response_dict = question_response.model_dump()
        writing_table.replace_one(
            {"user_id": user_id, "question_id": question_id, "level": level},
            question_response_dict,
            upsert=True
        )

        # Return response
        return WritingAnswerResponse(
            question_id=question_id,
            question_text=question.full_name,
            user_answer=answer,
            evaluation=evaluation
        )

    except Exception as e:
        print(f"Error answering writing question: {str(e)}")
        return None


def get_user_question_response(
    user_id: str, question_id: str, level: str
) -> Optional[WritingQuestionResponse]:
    """
    Get user's response to a specific writing question

    Args:
        user_id: The ID of the user
        question_id: The ID of the question
        level: The level of the question

    Returns:
        WritingQuestionResponse if found, None otherwise
    """
    try:
        # Find the user's response to this specific question
        response = writing_table.find_one({
            "user_id": user_id,
            "question_id": question_id,
            "level": level
        })

        if not response:
            return None

        # Convert ObjectId to string if present
        if "_id" in response:
            response["_id"] = str(response["_id"])

        return WritingQuestionResponse(**response)

    except Exception as e:
        print(f"Error retrieving user question response: {str(e)}")
        return None


def get_writing_questions_by_level(level: str, learning_language: str = "English") -> Optional[WritingQuestionsResponse]:
    """
    Load writing questions from the unified questions.json file based on user level

    Args:
        level: The user's level (beginner, elementary, intermediate, advanced)
        learning_language: Language for translating questions (default: "English")

    Returns:
        WritingQuestionsResponse containing questions for the level
    """
    try:
        level_lower = level.lower()
        valid_levels = ["beginner", "elementary", "intermediate", "advanced"]
        
        if level_lower not in valid_levels:
            print(f"Invalid level: {level}")
            return None

        # Get the file path
        current_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to src/
        file_path = os.path.join(current_dir, "writing_question", "questions.json")

        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Writing questions file not found: {file_path}")
            return None

        # Load and parse JSON file
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Extract the level data
        if level_lower not in data:
            print(f"Level '{level_lower}' not found in questions file")
            return None

        level_questions = data[level_lower]
        
        # Translate questions if needed
        if learning_language.lower() != "english":
            level_questions = translate_questions_list(level_questions, learning_language)
        
        # Convert questions list to WritingQuestion objects
        questions = []
        for question_data in level_questions:
            question = WritingQuestion(
                id=question_data.get("id", ""),
                name=question_data.get("name", ""),
                full_name=question_data.get("fullName", ""),
                scenarios=question_data.get("scenarios", []),
                level=level_lower,
            )
            questions.append(question)

        return WritingQuestionsResponse(
            level=level_lower,
            title=f"{level_lower.capitalize()} Level Questions",
            questions=questions,
            total_questions=len(questions),
        )

    except Exception as e:
        print(f"Error loading writing questions for level {level}: {str(e)}")
        return None


def get_all_writing_levels() -> List[str]:
    """
    Get all available writing levels

    Returns:
        List of available levels
    """
    return ["beginner", "elementary", "intermediate", "advanced"]


def get_writing_question_by_id(level: str, question_id: str, learning_language: str = "English") -> Optional[WritingQuestion]:
    """
    Get a specific writing question by level and question ID

    Args:
        level: The user's level (beginner, elementary, intermediate, advanced)
        question_id: The ID of the specific question to retrieve
        learning_language: Language for translating questions (default: "English")

    Returns:
        WritingQuestion if found, None otherwise
    """
    try:
        questions_response = get_writing_questions_by_level(level, learning_language)
        if not questions_response:
            return None

        # Find the question with matching ID
        for question in questions_response.questions:
            if question.id == question_id:
                return question

        return None

    except Exception as e:
        print(f"Error retrieving writing question {question_id} for level {level}: {str(e)}")
        return None


def get_all_writing_questions() -> Optional[dict]:
    """
    Load all writing questions from the questions.json file

    Returns:
        Dictionary containing all questions organized by level
    """
    try:
        # Get the file path
        current_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to src/
        file_path = os.path.join(current_dir, "writing_question", "questions.json")

        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Writing questions file not found: {file_path}")
            return None

        # Load and parse JSON file
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    except Exception as e:
        print(f"Error loading all writing questions: {str(e)}")
        return None


def count_questions_by_level(level: str) -> int:
    """
    Count the number of questions available for a specific level

    Args:
        level: The user's level (beginner, elementary, intermediate, advanced)

    Returns:
        Number of questions available for the level
    """
    try:
        questions_response = get_writing_questions_by_level(level)
        if not questions_response:
            return 0
        
        return questions_response.total_questions

    except Exception as e:
        print(f"Error counting questions for level {level}: {str(e)}")
        return 0


def get_user_writing_progress(user_id: str, level: str) -> dict:
    """
    Get user's writing progress for a specific level

    Args:
        user_id: The ID of the user
        level: The level to check progress for

    Returns:
        Dictionary with solved count and total count
    """
    try:
        # Count solved questions for this user and level
        solved_count = writing_table.count_documents({
            "user_id": user_id,
            "level": level.lower()
        })
        
        # Get total questions for this level
        total_count = count_questions_by_level(level)
        
        return {
            "solved": solved_count,
            "total": total_count,
            "level": level.lower()
        }

    except Exception as e:
        print(f"Error getting writing progress for user {user_id} level {level}: {str(e)}")
        return {
            "solved": 0,
            "total": 0,
            "level": level.lower()
        }


def get_writing_questions_with_status(user_id: str, level: str, learning_language: str = "English") -> Optional[WritingQuestionsResponse]:
    """
    Load writing questions from the unified questions.json file with solved status for user

    Args:
        user_id: The ID of the user to check solved status for
        level: The user's level (beginner, elementary, intermediate, advanced)
        learning_language: Language for translating questions (default: "English")

    Returns:
        WritingQuestionsResponse containing questions with solved status for the level
    """
    try:
        # Get the basic questions response
        questions_response = get_writing_questions_by_level(level, learning_language)
        if not questions_response:
            return None
        
        # Get solved question IDs for this user and level
        solved_questions = writing_table.find(
            {"user_id": user_id, "level": level.lower()},
            {"question_id": 1, "_id": 0}
        )
        solved_ids = {q["question_id"] for q in solved_questions}
        
        # Update questions with solved status
        for question in questions_response.questions:
            question.solved = question.id in solved_ids
        
        return questions_response

    except Exception as e:
        print(f"Error loading writing questions with status for level {level}: {str(e)}")
        return None


async def answer_writing_question_with_scenarios(
    user_id: str, 
    request: WritingScenarioAnswerRequest,
    system_language: str = "English", 
    learning_language: str = "English"
) -> Optional[WritingScenarioAnswerResponse]:
    """
    Save user's answers to multiple scenarios in a writing question and evaluate them
    
    Args:
        user_id: The ID of the user answering the question
        request: WritingScenarioAnswerRequest with question_id, level, and scenario answers
        system_language: Language for UI/feedback (default: "English")
        learning_language: Language being learned for questions (default: "English")
    
    Returns:
        WritingScenarioAnswerResponse with evaluation if successful, None otherwise
    """
    try:
        print(f"DEBUG: Looking for question {request.question_id} in level {request.level}")
        # Get the question details (in learning language)
        question = get_writing_question_by_id(request.level, request.question_id, learning_language)
        if not question:
            print(f"ERROR: Question {request.question_id} not found for level {request.level}")
            return None
        print(f"DEBUG: Found question: {question.name}")
        
        # Combine scenario answers for evaluation
        combined_answers = []
        for scenario_answer in request.scenario_answers:
            if scenario_answer.answer and scenario_answer.answer.strip():
                combined_answers.append(f"{scenario_answer.scenario_text}: {scenario_answer.answer}")
        
        combined_text = '\n\n'.join(combined_answers)
        
        if not combined_text.strip():
            print("No answers provided for any scenarios")
            return None
        
        # Evaluate the combined answer
        evaluation = await evaluate_writing_submission(
            user_text=combined_text,
            question=question.full_name,
            user_id=user_id,
            learning_language=learning_language,
            system_language=system_language
        )
        
        # Feedback should now be generated directly in the correct language by AI
        # No additional translation needed
        
        # Create question response for database
        question_response = WritingQuestionResponse.from_evaluation(
            user_id=user_id,
            question_id=request.question_id,
            level=request.level,
            question_text=question.full_name,
            user_answer=combined_text,  # Store combined for backward compatibility
            evaluation=evaluation,
            scenario_answers=request.scenario_answers  # Store individual scenario answers
        )
        
        # Save to database (replace existing answer if any)
        question_response_dict = question_response.model_dump()
        writing_table.replace_one(
            {"user_id": user_id, "question_id": request.question_id, "level": request.level},
            question_response_dict,
            upsert=True
        )
        
        # Return scenario response
        return WritingScenarioAnswerResponse(
            question_id=request.question_id,
            question_text=question.full_name,
            scenario_answers=request.scenario_answers,
            combined_answer=combined_text,
            evaluation=evaluation
        )
        
    except Exception as e:
        print(f"Error answering writing question with scenarios: {str(e)}")
        return None


def get_first_unsolved_question(user_id: str, learning_language: str = "English") -> Optional[dict]:
    """
    Get the first unsolved question for the user, scanning from beginner to advanced.
    
    Args:
        user_id: The ID of the user
        learning_language: Language for translating questions (default: "English")
    
    Returns:
        Dictionary with question details or None if all questions are solved
    """
    try:
        levels = get_all_writing_levels()
        
        for level in levels:
            # Get questions with status for this level
            questions_response = get_writing_questions_with_status(user_id, level, learning_language)
            if not questions_response:
                continue
            
            # Find first unsolved question
            for question in questions_response.questions:
                if not getattr(question, 'solved', False):
                    return {
                        "id": question.id,
                        "title": question.name,
                        "description": question.full_name,
                        "scenarios": question.scenarios,
                        "level": level
                    }
        
        # All questions are solved
        return None
    
    except Exception as e:
        print(f"Error getting first unsolved question for user {user_id}: {str(e)}")
        return None
