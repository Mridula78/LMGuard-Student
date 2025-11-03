import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_KEY = os.getenv("OPENAI_KEY", "")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    POLICY_FILE = os.getenv("POLICY_FILE", "config/policy.yaml")
    AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "1.0"))
    CACHE_MAX_ITEMS = int(os.getenv("CACHE_MAX_ITEMS", "1000"))
    # Providers: OPENAI | GOOGLE | LOCAL
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "GOOGLE")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "GOOGLE")
    LOG_FILE = os.getenv("LOG_FILE", "/data/lmguard_audit.json")
    HASH_SALT = os.getenv("HASH_SALT", "default-salt-change-in-prod")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
    # Allowed origins. Comma separated list; default "*" for dev.
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

config = Config()


