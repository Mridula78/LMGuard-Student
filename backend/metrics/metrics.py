from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST


agent_calls_total = Counter('lmguard_agent_calls_total', 'Total agent calls')
agent_failures_total = Counter('lmguard_agent_failures_total', 'Total agent failures')
scanner_latency = Histogram('lmguard_scanner_latency_seconds', 'Scanner latency')


def get_metrics():
    return generate_latest()


