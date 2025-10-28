from typing import Dict, List

from schemas import AgentDecision, PolicyDecision


def _redact_pii(text: str, pii_matches: List[Dict]) -> str:
    if not pii_matches:
        return text
    sorted_matches = sorted(pii_matches, key=lambda x: x["span"][0], reverse=True)
    result = text
    for match in sorted_matches:
        start, end = match["span"]
        replacement = f"[REDACTED_{match['type'].upper()}]"
        result = result[:start] + replacement + result[end:]
    return result


def apply_action(
    decision: AgentDecision,
    policy_decision: PolicyDecision,
    original_message: str,
    scanner_signals: Dict,
    tutor_response: str = None,
) -> Dict:
    action = decision.action if not decision.fallback else policy_decision.action

    if action == "allow":
        output = tutor_response or "Tutor: here's a helpful explanation (no direct answers)."
        return {"action": "allow", "output": output, "policy_reason": policy_decision.explanation}

    if action == "redact":
        redacted_msg = _redact_pii(original_message, scanner_signals.get("pii", []))
        output = f"Your message was processed with privacy protection. Redacted message: {redacted_msg}"
        return {"action": "redact", "output": output, "policy_reason": policy_decision.explanation}

    if action == "block":
        reason = policy_decision.explanation
        output = f"Your request is not allowed. Reason: {reason}"
        if "self-harm" in reason.lower() or "self harm" in reason.lower():
            output += "\n\nIf you're experiencing distress, please reach out: National Suicide Prevention Lifeline: 988"
        return {"action": "block", "output": output, "policy_reason": reason}

    if action == "rewrite_review":
        output = decision.rewrite or "Let me help you understand the concept instead: [Tutor provides conceptual guidance]"
        return {"action": "rewrite_review", "output": output, "policy_reason": decision.explanation}

    return {"action": "block", "output": "Your request could not be processed.", "policy_reason": "Unknown action"}


