"""
Content Check Service

This service provides functions for content moderation and user purpose processing
using AI-powered analysis. It includes:

1. Content Moderation: Check if user-generated content is appropriate for educational purposes
2. Purpose Summarization: Process and summarize user explanations of their app usage goals

Usage Examples:

# Content Moderation
result = moderate_user_content(
    content="Hello, I want to learn English for my job",
    purpose="language learning",
    user_id="user123"
)

# Purpose Processing
purpose_result = process_user_purpose_explanation(
    user_explanation="I want to learn Spanish because I'm moving to Madrid for work",
    user_id="user123",
    update_user_profile=True
)

# Educational Content Validation
validation_result = validate_educational_content(
    content="The cat sits on the mat",
    content_type="vocabulary",
    educational_level="beginner"
)
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status

from src.api_clients.user_prompts import (
    check_content_appropriateness,
    summarize_user_purpose,
    ContentModerationResult,
    PurposeSummaryResult,
)
from src.database.database import user_table
import logging

logger = logging.getLogger(__name__)


def moderate_user_content(
    content: str,
    purpose: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Service function to moderate user-generated content for appropriateness.

    Args:
        content: The text content to be moderated
        purpose: The educational purpose/context
        user_id: Optional user ID for logging purposes

    Returns:
        Dict containing moderation results and recommendation

    Raises:
        HTTPException: If moderation fails or content is inappropriate
    """
    try:
        # Log the moderation attempt
        logger.info(
            f"Content moderation requested for user {user_id}, purpose: {purpose}"
        )

        # Validate input
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content cannot be empty",
            )

        if not purpose or not purpose.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purpose must be specified",
            )

        # Check content appropriateness using AI
        moderation_result = check_content_appropriateness(
            content=content.strip(),
            purpose=purpose.strip(),
        )

        if not moderation_result:
            logger.error(f"Content moderation failed for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Content moderation service is currently unavailable",
            )

        # Prepare response
        response = {
            "is_appropriate": moderation_result.is_appropriate,
            "moderation_timestamp": datetime.now(timezone.utc).isoformat(),
            "purpose": purpose,
            "user_id": user_id,
        }

        # If content is not appropriate, include detailed information
        if not moderation_result.is_appropriate:
            logger.warning(
                f"Inappropriate content detected for user {user_id}: {purpose}"
            )
            response.update(
                {
                    "action": "reject",
                    "message": "Content has been flagged as inappropriate for educational purposes",
                }
            )
        else:
            logger.info(f"Content approved for user {user_id}")
            response.update(
                {
                    "action": "approve",
                    "message": "Content is appropriate for the specified educational purpose",
                }
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in content moderation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during content moderation",
        )


def process_user_purpose_explanation(
    user_explanation: str,
    user_id: str,
    update_user_profile: bool = True,
) -> Dict[str, Any]:
    """
    Service function to process and summarize user's purpose explanation.

    Args:
        user_explanation: User's detailed explanation of their app usage purpose
        user_id: User ID to update their profile
        update_user_profile: Whether to update the user's profile with the summarized purpose

    Returns:
        Dict containing summarized purpose and processing results

    Raises:
        HTTPException: If processing fails or user not found
    """
    try:
        # Log the purpose processing attempt
        logger.info(f"Purpose summarization requested for user {user_id}")

        # Validate input
        if not user_explanation or not user_explanation.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User explanation cannot be empty",
            )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required"
            )

        # Verify user exists if we need to update their profile
        if update_user_profile:
            user = user_table.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

        # Summarize user purpose using AI
        summary_result = summarize_user_purpose(
            user_explanation=user_explanation.strip(),
        )

        if not summary_result:
            logger.error(f"Purpose summarization failed for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Purpose summarization service is currently unavailable",
            )

        # Prepare response
        response = {
            "summary": summary_result.summary,
            "original_explanation": user_explanation.strip(),
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
        }

        # Update user profile if requested
        if update_user_profile:
            try:
                update_data = {
                    "purpose": summary_result.summary,
                    "purpose_explanation": user_explanation.strip(),
                    "purpose_updated_at": datetime.now(timezone.utc),
                }

                result = user_table.update_one(
                    {"_id": ObjectId(user_id)}, {"$set": update_data}
                )

                if result.modified_count > 0:
                    logger.info(
                        f"User profile updated with new purpose for user {user_id}"
                    )
                    response["profile_updated"] = True
                    response["message"] = (
                        "Purpose successfully processed and profile updated"
                    )
                else:
                    logger.warning(
                        f"No changes made to user profile for user {user_id}"
                    )
                    response["profile_updated"] = False
                    response["message"] = (
                        "Purpose processed but no profile changes were needed"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to update user profile for user {user_id}: {str(e)}"
                )
                response["profile_updated"] = False
                response["message"] = "Purpose processed but profile update failed"
        else:
            response["profile_updated"] = False
            response["message"] = "Purpose successfully processed"

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in purpose processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during purpose processing",
        )


def get_content_moderation_history(
    user_id: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Retrieve content moderation history for a user (if stored in database).
    This is a placeholder function for future implementation.

    Args:
        user_id: User ID to get moderation history for
        limit: Maximum number of records to return

    Returns:
        Dict containing moderation history
    """
    try:
        # Verify user exists
        user = user_table.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # This is a placeholder - in the future, you might want to store
        # moderation history in a separate collection
        return {
            "user_id": user_id,
            "moderation_history": [],
            "message": "Moderation history feature not yet implemented",
            "total_records": 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving moderation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving moderation history",
        )


def validate_educational_content(
    content: str,
    content_type: str,
    educational_level: str = "intermediate",
) -> Dict[str, Any]:
    """
    Validate content specifically for educational appropriateness.

    Args:
        content: The educational content to validate
        content_type: Type of content (e.g., "vocabulary", "sentence", "essay", "quiz")
        educational_level: Educational level (e.g., "beginner", "intermediate", "advanced")

    Returns:
        Dict containing validation results
    """
    try:
        # Create a specific educational purpose based on content type and level
        purpose = f"{educational_level} level {content_type} for language learning"

        # Use the general moderation function with educational context
        result = moderate_user_content(
            content=content,
            purpose=purpose,
        )

        # Add educational-specific metadata
        result.update(
            {
                "content_type": content_type,
                "educational_level": educational_level,
                "validation_type": "educational_content",
            }
        )

        return result

    except Exception as e:
        logger.error(f"Error in educational content validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during educational content validation",
        )


def check_user_content(
    content: str,
    content_type: str = "general",
    user_id: Optional[str] = None,
    raise_on_inappropriate: bool = True,
) -> bool:
    """
    Simple wrapper function to check if user content is appropriate.
    
    Args:
        content: The content to check
        content_type: Type of content (vocabulary, sentence, writing, etc.)
        user_id: Optional user ID for logging
        raise_on_inappropriate: Whether to raise exception if content is inappropriate
        
    Returns:
        bool: True if content is appropriate, False otherwise
        
    Raises:
        HTTPException: If content is inappropriate and raise_on_inappropriate=True
    """
    try:
        purpose = f"{content_type} content for language learning"
        result = moderate_user_content(content=content, purpose=purpose, user_id=user_id)
        
        if not result["is_appropriate"] and raise_on_inappropriate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content contains inappropriate material for educational purposes"
            )
            
        return result["is_appropriate"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in content checking: {str(e)}")
        if raise_on_inappropriate:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Content validation service is currently unavailable"
            )
        return True  # Default to allowing content if service fails
