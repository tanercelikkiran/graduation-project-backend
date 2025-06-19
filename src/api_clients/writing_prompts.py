from src.models.writing import DetailedWritingResponse
from .api import gemini_client
from google.genai import types


def create_writing_prompt(
    user_text: str,
    question: str = "",
    learning_language: str = "English",
    system_language: str = "English",
) -> str:
    """
    Create a prompt for writing evaluation using Gemini

    Args:
        user_text: The text submitted by the user for evaluation
        question: The question or prompt that the user is responding to
        learning_language: The language the user is learning/writing in
        system_language: The user's preferred language for feedback

    Returns:
        Formatted prompt string ready to send to Gemini
    """
    # Language context information
    language_context = f"""
**--- CRITICAL LANGUAGE REQUIREMENTS ---**
- The user is learning: {learning_language}
- The user's text is written in: {learning_language}
- IMPORTANT: Provide ALL feedback, suggestions, and comments EXCLUSIVELY in {system_language}. Do NOT use any other language for feedback.
- IMPORTANT: Evaluate the text according to {learning_language} language standards, grammar rules, and conventions ONLY.
- IMPORTANT: When assessing grammar, spelling, and vocabulary, apply {learning_language} rules exclusively.
- Verify language accuracy: All feedback must be written in {system_language} and must be grammatically correct in {system_language}.
- Do NOT mix languages in your feedback or evaluation.

"""

    base_prompt = f"""
You are a meticulous text evaluation AI. Your task is to analyze the user-provided text based on the detailed criteria below and return your findings in a structured JSON format.

{language_context}
**--- Question/Prompt Being Answered ---**
{question if question else "No specific question provided. Evaluate the text as a standalone piece of writing."}

**--- Evaluation Criteria & Scoring Rubric ---**

**1. Content (Score 1-5):** Evaluate the substance and relevance of the text.
*   **Relevance & Completeness:** Does the text fully address the prompt or topic? Is any crucial information missing, or is there irrelevant information included?
*   **Clarity & Precision:** Is the core message easy to understand? Is the information presented clearly and without ambiguity?
*   **Scoring Guide:**
    *   5: Excellent - Perfectly on-topic, comprehensive, and very clear.
    *   4: Good - Mostly complete and clear, with only minor omissions or ambiguities.
    *   3: Average - Addresses the topic but has noticeable gaps or includes some irrelevant information.
    *   2: Poor - Largely misses the point or is significantly incomplete.
    *   1: Very Poor - Completely off-topic or nonsensical.

**2. Organization (Score 1-5):** Evaluate the structure and flow of the text.
*   **Logical Structure:** Is there a clear introduction, body, and conclusion (where applicable)? Are ideas presented in a logical order?
*   **Flow & Cohesion:** Are sentences and paragraphs connected smoothly with appropriate transitions (e.g., 'however', 'therefore', 'in addition')? Does it read as a coherent whole rather than a list of disconnected points?
*   **Scoring Guide:**
    *   5: Excellent - Flawlessly structured with seamless transitions.
    *   4: Good - Clearly organized with good flow, perhaps with a few awkward transitions.
    *   3: Average - A basic structure is present, but the flow is often choppy or illogical.
    *   2: Poor - Lacks a clear structure; ideas are jumbled and difficult to follow.
    *   1: Very Poor - No discernible organization.

**3. Use of {learning_language} (Score 1-5):** Evaluate the technical correctness of the writing in {learning_language}.
*   **Grammar & Punctuation:** Are sentence structures grammatically correct according to {learning_language} grammar rules? Is punctuation used properly according to {learning_language} conventions?
*   **Spelling & Word Choice:** Are all words spelled correctly in {learning_language}? Is the vocabulary appropriate for the context and used accurately in {learning_language}?
*   **Scoring Guide:**
    *   5: Excellent - No or very few minor errors.
    *   4: Good - A few minor errors in grammar, spelling, or punctuation that do not impede understanding.
    *   3: Average - Several noticeable errors that may slightly obscure meaning.
    *   2: Poor - Frequent and significant errors that make the text hard to read.
    *   1: Very Poor - Riddled with errors, making it largely incomprehensible.

**--- CRITICAL OUTPUT INSTRUCTIONS ---**

ABSOLUTE REQUIREMENT: All feedback text, suggestions, and comments must be written EXCLUSIVELY in {system_language}. The user expects to receive feedback in {system_language}.

**LANGUAGE COMPLIANCE FOR OUTPUT:**
- Every word in the "feedback" field must be in {system_language}
- Every word in the "suggestion" field must be in {system_language}
- Every word in the "error" field descriptions must be in {system_language}
- Do NOT mix languages in any output field
- Verify that your entire response is written in {system_language} before submitting

Return your analysis in the following JSON structure:

  "score": <overall score on scale of 0-100>,
  "feedback": "<overall feedback summary in 1-3 sentences>",
  "details": {{
    "content_score": <1-5 score for content>,
    "organization_score": <1-5 score for organization>,
    "language_score": <1-5 score for language usage>,
    "total_score": <sum of all scores, max 15>
  }},
  "feedback_items": [
    {{
      "type": "Grammar|Spelling|Punctuation|Style",
      "error": "<specific error text>",
      "suggestion": "<correction or improvement suggestion>"
    }}
    Include 0-5 specific issues, if any found
  ]

**--- Text to Evaluate ---**
{user_text}

**--- FINAL LANGUAGE COMPLIANCE CHECK ---**
Before submitting your response, verify that:
1. ALL feedback is written ONLY in {system_language}
2. ALL suggestions are written ONLY in {system_language}
3. ALL error descriptions are written ONLY in {system_language}
4. You evaluated the text according to {learning_language} standards
5. No mixing of languages occurred in your response
"""

    return base_prompt.strip()


def send_writing_prompt_to_gemini(
    user_text: str,
    question: str = "",
    learning_language: str = "English",
    system_language: str = "English",
) -> DetailedWritingResponse:
    """
    Send a writing prompt to Gemini using structured outputs and return the structured response

    Args:
        user_text: The text submitted by the user for evaluation
        question: The question or prompt that the user is responding to
        learning_language: The language the user is learning/writing in
        system_language: The user's preferred language for feedback

    Returns:
        DetailedWritingResponse object with detailed scores and feedback
    """

    prompt = create_writing_prompt(
        user_text, question, learning_language, system_language
    )

    # Use structured outputs with the DetailedWritingResponse schema
    # Note: gemini_client.models.generate_content is synchronous, not async
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash-preview-05-20",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DetailedWritingResponse,
        ),
    )

    return response.parsed
