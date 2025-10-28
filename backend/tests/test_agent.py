from unittest.mock import Mock, patch

from agentic_guard.agent import decide
from schemas import AgentDecision


@patch("agentic_guard.agent.httpx.post")
def test_agent_valid_response(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"action": "allow", "confidence": 0.9, "explanation": "Safe content", "rewrite": null}'}}]
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = decide("Hello", {}, "policy")
    assert isinstance(result, AgentDecision)
    assert result.action == "allow"
    assert result.confidence == 0.9


@patch("agentic_guard.agent.httpx.post")
def test_agent_timeout(mock_post):
    import httpx

    mock_post.side_effect = httpx.TimeoutException("Timeout")

    result = decide("Hello", {}, "policy")
    assert result.fallback is True
    assert result.action == "block"


@patch("agentic_guard.agent.httpx.post")
def test_agent_invalid_json(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "invalid json"}}]}
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = decide("Hello", {}, "policy")
    assert result.fallback is True


