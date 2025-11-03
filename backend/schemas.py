from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    student_id: Optional[str] = None


class ChatResponse(BaseModel):
    action: str
    output: str
    policy_reason: Optional[str] = None
    agent_confidence: Optional[float] = None


class HealthResponse(BaseModel):
    status: str


class PolicyDecision(BaseModel):
    action: str
    explanation: str
    severity: int


class AgentDecision(BaseModel):
    action: str
    confidence: float
    explanation: str
    rewrite: Optional[str] = None
    fallback: bool = False


