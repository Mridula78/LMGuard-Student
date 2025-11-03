import uuid
import time
import json
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from schemas import ChatRequest, ChatResponse, HealthResponse, AgentDecision, PolicyDecision
from scanners.run_all import run_all_scanners
from policy.engine import PolicyEngine
from agentic_guard import agent as agent_module
from action_app.actions import apply_action
from tutor.stub_adapter import get_tutor_response
from audit.logger import log_audit
from metrics.metrics import agent_calls_total, agent_failures_total, scanner_latency, get_metrics
from prometheus_client import CONTENT_TYPE_LATEST
from deps import config

app = FastAPI(title="LMGuard Student MVP")

# CORS: ALLOWED_ORIGINS from config (comma-separated) or "*" (dev)
origins = [o.strip() for o in str(config.ALLOWED_ORIGINS).split(",")] if config.ALLOWED_ORIGINS else ["*"]
if origins == ["*"]:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
else:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Initialize policy engine (will raise if policy invalid)
try:
    policy_engine = PolicyEngine()
except Exception as e:
    # Fail-fast on invalid policy rather than silently fallback
    raise RuntimeError(f"Policy engine failed to initialize: {e}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)

@app.get("/admin/logs")
async def get_logs(limit: int = 20, x_admin_token: Optional[str] = Header(None)):
    """Get last N audit log entries. Protected by X-ADMIN-TOKEN header."""
    # admin token check
    if not config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token not configured on server.")
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token.")
    try:
        with open(config.LOG_FILE, 'r') as f:
            lines = f.readlines()
        recent_lines = lines[-limit:]
        logs = [json.loads(line) for line in recent_lines]
        return {"logs": logs, "count": len(logs)}
    except FileNotFoundError:
        return {"logs": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with guard logic (async)."""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Get latest user message
    user_messages = [m.content for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")
    user_message = user_messages[-1]

    # Basic input limits
    if len(user_message) > 8000:
        raise HTTPException(status_code=413, detail="Message too long")

    # Run scanners (sync as currently implemented)
    scanner_start = time.time()
    scanner_signals = run_all_scanners(user_message)
    scanner_latency.observe(time.time() - scanner_start)
    scanner_ms = int((time.time() - scanner_start) * 1000)

    # Evaluate policy
    policy_decision: PolicyDecision = policy_engine.evaluate(scanner_signals)

    # Agent decision (async) if borderline
    agent_decision: AgentDecision = None
    agent_ms = 0
    if policy_decision.action == "borderline":
        agent_calls_total.inc()
        agent_start = time.time()
        try:
            agent_decision = await agent_module.decide(user_message, scanner_signals, str(policy_engine.policy))
            if agent_decision.fallback:
                agent_failures_total.inc()
        except Exception as e:
            agent_failures_total.inc()
            # fallback to policy decision
            agent_decision = AgentDecision(action=policy_decision.action, confidence=0.0, explanation="Agent error - using policy fallback", fallback=True)
        agent_ms = int((time.time() - agent_start) * 1000)
    else:
        # Build synthetic AgentDecision from policy for consistent downstream handling
        agent_decision = AgentDecision(action=policy_decision.action, confidence=1.0, explanation=policy_decision.explanation, fallback=False)

    # If allowed, generate tutor response (stub)
    tutor_response = None
    if agent_decision.action == "allow":
        tutor_response = get_tutor_response(user_message)

    # Apply action
    result = apply_action(agent_decision, policy_decision, user_message, scanner_signals, tutor_response)

    # Log audit
    total_ms = int((time.time() - start_time) * 1000)
    log_audit(
        request_id=request_id,
        student_id=request.student_id or "anonymous",
        scanner_signals=scanner_signals,
        policy_decision=policy_decision.dict(),
        agent_decision=agent_decision.dict() if hasattr(agent_decision, "dict") else {},
        final_action=result.get("action"),
        latencies={"scanners_ms": scanner_ms, "agent_ms": agent_ms, "total_ms": total_ms}
    )

    return ChatResponse(action=result.get("action"), output=result.get("output"), policy_reason=result.get("policy_reason"), agent_confidence=getattr(agent_decision, "confidence", None))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)