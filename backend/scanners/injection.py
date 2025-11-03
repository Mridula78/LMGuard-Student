import re
from typing import List, Dict


def scan_injection(text: str) -> List[Dict]:
    """Detect prompt injection attempts."""
    results: List[Dict] = []

    injection_patterns = [
        r"(?i)(ignore|disregard)\s+(previous|above|prior)\s+(instructions|prompts?)",
        r'(?i)system\s*:\s*["]',
        r"(?i)you\s+are\s+(now|no longer)",
        r"(?i)new\s+instructions?",
        r"(?i)developer\s+mode",
    ]

    for pattern in injection_patterns:
        if re.search(pattern, text):
            results.append({
                "type": "prompt_injection",
                "pattern": pattern,
            })
            break

    return results
