from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Metrics
agent_calls_total = Counter('lmguard_agent_calls_total', 'Total agent calls')
agent_failures_total = Counter('lmguard_agent_failures_total', 'Total agent failures')
scanner_latency = Histogram('lmguard_scanner_latency_seconds', 'Scanner latency')

def get_metrics():
    """Return prometheus metrics bytes."""
    return generate_latest()

# re-export constant for convenience
__all__ = [
    "agent_calls_total",
    "agent_failures_total",
    "scanner_latency",
    "get_metrics",
    "CONTENT_TYPE_LATEST"
]


