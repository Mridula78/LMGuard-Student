import json
from datetime import datetime
from typing import Dict, List

import httpx
import jsonschema

from deps import config
from schemas import AgentDecision
from .cache import embedding_cache


SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["allow", "redact", "block", "rewrite_review"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "explanation": {"type": "string"},
        "rewrite": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["action", "confidence", "explanation"],
}


def _get_embedding(text: str) -> List[float]:
    if config.EMBEDDING_PROVIDER == "OPENAI":
        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {config.OPENAI_KEY}",
                    "Content-Type": "application/json",
                },
                json={"input": text, "model": "text-embedding-ada-002"},
                timeout=2.0,
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
        except Exception:
            return [float(ord(c)) for c in text[:100]]
    return [float(ord(c)) for c in text[:100]]


def decide(user_message: str, scanner_signals: Dict, policy_excerpt: str) -> AgentDecision:
    try:
        embedding = _get_embedding(user_message)
        cached = embedding_cache.query(embedding)
        if cached:
            return AgentDecision(**cached)
    except Exception:
        pass

    prompt = f"""You are LMGuard Decision Agent.
Input:
- user_message: "{user_message}"
- scanner_signals: {json.dumps(scanner_signals)}
- policy_excerpt: {policy_excerpt}

Task: Based on the scanners and policy excerpt, choose one action and explain briefly.
Return ONLY valid JSON matching the schema (no extra commentary):

{{
  "action": "allow" | "redact" | "block" | "rewrite_review",
  "confidence": 0.0-1.0,
  "explanation": "short reason (<120 chars)",
  "rewrite": null or "rewritten_text_if_applicable"
}}

Conservative rule: if unsure, prefer "rewrite_review" or "block"."""

    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENAI_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 200,
            },
            timeout=config.AGENT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        decision_dict = json.loads(content)
        jsonschema.validate(instance=decision_dict, schema=SCHEMA)

        try:
            embedding_cache.add(embedding, decision_dict, datetime.utcnow().isoformat())
        except Exception:
            pass

        return AgentDecision(**decision_dict)

    except (httpx.TimeoutException, httpx.HTTPError, json.JSONDecodeError, jsonschema.ValidationError, KeyError):
        return AgentDecision(action="block", confidence=0.0, explanation="Agent timeout or error", fallback=True)


