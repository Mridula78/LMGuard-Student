from typing import Dict, List, Tuple
import yaml

from schemas import PolicyDecision
from deps import config


class PolicyEngine:
    def __init__(self, policy_file: str = None):
        self.policy_file = policy_file or config.POLICY_FILE
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict:
        try:
            with open(self.policy_file, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            return {
                "version": 1,
                "categories": {
                    "benign": {
                        "action": "allow",
                        "severity": 10,
                        "explanation": "Content allowed.",
                    }
                },
                "fallback_action": "block",
            }

    def evaluate(self, scanner_signals: Dict) -> PolicyDecision:
        matched: List[Tuple[str, Dict]] = []

        if scanner_signals.get("pii"):
            if len(scanner_signals["pii"]) > 0:
                matched.append(("pii", self.policy["categories"].get("pii")))

        if scanner_signals.get("dishonesty"):
            for item in scanner_signals["dishonesty"]:
                if item.get("score", 0) > 0.5:
                    matched.append((
                        "academic_dishonesty",
                        self.policy["categories"].get("academic_dishonesty"),
                    ))
                    break

        if scanner_signals.get("injection"):
            if len(scanner_signals["injection"]) > 0:
                matched.append(("injection", self.policy["categories"].get("injection")))

        if scanner_signals.get("toxicity_score", 0) > 0.6:
            matched.append(("toxicity", self.policy["categories"].get("toxicity")))

        if not matched:
            benign = self.policy["categories"].get("benign", {})
            return PolicyDecision(
                action=benign.get("action", "allow"),
                explanation=benign.get("explanation", "Content allowed."),
                severity=benign.get("severity", 10),
            )

        matched.sort(key=lambda x: (x[1] or {}).get("severity", 0), reverse=True)
        top_category = matched[0][1] or {"action": "allow", "explanation": "", "severity": 10}

        action = top_category.get("action", "allow")
        if top_category.get("severity", 0) >= 90:
            action = "block"

        return PolicyDecision(
            action=action,
            explanation=top_category.get("explanation", ""),
            severity=top_category.get("severity", 10),
        )


