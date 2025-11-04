import uuid
import time
import json
from typing import Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from schemas import ChatRequest, ChatResponse, HealthResponse
from scanners.run_all import run_all_scanners
from policy.engine import PolicyEngine
from agentic_guard.agent import decide
from action_app.actions import apply_action
from tutor.gemini_adapter import get_tutor_response
from audit.logger import log_audit
from metrics.metrics import (
    agent_calls_total,
    agent_failures_total,
    scanner_latency,
    get_metrics,
    CONTENT_TYPE_LATEST
)
from deps import config


# Initialize policy engine at startup
policy_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global policy_engine
    # Startup
    try:
        policy_engine = PolicyEngine()
        print(f"[startup] Policy engine loaded from {config.POLICY_FILE}")
    except Exception as e:
        print(f"[startup] ERROR: Failed to load policy engine: {e}")
        raise
    
    yield
    
    # Shutdown
    print("[shutdown] LMGuard backend shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="LMGuard Student MVP",
    description="AI-powered tutoring system with built-in safety guardrails",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = config.ALLOWED_ORIGINS.split(",") if config.ALLOWED_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint with guard logic.
    
    Flow:
    1. Run scanners on user message
    2. Evaluate policy
    3. If borderline, call agentic guard
    4. Apply action (allow/redact/block/rewrite)
    5. Log audit trail
    6. Return response
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    latencies: Dict[str, float] = {}
    
    # Extract last user message
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    student_id = request.student_id or "anonymous"
    
    try:
        # Step 1: Run all scanners
        scanner_start = time.time()
        scanner_signals = run_all_scanners(user_message)
        scanner_latency.observe(time.time() - scanner_start)
        latencies["scanners"] = time.time() - scanner_start
        
        # Step 2: Evaluate policy
        policy_start = time.time()
        policy_decision = policy_engine.evaluate(scanner_signals)
        latencies["policy"] = time.time() - policy_start
        
        # Step 3: Agent decision (if borderline)
        agent_decision = None
        tutor_response = None
        
        if policy_decision.action == "borderline":
            agent_start = time.time()
            agent_calls_total.inc()
            
            try:
                # Get policy excerpt for agent context
                policy_excerpt = json.dumps({
                    "action": policy_decision.action,
                    "severity": policy_decision.severity,
                    "explanation": policy_decision.explanation
                })
                
                agent_decision = await decide(
                    user_message=user_message,
                    scanner_signals=scanner_signals,
                    policy_excerpt=policy_excerpt
                )
                
                if agent_decision.fallback:
                    agent_failures_total.inc()
                
            except Exception as e:
                agent_failures_total.inc()
                print(f"[agent] Error: {e}")
                # Fail-safe: default to block on agent error
                from schemas import AgentDecision
                agent_decision = AgentDecision(
                    action="block",
                    confidence=0.0,
                    explanation=f"Agent error: {str(e)}",
                    rewrite=None,
                    fallback=True
                )
            
            latencies["agent"] = time.time() - agent_start
        else:
            # Direct policy decision (no agent needed)
            from schemas import AgentDecision
            agent_decision = AgentDecision(
                action=policy_decision.action,
                confidence=1.0,
                explanation=policy_decision.explanation,
                rewrite=None,
                fallback=False
            )
        
        # Step 4: Get tutor response if allowed
        if agent_decision.action == "allow":
            tutor_start = time.time()
            try:
                tutor_response = get_tutor_response(
                    user_message,
                    constrain_to_teaching=True
                )
            except Exception as e:
                print(f"[tutor] Error: {e}")
                tutor_response = "I'm here to help you learn. Could you rephrase your question?"
            latencies["tutor"] = time.time() - tutor_start
        
        # Step 5: Apply action
        final_result = apply_action(
            agent_decision=agent_decision,
            policy_decision=policy_decision,
            user_message=user_message,
            scanner_signals=scanner_signals,
            tutor_response=tutor_response
        )
        
        # Step 6: Audit logging
        latencies["total"] = time.time() - start_time
        try:
            log_audit(
                request_id=request_id,
                student_id=student_id,
                scanner_signals=scanner_signals,
                policy_decision=policy_decision.dict(),
                agent_decision=agent_decision.dict() if agent_decision else {},
                final_action=final_result["action"],
                latencies=latencies
            )
        except Exception as e:
            print(f"[audit] Logging failed: {e}")
        
        # Step 7: Return response
        return ChatResponse(
            action=final_result["action"],
            output=final_result["output"],
            policy_reason=final_result["policy_reason"],
            agent_confidence=agent_decision.confidence if agent_decision else None
        )
    
    except Exception as e:
        print(f"[chat] Unhandled error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/admin/logs")
async def get_logs(
    limit: int = 20,
    authorization: str = Header(None)
):
    """
    Retrieve recent audit logs (admin only).
    Requires ADMIN_TOKEN in Authorization header.
    """
    if config.ADMIN_TOKEN and authorization != f"Bearer {config.ADMIN_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        import os
        if not os.path.exists(config.LOG_FILE):
            return {"logs": [], "message": "No logs found"}
        
        with open(config.LOG_FILE, 'r') as f:
            lines = f.readlines()
        
        # Get last N lines
        recent_lines = lines[-limit:] if len(lines) > limit else lines
        logs = [json.loads(line.strip()) for line in recent_lines if line.strip()]
        
        return {
            "logs": logs,
            "count": len(logs),
            "total_entries": len(lines)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)