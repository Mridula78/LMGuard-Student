from typing import Dict, Optional
from schemas import AgentDecision, PolicyDecision


def apply_action(
    agent_decision: AgentDecision,
    policy_decision: PolicyDecision,
    user_message: str,
    scanner_signals: Dict,
    tutor_response: Optional[str]
) -> Dict:
    """
    Apply the final action based on agent/policy decisions.
    
    Returns a dict with: action, output, policy_reason
    """
    action = agent_decision.action
    
    if action == "allow":
        return {
            "action": "allow",
            "output": tutor_response or "Request allowed.",
            "policy_reason": agent_decision.explanation
        }
    
    elif action == "redact":
        # Redact PII from message
        redacted_message = user_message
        pii_items = scanner_signals.get("pii", [])
        
        for pii_item in pii_items:
            pii_match = pii_item.get("match", "")
            pii_type = pii_item.get("type", "INFO").upper()
            if pii_match:
                redacted_message = redacted_message.replace(
                    pii_match, 
                    f"[REDACTED_{pii_type}]"
                )
        
        return {
            "action": "redact",
            "output": f"Your message contained sensitive information that was redacted: {redacted_message}",
            "policy_reason": agent_decision.explanation or "PII detected and redacted."
        }
    
    elif action == "block":
        # Provide helpful blocking message
        explanation = agent_decision.explanation or "Request blocked due to policy violation."
        
        return {
            "action": "block",
            "output": f"I cannot process this request. {explanation}",
            "policy_reason": explanation
        }
    
    elif action == "rewrite_review":
        # Use agent's rewritten version or ask for rephrase
        output = agent_decision.rewrite if agent_decision.rewrite else \
                 "Please rephrase your question in a more appropriate way."
        
        return {
            "action": "rewrite_review",
            "output": output,
            "policy_reason": agent_decision.explanation or "Request needs revision."
        }
    
    else:
        # Fallback for unknown actions - fail safe to block
        return {
            "action": "block",
            "output": "Unable to process request due to an internal error.",
            "policy_reason": f"Unknown action: {action}"
        }