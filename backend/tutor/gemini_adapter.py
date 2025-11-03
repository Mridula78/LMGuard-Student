import httpx
from typing import Optional
from deps import config


GEMINI_CHAT_MODEL = "gemini-1.5-flash"


def _build_messages(user_message: str, system_preamble: Optional[str] = None):
    contents = []
    if system_preamble:
        contents.append({
            "role": "user",
            "parts": [{"text": system_preamble}]
        })
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })
    return contents


def get_tutor_response(message: str, constrain_to_teaching: bool = False) -> str:
    if not config.__dict__.get("GOOGLE_API_KEY"):
        return "Tutor: here's a helpful explanation (no direct answers)."

    system = None
    if constrain_to_teaching:
        system = (
            "You are a helpful tutor. Teach the underlying concepts and guidance. "
            "Do not provide exact solutions or final answers. Keep it concise."
        )

    params = {"key": config.GOOGLE_API_KEY}
    payload = {
        "contents": _build_messages(message, system_preamble=system)
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_CHAT_MODEL}:generateContent",
                params=params,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # Gemini response structure: candidates -> content -> parts[0].text
            candidates = data.get("candidates") or []
            if not candidates:
                return "Tutor: here's a helpful explanation (no direct answers)."
            parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
            text = parts[0].get("text") if parts else None
            return text or "Tutor: here's a helpful explanation (no direct answers)."
    except Exception:
        return "Tutor: here's a helpful explanation (no direct answers)."


