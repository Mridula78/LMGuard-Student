import pytest

from policy.engine import PolicyEngine


@pytest.fixture
def engine():
    return PolicyEngine()


def test_benign_content(engine):
    signals = {"pii": [], "dishonesty": [], "injection": [], "toxicity_score": 0.1}
    decision = engine.evaluate(signals)
    assert decision.action == "allow"


def test_pii_redact(engine):
    signals = {"pii": [{"type": "email", "match": "test@test.com", "span": [0, 0]}], "dishonesty": [], "injection": [], "toxicity_score": 0.0}
    decision = engine.evaluate(signals)
    assert decision.action == "redact"


def test_injection_block(engine):
    signals = {"pii": [], "dishonesty": [], "injection": [{"type": "prompt_injection"}], "toxicity_score": 0.0}
    decision = engine.evaluate(signals)
    assert decision.action == "block"
    assert decision.severity >= 90


def test_dishonesty_borderline(engine):
    signals = {"pii": [], "dishonesty": [{"type": "homework", "score": 0.8}], "injection": [], "toxicity_score": 0.0}
    decision = engine.evaluate(signals)
    assert decision.action in ["borderline", "block"]


