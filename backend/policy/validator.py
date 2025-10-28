from typing import Dict


def validate_policy(policy: Dict) -> bool:
    """Validate policy structure."""
    required_keys = ["version", "categories", "fallback_action"]
    if not all(key in policy for key in required_keys):
        return False

    for _, cat_data in policy["categories"].items():
        if not all(key in cat_data for key in ["action", "severity", "explanation"]):
            return False

    return True


