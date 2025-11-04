import yaml
from typing import Dict
from schemas import PolicyDecision
from deps import config
from .validator import validate_policy


class PolicyEngine:
    """Policy evaluation engine that maps scanner signals to actions."""
    
    def __init__(self, policy_file: str = None):
        self.policy_file = policy_file or config.POLICY_FILE
        self.policy = self._load_policy()
    
    def _load_policy(self) -> Dict:
        """Load and validate policy from YAML file."""
        try:
            with open(self.policy_file, 'r') as f:
                policy = yaml.safe_load(f)
            
            if not validate_policy(policy):
                raise ValueError("Invalid policy structure")
            
            return policy
        except FileNotFoundError:
            raise FileNotFoundError(f"Policy file not found: {self.policy_file}")
        except Exception as e:
            raise RuntimeError(f"Failed to load policy: {e}")
    
    def evaluate(self, scanner_signals: Dict) -> PolicyDecision:
        """
        Evaluate scanner signals against policy rules.
        
        Returns PolicyDecision with action, explanation, and severity.
        Priority order: injection > toxicity > pii > dishonesty > benign
        """
        categories = self.policy.get("categories", {})
        
        # Check for prompt injection (highest priority)
        if scanner_signals.get("injection"):
            cat = categories.get("injection", {})
            return PolicyDecision(
                action=cat.get("action", "block"),
                explanation=cat.get("explanation", "Prompt injection detected."),
                severity=cat.get("severity", 90)
            )
        
        # Check for toxicity
        toxicity_score = scanner_signals.get("toxicity_score", 0.0)
        if toxicity_score > 0.5:  # Threshold for toxicity
            cat = categories.get("toxicity", {})
            return PolicyDecision(
                action=cat.get("action", "block"),
                explanation=cat.get("explanation", "Toxic content detected."),
                severity=cat.get("severity", 85)
            )
        
        # Check for PII
        if scanner_signals.get("pii"):
            cat = categories.get("pii", {})
            return PolicyDecision(
                action=cat.get("action", "redact"),
                explanation=cat.get("explanation", "PII detected and will be redacted."),
                severity=cat.get("severity", 80)
            )
        
        # Check for academic dishonesty
        dishonesty_items = scanner_signals.get("dishonesty", [])
        if dishonesty_items:
            # Check severity based on score
            max_score = max(item.get("score", 0) for item in dishonesty_items)
            cat = categories.get("academic_dishonesty", {})
            
            # High confidence dishonesty -> block directly
            if max_score > 0.7:
                return PolicyDecision(
                    action="block",
                    explanation="Clear attempt to request homework completion.",
                    severity=cat.get("severity", 70)
                )
            
            # Medium confidence -> borderline (send to agent)
            return PolicyDecision(
                action=cat.get("action", "borderline"),
                explanation=cat.get("explanation", "Possible academic dishonesty."),
                severity=cat.get("severity", 70)
            )
        
        # Check for self-harm content (if scanner exists)
        if scanner_signals.get("self_harm"):
            cat = categories.get("self_harm", {})
            return PolicyDecision(
                action=cat.get("action", "block"),
                explanation=cat.get("explanation", "Self-harm content detected."),
                severity=cat.get("severity", 95)
            )
        
        # No issues detected - allow
        cat = categories.get("benign", {})
        return PolicyDecision(
            action=cat.get("action", "allow"),
            explanation=cat.get("explanation", "Content allowed."),
            severity=cat.get("severity", 10)
        )
    
    def reload(self):
        """Reload policy from file (useful for hot-reloading)."""
        self.policy = self._load_policy()