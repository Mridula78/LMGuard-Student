from typing import Dict


def scan_toxicity(text: str) -> Dict:
    """Simple toxicity detection using keywords."""
    toxic_keywords = [
        "hate",
        "kill",
        "die",
        "stupid",
        "idiot",
        "dumb",
        "attack",
        "violent",
    ]

    text_lower = text.lower()
    count = sum(1 for keyword in toxic_keywords if keyword in text_lower)
    score = min(1.0, count * 0.25)
    return {"toxicity_score": score}


