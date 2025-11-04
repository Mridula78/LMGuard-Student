import google.generativeai as genai
from typing import Optional
from deps import config

GEMINI_CHAT_MODEL = "gemini-2.5-flash"


def get_tutor_response(message: str, constrain_to_teaching: bool = False) -> str:
    """
    Get tutor response from Google Gemini using the official SDK.

    Args:
        message: User's question
        constrain_to_teaching: If True, the assistant will guide but not give direct answers

    Returns:
        Tutor's response text
    """

    if not getattr(config, "GOOGLE_API_KEY", None):
        print("[tutor] No GOOGLE_API_KEY configured")
        return "I'm here to help you learn! Could you tell me more about what you're trying to understand?"

    # Configure API key
    genai.configure(api_key=config.GOOGLE_API_KEY)

    # Build system instruction
    base_instruction = (
        "You are a helpful educational tutor. Your role is to guide students to understanding "
        "by teaching concepts, asking guiding questions, and giving hints — "
        "never providing direct answers to homework or assignments."
    )

    if constrain_to_teaching:
        base_instruction += (
            " Stay concise and conversational. Focus on helping them think rather than giving answers."
        )

    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_CHAT_MODEL,
            system_instruction=base_instruction  # ✅ This is the clean SDK method
        )

        response = model.generate_content(
            message,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
                top_p=0.95
            )
        )

        return response.text.strip()

    except Exception as e:
        print(f"[tutor] Gemini SDK error: {e}")
        return "I'm having trouble responding right now. Could you try again?"
