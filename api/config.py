import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8443"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_SECURE = os.getenv("CLICKHOUSE_SECURE", "true").lower() in ("1", "true", "yes")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-key")
CREDITS_PER_100_RECORDS = int(os.getenv("CREDITS_PER_100_RECORDS", "1"))
MAX_LIMIT = int(os.getenv("MAX_LIMIT", "1000"))

print(CLICKHOUSE_USER)