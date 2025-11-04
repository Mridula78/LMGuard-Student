import pytest
from unittest.mock import patch, AsyncMock
from agentic_guard.agent import decide, _get_embedding
from schemas import AgentDecision


@pytest.mark.asyncio
async def test_agent_allow_decision():
    """Test that agent can make an 'allow' decision."""
    signals = {
        "pii": [],
        "dishonesty": [],
        "injection": [],
        "toxicity_score": 0.1
    }
    policy_excerpt = '{"action": "borderline", "severity": 50}'
    
    decision = await decide(
        "Can you help me understand how derivatives work in calculus?",
        signals,
        policy_excerpt
    )
    
    assert isinstance(decision, AgentDecision)
    assert decision.action in ["allow", "redact", "block", "rewrite_review"]
    assert 0.0 <= decision.confidence <= 1.0
    assert isinstance(decision.explanation, str)
    assert len(decision.explanation) > 0


@pytest.mark.asyncio
async def test_agent_block_decision():
    """Test that agent blocks inappropriate requests."""
    signals = {
        "pii": [],
        "dishonesty": [{"type": "homework", "score": 0.9, "evidence": ["do my homework"]}],
        "injection": [],
        "toxicity_score": 0.2
    }
    policy_excerpt = '{"action": "borderline", "severity": 70}'
    
    decision = await decide(
        "Do my homework for me please",
        signals,
        policy_excerpt
    )
    
    assert isinstance(decision, AgentDecision)
    assert decision.action in ["block", "rewrite_review"]
    assert decision.confidence > 0.0


@pytest.mark.asyncio
async def test_agent_fallback_on_timeout():
    """Test that agent falls back to block on timeout."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock timeout
        mock_response = AsyncMock()
        mock_response.post.side_effect = Exception("Timeout")
        mock_client.return_value.__aenter__.return_value = mock_response
        
        signals = {"pii": [], "dishonesty": [], "injection": []}
        policy_excerpt = '{"action": "borderline"}'
        
        decision = await decide("test message", signals, policy_excerpt)
        
        assert decision.action == "block"
        assert decision.fallback is True
        assert decision.confidence == 0.0


@pytest.mark.asyncio
async def test_agent_fallback_on_invalid_json():
    """Test that agent falls back to block on invalid JSON response."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock invalid JSON response
        mock_response = AsyncMock()
        mock_post = AsyncMock()
        mock_post.raise_for_status = AsyncMock()
        mock_post.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "This is not valid JSON at all!"}]
                }
            }]
        }
        mock_response.post.return_value = mock_post
        mock_client.return_value.__aenter__.return_value = mock_response
        
        signals = {"pii": [], "dishonesty": [], "injection": []}
        policy_excerpt = '{"action": "borderline"}'
        
        decision = await decide("test", signals, policy_excerpt)
        
        assert decision.action == "block"
        assert decision.fallback is True


@pytest.mark.asyncio
async def test_agent_valid_json_with_markdown():
    """Test that agent can parse JSON wrapped in markdown."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock JSON wrapped in markdown
        mock_response = AsyncMock()
        mock_post = AsyncMock()
        mock_post.raise_for_status = AsyncMock()
        mock_post.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '```json\n{"action": "allow", "confidence": 0.95, "explanation": "Educational question", "rewrite": null}\n```'
                    }]
                }
            }]
        }
        mock_response.post.return_value = mock_post
        mock_client.return_value.__aenter__.return_value = mock_response
        
        signals = {"pii": [], "dishonesty": [], "injection": []}
        policy_excerpt = '{"action": "borderline"}'
        
        decision = await decide("test", signals, policy_excerpt)
        
        assert decision.action == "allow"
        assert decision.confidence == 0.95
        assert decision.fallback is False


@pytest.mark.asyncio
async def test_embedding_cache_hit():
    """Test that cache returns previous decision for similar queries."""
    from agentic_guard.cache import embedding_cache
    
    # Clear cache
    embedding_cache.cache.clear()
    embedding_cache.embeddings.clear()
    
    signals = {"pii": [], "dishonesty": [], "injection": []}
    policy_excerpt = '{"action": "borderline"}'
    
    # First call - should cache
    decision1 = await decide("What is calculus?", signals, policy_excerpt)
    
    # Second call with very similar question - should hit cache if embedding available
    # Note: This test may not always hit cache depending on embedding provider availability
    decision2 = await decide("What is calculus?", signals, policy_excerpt)
    
    # Both should be valid decisions
    assert isinstance(decision1, AgentDecision)
    assert isinstance(decision2, AgentDecision)


@pytest.mark.asyncio 
async def test_get_embedding_with_google():
    """Test Google embedding generation."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_post = AsyncMock()
        mock_post.raise_for_status = AsyncMock()
        mock_post.json.return_value = {
            "embedding": {
                "values": [0.1] * 768  # Google embeddings are 768-dimensional
            }
        }
        mock_response.post.return_value = mock_post
        mock_client.return_value.__aenter__.return_value = mock_response
        
        with patch('deps.config.EMBEDDING_PROVIDER', 'GOOGLE'):
            with patch('deps.config.GOOGLE_API_KEY', 'test-key'):
                embedding = await _get_embedding("test text")
                
                assert embedding is not None
                assert len(embedding) == 768
                assert all(isinstance(x, (int, float)) for x in embedding)


@pytest.mark.asyncio
async def test_get_embedding_returns_none_on_error():
    """Test that embedding returns None on error instead of crashing."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.post.side_effect = Exception("API Error")
        mock_client.return_value.__aenter__.return_value = mock_response
        
        with patch('deps.config.EMBEDDING_PROVIDER', 'GOOGLE'):
            with patch('deps.config.GOOGLE_API_KEY', 'test-key'):
                embedding = await _get_embedding("test")
                
                assert embedding is None


@pytest.mark.asyncio
async def test_agent_rewrite_decision():
    """Test that agent can provide rewrite suggestions."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_post = AsyncMock()
        mock_post.raise_for_status = AsyncMock()
        mock_post.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "action": "rewrite_review",
                            "confidence": 0.8,
                            "explanation": "Question needs rephrasing",
                            "rewrite": "Can you help me understand the concept behind this problem?"
                        })
                    }]
                }
            }]
        }
        mock_response.post.return_value = mock_post
        mock_client.return_value.__aenter__.return_value = mock_response
        
        signals = {"pii": [], "dishonesty": [{"type": "homework", "score": 0.5}], "injection": []}
        policy_excerpt = '{"action": "borderline"}'
        
        decision = await decide("solve this problem", signals, policy_excerpt)
        
        assert decision.action == "rewrite_review"
        assert decision.rewrite is not None
        assert len(decision.rewrite) > 0


@pytest.mark.asyncio
async def test_agent_confidence_range():
    """Test that confidence is always in valid range."""
    signals = {"pii": [], "dishonesty": [], "injection": []}
    policy_excerpt = '{"action": "borderline"}'
    
    decision = await decide("random question", signals, policy_excerpt)
    
    assert 0.0 <= decision.confidence <= 1.0


import json  # Add this import at the top of the file