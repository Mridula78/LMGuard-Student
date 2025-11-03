import json
import httpx
import jsonschema
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from schemas import AgentDecision
from deps import config
from .cache import embedding_cache

# JSON schema (duplicate from file for runtime validation)
SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["allow","redact","block","rewrite_review"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "explanation": {"type": "string"},
        "rewrite": {"anyOf": [{"type": "string"}, {"type": "null"}]}
    },
    "required": ["action", "confidence", "explanation"]
}

async def _get_embedding(text: str) -> Optional[List[float]]:
    """Get embedding for text (async). On failure return None or fallback vector."""
    if config.EMBEDDING_PROVIDER == "GOOGLE" and config.GOOGLE_API_KEY:
        # Google AI Studio Embeddings: text-embedding-004
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedText",
                    params={"key": config.GOOGLE_API_KEY},
                    headers={"Content-Type": "application/json"},
                    json={"text": text},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding", {}).get("value", data.get("embedding", {}).get("values")) or data["embedding"]["values"]
        except Exception:
            return None
    # Deterministic lightweight fallback embedding (not ideal for production)
    return [float(ord(c)) for c in text[:128]]

async def decide(user_message: str, scanner_signals: Dict, policy_excerpt: str) -> AgentDecision:
    """Async decision call to an LLM agent with caching and validation."""
    embedding = None
    # Try to compute embedding and check cache
    try:
        embedding = await _get_embedding(user_message)
        if embedding is not None:
            cached = embedding_cache.query(embedding)
            if cached:
                # cached is a dict compatible with AgentDecision
                return AgentDecision(**cached)
    except Exception:
        embedding = None

    # Build a safe structured prompt: system message describes task; user message contains JSON payload
    system_msg = (
        "You are LMGuard Decision Agent. Based on the provided user_message, "
        "scanner_signals JSON, and policy excerpt, decide a single action. "
        "Return ONLY valid JSON matching the schema provided. Be conservative."
    )
    user_payload = {
        "user_message": user_message,
        "scanner_signals": scanner_signals,
        "policy_excerpt": policy_excerpt
    }
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": json.dumps(user_payload)}
    ]

    try:
        async with httpx.AsyncClient(timeout=config.AGENT_TIMEOUT_SECONDS + 1.0) as client:
            if getattr(config, "LLM_PROVIDER", "GOOGLE") == "GOOGLE" and config.GOOGLE_API_KEY:
                # Gemini generateContent API
                resp = await client.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                    params={"key": config.GOOGLE_API_KEY},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [
                            {"role": "system", "parts": [{"text": system_msg}]},
                            {"role": "user", "parts": [{"text": json.dumps(user_payload)}]},
                        ]
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                # Extract text
                candidates = data.get("candidates", [])
                content = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
            else:
                # Fallback to OpenAI if configured
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.OPENAI_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 300
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        # Agent error -> conservative fallback (block). Mark fallback True.
        return AgentDecision(action="block", confidence=0.0, explanation="Agent timeout or error", rewrite=None, fallback=True)
    # sanitize content: extract JSON if wrapped in triple backticks
    content = content.strip()
    if content.startswith("```"):
        # remove code fences
        parts = content.split("```")
        # try to find JSON block
        for p in parts:
            try:
                parsed = json.loads(p.strip())
                content = json.dumps(parsed)
                break
            except Exception:
                continue
    # try parse JSON
    try:
        decision_dict = json.loads(content)
        # validate
        jsonschema.validate(instance=decision_dict, schema=SCHEMA)
    except Exception:
        # invalid JSON or schema -> fallback block
        return AgentDecision(action="block", confidence=0.0, explanation="Agent returned invalid JSON", rewrite=None, fallback=True)

    # cache decision if embedding exists
    try:
        if embedding is not None:
            embedding_cache.add(embedding, decision_dict, datetime.utcnow().isoformat())
    except Exception:
        pass

    return AgentDecision(**decision_dict)


