from clickhouse_connect import get_client
from api.config import CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_SECURE

_client = None

def get_clickhouse_client():
    global _client
    if _client is None:
        _client = get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            secure=CLICKHOUSE_SECURE
        )
    return _client
