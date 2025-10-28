from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint():
    payload = {"messages": [{"role": "user", "content": "What is 2+2?"}], "student_id": "TEST123"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "action" in data and "output" in data and "policy_reason" in data


def test_chat_with_pii():
    payload = {"messages": [{"role": "user", "content": "My email is test@example.com"}]}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] in ["redact", "block"]


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "lmguard" in response.text


