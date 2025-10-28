from typing import Dict
from .pii import scan_pii
from .dishonesty import scan_dishonesty
from .injection import scan_injection
from .toxicity import scan_toxicity


def run_all_scanners(text: str) -> Dict:
    """Run all scanners and return combined results."""
    return {
        "pii": scan_pii(text),
        "dishonesty": scan_dishonesty(text),
        "injection": scan_injection(text),
        **scan_toxicity(text),
    }


