import re
from typing import List, Dict


def scan_pii(text: str) -> List[Dict]:
    """Scan for PII using regex patterns."""
    results: List[Dict] = []

    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    for match in re.finditer(email_pattern, text):
        results.append({
            "type": "email",
            "match": match.group(),
            "span": [match.start(), match.end()],
        })

    phone_patterns = [
        r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        r"\b\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b",
        r"\b\d{10}\b",
    ]
    for pattern in phone_patterns:
        for match in re.finditer(pattern, text):
            results.append({
                "type": "phone",
                "match": match.group(),
                "span": [match.start(), match.end()],
            })

    return results


