from .api import gemini_client
from google.genai import types
from pydantic import BaseModel
from typing import Optional, List
import time


class ContentModerationResult(BaseModel):
    """Model for content moderation response"""

    is_appropriate: bool


class PurposeSummaryResult(BaseModel):
    """Model for purpose summarization response"""

    summary: str  # Brief summary of the purpose


def check_content_appropriateness(
    content: str,
    purpose: str,
    max_retries: int = 3,
) -> Optional[ContentModerationResult]:
    """
    Check if the given content is appropriate for the specified educational purpose.

    Args:
        content: The text content to be checked for appropriateness
        purpose: The educational purpose/context (e.g., "language learning", "children's education", "business training")
        max_retries: Maximum number of retry attempts on failure

    Returns:
        ContentModerationResult: Analysis of content appropriateness

    Raises:
        Exception: If content moderation fails after all retries
    """

    prompt = f"""

**CONTENT MODERATION TASK:**
You are a content moderation AI for educational platforms. Analyze the provided content for appropriateness in the context of: {purpose}

**EVALUATION CRITERIA:**
1. **Educational Appropriateness**: Is the content suitable for educational purposes?
2. **Age Appropriateness**: Is the content appropriate for learners of all ages?
3. **Cultural Sensitivity**: Does the content respect cultural differences and avoid offensive material?
4. **Language Learning Suitability**: Is the content appropriate for language learning contexts?
5. **Professional Standards**: Does the content meet professional educational standards?

**CONTENT CATEGORIES TO FLAG:**
- Explicit sexual content
- Violence or graphic descriptions
- Hate speech or discriminatory language
- Illegal activities or dangerous behaviors
- Inappropriate profanity or vulgar language
- Content that promotes harmful ideologies
- Spam or irrelevant content
- Content that violates educational standards
- Malicious content (e.g., phishing, scams)

**SCORING:**
- confidence_score: Rate your confidence in this assessment (0.0 = uncertain, 1.0 = very confident)
- is_appropriate: true if content is appropriate, false if it should be flagged

**OUTPUT FORMAT:**
Respond with a JSON object matching the ContentModerationResult schema:
{{
  "is_appropriate": <boolean>,
}}

**CONTENT TO ANALYZE:**
"{content}"

**PURPOSE CONTEXT:**
{purpose}
"""

    retry_count = 0
    while retry_count < max_retries:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContentModerationResult,
                ),
            )
            return response.parsed

        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(
                    f"Error in check_content_appropriateness after {max_retries} attempts: {str(e)}"
                )
                return None
            time.sleep(1)  # Wait before retrying


def summarize_user_purpose(
    user_explanation: str,
    max_retries: int = 3,
) -> Optional[PurposeSummaryResult]:
    """
    Summarize the user's explanation of their app usage purpose into 3-5 keywords and a brief summary.

    Args:
        user_explanation: The user's detailed explanation of why they want to use the app
        max_retries: Maximum number of retry attempts on failure

    Returns:
        PurposeSummaryResult: Summarized purpose with keywords and category

    Raises:
        Exception: If purpose summarization fails after all retries
    """

    prompt = f"""
**PURPOSE SUMMARIZATION TASK:**
You are an AI that helps extract and summarize user learning goals for a language learning app. 
Analyze the user's explanation and extract the core purpose into structured data.

**ANALYSIS REQUIREMENTS:**
1. **Summary**: Create a concise 3-5 word summary of their main goal

**OUTPUT FORMAT:**
Respond with a JSON object matching the PurposeSummaryResult schema:
{{
  "summary": "<brief summary in English>",
}}

**USER EXPLANATION TO ANALYZE:**
"{user_explanation}"
"""

    retry_count = 0
    while retry_count < max_retries:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PurposeSummaryResult,
                ),
            )
            return response.parsed

        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(
                    f"Error in summarize_user_purpose after {max_retries} attempts: {str(e)}"
                )
                return None
            time.sleep(1)  # Wait before retrying
