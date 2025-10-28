import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    OPENAI_KEY = os.getenv("OPENAI_KEY", "")
    POLICY_FILE = os.getenv("POLICY_FILE", "config/policy.yaml")
    AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "1.0"))
    CACHE_MAX_ITEMS = int(os.getenv("CACHE_MAX_ITEMS", "1000"))
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "OPENAI")
    LOG_FILE = os.getenv("LOG_FILE", "/data/lmguard_audit.json")
    HASH_SALT = os.getenv("HASH_SALT", "default-salt-change-in-prod")


config = Config()


