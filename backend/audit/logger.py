import hashlib
import json
from datetime import datetime
from typing import Dict

from deps import config


def _hash_student_id(student_id: str) -> str:
    return hashlib.sha256(f"{student_id}{config.HASH_SALT}".encode()).hexdigest()


def _redact_pii_from_signals(scanner_signals: Dict) -> Dict:
    signals_copy = json.loads(json.dumps(scanner_signals))
    if "pii" in signals_copy:
        for item in signals_copy["pii"]:
            item["match"] = "[REDACTED]"
    return signals_copy


def log_audit(
    request_id: str,
    student_id: str,
    scanner_signals: Dict,
    policy_decision: Dict,
    agent_decision: Dict,
    final_action: str,
    latencies: Dict,
) -> None:
    student_hash = _hash_student_id(student_id) if student_id else "anonymous"
    log_entry = {
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "student_hash": student_hash,
        "scanner_signals": _redact_pii_from_signals(scanner_signals),
        "policy_decision": policy_decision,
        "agent_decision": agent_decision,
        "final_action": final_action,
        "latencies": latencies,
    }
    try:
        with open(config.LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Failed to write audit log: {e}")


