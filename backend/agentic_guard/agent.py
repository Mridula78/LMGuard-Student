import json
import httpx
import jsonschema
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from schemas import AgentDecision
from deps import config
from .cache import embedding_cache

# JSON schema for validation
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
    """
    Get embedding for text (async).
    Returns None on failure - cache will skip caching for this request.
    """
    if config.EMBEDDING_PROVIDER == "GOOGLE" and config.GOOGLE_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedText",
                    params={"key": config.GOOGLE_API_KEY},
                    headers={"Content-Type": "application/json"},
                    json={"content": {"parts": [{"text": text}]}},
                )
                resp.raise_for_status()
                data = resp.json()
                
                # Extract embedding from response
                embedding_obj = data.get("embedding", {})
                values = embedding_obj.get("values") or embedding_obj.get("value")
                
                if values and isinstance(values, list):
                    return values
                
                print(f"[embedding] Unexpected response format: {data}")
                return None
                
        except httpx.TimeoutException:
            print("[embedding] Timeout getting embedding")
            return None
        except httpx.HTTPError as e:
            print(f"[embedding] HTTP error: {e}")
            return None
        except Exception as e:
            print(f"[embedding] Unexpected error: {e}")
            return None
    
    elif config.EMBEDDING_PROVIDER == "OPENAI" and config.OPENAI_KEY:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {config.OPENAI_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": text,
                        "model": "text-embedding-3-small"
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            print(f"[embedding] OpenAI error: {e}")
            return None
    
    # No valid provider configured - skip caching
    return None

async def decide(user_message: str, scanner_signals: Dict, policy_excerpt: str) -> AgentDecision:
    """
    Async decision call to an LLM agent with caching and validation.
    
    Returns AgentDecision with action, confidence, explanation, and optional rewrite.
    On error, returns fail-safe block decision with fallback=True.
    """
    embedding = None
    
    # Try to compute embedding and check cache
    try:
        embedding = await _get_embedding(user_message)
        if embedding is not None:
            cached = embedding_cache.query(embedding)
            if cached:
                print("[agent] Cache hit")
                return AgentDecision(**cached)
    except Exception as e:
        print(f"[agent] Cache check error: {e}")
        embedding = None

    # Build structured prompt
    system_msg = (
        "You are LMGuard Decision Agent. Analyze the user's message in an educational context. "
        "Based on scanner signals and policy, decide ONE action from: allow, redact, block, rewrite_review. "
        "Return ONLY valid JSON matching this exact schema:\n"
        '{"action": "allow|redact|block|rewrite_review", "confidence": 0.0-1.0, "explanation": "brief reason", "rewrite": null or "improved message"}\n'
        "Be conservative - prioritize student safety and academic integrity."
    )
    
    user_payload = {
        "user_message": user_message,
        "scanner_signals": scanner_signals,
        "policy_excerpt": policy_excerpt,
        "instructions": "Respond with JSON only. No markdown, no explanation outside JSON."
    }
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": json.dumps(user_payload, indent=2)}
    ]

    # Call LLM
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
                            {
                                "role": "user",
                                "parts": [
                                    {"text": system_msg},
                                    {"text": json.dumps(user_payload, indent=2)}
                                ]
                            }
                        ],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 300
                        }
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                
                # Safe extraction of response text
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidates in Gemini response")
                
                content_obj = candidates[0].get("content", {})
                parts = content_obj.get("parts", [])
                
                if not parts:
                    raise ValueError("No parts in Gemini response")
                
                content = parts[0].get("text", "").strip()
                
                if not content:
                    raise ValueError("Empty text in Gemini response")
                
            else:
                # OpenAI fallback
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
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        print(f"[agent] LLM call failed: {e}")
        return AgentDecision(
            action="block",
            confidence=0.0,
            explanation="Agent timeout - request blocked for safety",
            rewrite=None,
            fallback=True
        )
    except Exception as e:
        print(f"[agent] Unexpected error: {e}")
        return AgentDecision(
            action="block",
            confidence=0.0,
            explanation=f"Agent error: {str(e)}",
            rewrite=None,
            fallback=True
        )
    
    # Parse and validate JSON response
    try:
        # Remove markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Find JSON content between fences
            json_lines = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or (not line.strip().startswith("```")):
                    json_lines.append(line)
            content = "\n".join(json_lines).strip()
        
        # Parse JSON
        decision_dict = json.loads(content)
        
        # Validate against schema
        jsonschema.validate(instance=decision_dict, schema=SCHEMA)
        
    except json.JSONDecodeError as e:
        print(f"[agent] JSON parse error: {e}\nContent: {content[:200]}")
        return AgentDecision(
            action="block",
            confidence=0.0,
            explanation="Agent returned invalid JSON",
            rewrite=None,
            fallback=True
        )
    except jsonschema.ValidationError as e:
        print(f"[agent] Schema validation error: {e}")
        return AgentDecision(
            action="block",
            confidence=0.0,
            explanation="Agent returned invalid response format",
            rewrite=None,
            fallback=True
        )
    except Exception as e:
        print(f"[agent] Validation error: {e}")
        return AgentDecision(
            action="block",
            confidence=0.0,
            explanation="Agent response validation failed",
            rewrite=None,
            fallback=True
        )
    
    # Cache decision if embedding exists
    try:
        if embedding is not None:
            embedding_cache.add(embedding, decision_dict, datetime.utcnow().isoformat())
            print("[agent] Decision cached")
    except Exception as e:
        print(f"[agent] Cache add error: {e}")
    
    return AgentDecision(**decision_dict)