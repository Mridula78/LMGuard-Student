from typing import List, Dict


def scan_dishonesty(text: str) -> List[Dict]:
    """Detect academic dishonesty using keyword heuristics."""
    results: List[Dict] = []

    homework_keywords = [
        "do my homework",
        "solve this for me",
        "give me the answer",
        "complete this assignment",
        "write my essay",
        "answer key",
        "cheat sheet",
    ]

    text_lower = text.lower()
    evidence: List[str] = []

    for keyword in homework_keywords:
        if keyword in text_lower:
            evidence.append(f"Contains: '{keyword}'")

    if evidence:
        score = min(0.9, len(evidence) * 0.3)
        results.append({
            "type": "homework",
            "score": score,
            "evidence": evidence,
        })

    return results


