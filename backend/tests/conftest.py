import os

# Set test environment variables
os.environ["POLICY_FILE"] = "config/policy.yaml"
os.environ["LOG_FILE"] = "/tmp/test_audit.json"
os.environ["HASH_SALT"] = "test-salt"
os.environ["AGENT_TIMEOUT_SECONDS"] = "0.5"


