import yaml
import os
from typing import Dict
from schemas import PolicyDecision
from deps import config
from policy.validator import validate_policy

class PolicyEngine:
    def __init__(self, policy_file: str = None):
        self.policy_file = policy_file or config.POLICY_FILE
        self.policy = self._load_policy()
    
    def _load_policy(self) -> Dict:
        """Load and validate policy from YAML. Raise or fallback on invalid config."""
        if not os.path.exists(self.policy_file):
            raise RuntimeError(f"Policy file not found at {self.policy_file}")
        with open(self.policy_file, 'r') as f:
            policy = yaml.safe_load(f)
        if not validate_policy(policy):
            raise RuntimeError("Invalid policy.yaml structure. Please fix policy file.")
        return policy
    
    def evaluate(self, scanner_signals: Dict) -> PolicyDecision:
        """Evaluate scanner signals against policy."""
        matched_categories = []
        categories = self.policy.get("categories", {})

        # Check PII
        if scanner_signals.get("pii") and len(scanner_signals["pii"]) > 0:
            cat = categories.get("pii")
            if cat:
                matched_categories.append(("pii", cat))

        # Check dishonesty (scanner key can be 'dishonesty' or 'academic_dishonesty')
        dishonesty_key = "dishonesty" if "dishonesty" in scanner_signals else "academic_dishonesty"
        if scanner_signals.get(dishonesty_key) and len(scanner_signals[dishonesty_key]) > 0:
            for item in scanner_signals[dishonesty_key]:
                if item.get("score", 0) > 0:
                    cat = categories.get("academic_dishonesty")
                    if cat:
                        matched_categories.append(("academic_dishonesty", cat))
                        break
        
        # Check injection
        if scanner_signals.get("injection") and len(scanner_signals["injection"]) > 0:
            cat = categories.get("injection")
            if cat:
                matched_categories.append(("injection", cat))
        
        # Check toxicity
        if scanner_signals.get("toxicity_score", 0) > 0.6:
            cat = categories.get("toxicity")
            if cat:
                matched_categories.append(("toxicity", cat))
        
        if not matched_categories:
            benign = categories.get("benign", {"action":"allow","explanation":"Content allowed.","severity":10})
            return PolicyDecision(action=benign["action"], explanation=benign.get("explanation",""), severity=benign.get("severity",10))

        matched_categories.sort(key=lambda x: x[1].get("severity", 0), reverse=True)
        top_category = matched_categories[0][1]
        action = top_category.get("action", "block")
        # Force block for very high severity categories
        if top_category.get("severity", 0) >= 90:
            action = "block"
        return PolicyDecision(action=action, explanation=top_category.get("explanation",""), severity=top_category.get("severity",0))

def _example():
    # quick usage example
    pe = PolicyEngine()
    print(pe.policy)


