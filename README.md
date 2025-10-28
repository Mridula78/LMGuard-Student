# LMGuard Student MVP

AI-powered tutoring system with built-in safety guardrails for educational environments.

## Architecture

- **Frontend**: React + TypeScript (deployed on Vercel)
- **Backend**: FastAPI + Python (deployed on Render)
- **Guard System**: Multi-layer protection (scanners → policy engine → agentic guard)

## Features

- ✅ PII Detection & Redaction
- ✅ Academic Dishonesty Detection
- ✅ Prompt Injection Protection
- ✅ Agentic Decision-Making with LLM
- ✅ Semantic Caching (Embedding-based LRU)
- ✅ Audit Logging (Pseudonymized)
- ✅ Prometheus Metrics
- ✅ Fail-Safe Design (timeouts, fallbacks)

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (optional)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your OPENAI_KEY

# Create data directory for logs
mkdir -p /data

# Run backend
uvicorn main:app --reload
```

Backend runs at http://localhost:8000

### 2. Frontend Setup

```bash
cd frontend
npm install

# Create .env file
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Run frontend
npm start
```

Frontend runs at http://localhost:3000

### 3. Using Docker Compose

```bash
# From project root
docker-compose up --build
```

## API Endpoints

### POST /chat
Main chat endpoint with guard logic.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Help me understand calculus"}
  ],
  "student_id": "S123"
}
```

**Response:**
```json
{
  "action": "allow",
  "output": "Let me explain calculus concepts...",
  "policy_reason": "Content allowed.",
  "agent_confidence": 0.95
}
```

### GET /health
Health check endpoint.

### GET /metrics
Prometheus metrics in text format.

### GET /admin/logs?limit=20
Retrieve recent audit logs (pseudonymized).

## Guard System Flow

```
User Message
    ↓
Scanners (PII, Dishonesty, Injection, Toxicity)
    ↓
Policy Engine (Evaluate against policy.yaml)
    ↓
[If borderline] → Agentic Guard (LLM decides with cache)
    ↓
Action Application (allow/redact/block/rewrite_review)
    ↓
Audit Logging + Metrics
    ↓
Response to User
```

## Configuration

Edit `backend/config/policy.yaml` to customize policies:

```yaml
categories:
  pii:
    action: redact
    severity: 80
  academic_dishonesty:
    action: borderline  # Sends to agent for review
    severity: 70
  injection:
    action: block
    severity: 90
```

## Testing

```bash
cd backend
pytest tests/ -v
```

## Deployment

### Backend (Render)
1. Create new Web Service on Render
2. Connect GitHub repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`

### Frontend (Vercel)
1. Connect GitHub repo to Vercel
2. Set framework preset: Create React App
3. Set environment variable: `REACT_APP_API_URL=<your-render-url>`
4. Deploy

## Monitoring

- **Metrics**: Access `/metrics` endpoint for Prometheus scraping
- **Logs**: Access `/admin/logs` for audit trail
- **Health**: Monitor `/health` endpoint for uptime

## Security Notes

- Student IDs are hashed with salt before logging
- PII is redacted from audit logs
- Agent decisions cached using embeddings (not raw text)
- Fail-safe defaults to block on errors
- Rate limiting recommended for production

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_KEY` | OpenAI API key for agent & embeddings | Required |
| `POLICY_FILE` | Path to policy YAML | `/app/config/policy.yaml` |
| `AGENT_TIMEOUT_SECONDS` | Agent timeout | `1.0` |
| `CACHE_MAX_ITEMS` | Max cache entries | `1000` |
| `EMBEDDING_PROVIDER` | `OPENAI` or `LOCAL` | `OPENAI` |
| `LOG_FILE` | Audit log file path | `/data/lmguard_audit.json` |
| `HASH_SALT` | Salt for hashing student IDs | Change in production! |

## License

MIT License - See LICENSE file for details.

## Support

For issues or questions, please open a GitHub issue.


