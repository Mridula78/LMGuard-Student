import google.generativeai as genai
from typing import List, Dict
from deps import config

GEMINI_CHAT_MODEL = "gemini-2.5-flash"  # or "gemini-1.5-flash" if 2.0 not available


def format_messages_for_gemini(messages: List[Dict[str, str]]) -> List[Dict]:
    """Ensure roles are Gemini-compatible."""
    formatted = []
    for msg in messages:
        role = msg.get("role", "user")
        if role == "assistant":
            role = "model"
        elif role == "system":
            continue
        formatted.append({"role": role, "parts": msg.get("parts", [])})
    return formatted


def get_tutor_response(messages: List[Dict[str, str]], constrain_to_teaching: bool = False) -> str:
    """
    Get tutor response from Google Gemini using the official SDK, with conversation context.
    """

    if not getattr(config, "GOOGLE_API_KEY", None):
        print("[tutor] No GOOGLE_API_KEY configured")
        return "I'm here to help you learn! Could you tell me more about what you're trying to understand?"

    genai.configure(api_key=config.GOOGLE_API_KEY)

    base_instruction = (
        "You are a helpful educational tutor. Your role is to guide students to understanding "
        "by teaching concepts, asking guiding questions, and giving hints — never providing direct answers. "
        "Be encouraging, patient, and focus on building understanding rather than just giving solutions."
    )

    if constrain_to_teaching:
        base_instruction += " Stay concise and conversational."

    try:
        # ✅ Create the model (no system_instruction)
        model = genai.GenerativeModel(model_name=GEMINI_CHAT_MODEL)

        # ✅ Prepend base instruction as a normal message
        full_history = [{"role": "user", "parts": [{"text": base_instruction}]}] + format_messages_for_gemini(messages)

        # ✅ Start chat session
        chat = model.start_chat(history=full_history)

        # ✅ Send only the latest user input
        response = chat.send_message(
            messages[-1]["parts"][0]["text"],
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
                top_p=0.95,
            ),
        )

        return response.text.strip() if response.text else "I'm not sure I understood that. Could you clarify?"

    except Exception as e:
        print(f"[tutor] Gemini SDK error: {type(e).__name__}: {e}")
        return "I'm having trouble responding right now. Could you try again?"
