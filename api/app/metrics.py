from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from fastapi import Request, Response
import time

# painel 3
http_requests_total = Counter(
    'http_requests_total',
    'Total de requisições HTTP',
    ['method', 'handler', 'status']
)

# painel 8
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'Duração das requisições HTTP em segundos',
    ['method', 'handler'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# ws
websocket_connections = Gauge(
    'websocket_connections_active',
    'Número de conexões WebSocket ativas'
)

websocket_messages_total = Counter(
    'websocket_messages_total',
    'Total de mensagens WebSocket enviadas',
    ['chat_id']
)


async def metrics_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    method = request.method
    handler = request.url.path
    status = str(response.status_code)
    
    http_requests_total.labels(
        method=method,
        handler=handler,
        status=status
    ).inc()
    
    http_request_duration_seconds.labels(
        method=method,
        handler=handler
    ).observe(duration)
    
    return response


def get_metrics():
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain"
    )


def increment_websocket_connections():
    websocket_connections.inc()


def decrement_websocket_connections():
    websocket_connections.dec()


def record_websocket_message(chat_id: int):
    websocket_messages_total.labels(chat_id=str(chat_id)).inc()