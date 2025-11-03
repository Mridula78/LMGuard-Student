import json
import hashlib
import os
from typing import Dict
from datetime import datetime
from deps import config

def _hash_student_id(student_id: str) -> str:
    """Hash student ID with salt."""
    return hashlib.sha256(f"{student_id}{config.HASH_SALT}".encode()).hexdigest()

def _redact_pii_from_signals(scanner_signals: Dict) -> Dict:
    """Remove raw PII from signals."""
    signals_copy = {}
    # deep copy minimal structure
    for k, v in (scanner_signals or {}).items():
        if k == "pii":
            scrubbed = []
            for item in v:
                item_copy = item.copy()
                item_copy["match"] = "[REDACTED]"
                scrubbed.append(item_copy)
            signals_copy[k] = scrubbed
        else:
            signals_copy[k] = v
    return signals_copy

def _ensure_log_dir():
    log_file = config.LOG_FILE
    log_dir = os.path.dirname(log_file) or "."
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        pass

def log_audit(
    request_id: str,
    student_id: str,
    scanner_signals: Dict,
    policy_decision: Dict,
    agent_decision: Dict,
    final_action: str,
    latencies: Dict
):
    """Log audit entry with pseudonymization and PII redaction."""
    student_hash = _hash_student_id(student_id) if student_id else "anonymous"
    log_entry = {
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "student_hash": student_hash,
        "scanner_signals": _redact_pii_from_signals(scanner_signals),
        "policy_decision": policy_decision,
        "agent_decision": agent_decision,
        "final_action": final_action,
        "latencies": latencies
    }
    try:
        _ensure_log_dir()
        with open(config.LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        # do not raise — log to stdout for dev visibility
        print(f"[audit] Failed to write audit log: {e}")


