import json
import time
import uuid
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from action_app.actions import apply_action
from agentic_guard.agent import decide as agent_decide
from audit.logger import log_audit
from deps import config
from metrics.metrics import (
    CONTENT_TYPE_LATEST,
    agent_calls_total,
    agent_failures_total,
    get_metrics,
    scanner_latency,
)
from policy.engine import PolicyEngine
from schemas import ChatRequest, ChatResponse, HealthResponse
from scanners.run_all import run_all_scanners
from tutor.stub_adapter import get_tutor_response


app = FastAPI(title="LMGuard Student MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


policy_engine = PolicyEngine()


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.get("/admin/logs")
def get_logs(limit: int = 20):
    try:
        with open(config.LOG_FILE, "r") as f:
            lines = f.readlines()
        recent_lines = lines[-limit:]
        logs = [json.loads(line) for line in recent_lines]
        return {"logs": logs, "count": len(logs)}
    except FileNotFoundError:
        return {"logs": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    user_messages: List[str] = [m.content for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")

    user_message = user_messages[-1]

    scanner_start = time.time()
    scanner_signals = run_all_scanners(user_message)
    scanner_latency.observe(time.time() - scanner_start)
    scanner_ms = int((time.time() - scanner_start) * 1000)

    policy_decision = policy_engine.evaluate(scanner_signals)

    agent_ms = 0
    if policy_decision.action == "borderline":
        agent_calls_total.inc()
        agent_start = time.time()
        try:
            agent_decision = agent_decide(user_message, scanner_signals, str(policy_engine.policy))
            if agent_decision.fallback:
                agent_failures_total.inc()
        except Exception:
            from schemas import AgentDecision
            agent_decision = AgentDecision(
                action=policy_decision.action,
                confidence=0.0,
                explanation="Agent error - using policy fallback",
                fallback=True,
            )
            agent_failures_total.inc()
        agent_ms = int((time.time() - agent_start) * 1000)
    else:
        from schemas import AgentDecision
        agent_decision = AgentDecision(
            action=policy_decision.action,
            confidence=1.0,
            explanation=policy_decision.explanation,
            fallback=False,
        )

    tutor_response = None
    if agent_decision.action == "allow":
        tutor_response = get_tutor_response(user_message)

    result = apply_action(agent_decision, policy_decision, user_message, scanner_signals, tutor_response)

    total_ms = int((time.time() - start_time) * 1000)
    log_audit(
        request_id=request_id,
        student_id=request.student_id or "anonymous",
        scanner_signals=scanner_signals,
        policy_decision=policy_decision.dict(),
        agent_decision=agent_decision.dict(),
        final_action=result["action"],
        latencies={"scanners_ms": scanner_ms, "agent_ms": agent_ms, "total_ms": total_ms},
    )

    return ChatResponse(
        action=result["action"],
        output=result["output"],
        policy_reason=result["policy_reason"],
        agent_confidence=agent_decision.confidence if agent_decision else None,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


