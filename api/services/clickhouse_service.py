import time
from api.deps.clickhouse import get_clickhouse_client
from api.config import MAX_LIMIT, CREDITS_PER_100_RECORDS

client = get_clickhouse_client()

def count_query(sql: str, params=None):
    # Simple wrapper; client.query returns result object
    q = client.query(sql, parameters=params)
    rows = q.result_rows
    if rows:
        return int(rows[0][0])
    return 0

def execute_query(sql: str, params=None):
    result = client.query(sql, parameters=params)
    columns = result.column_names
    return [dict(zip(columns, row)) for row in result.result_rows]

def build_filter_clause(filters: dict):
    # Very small helper to build WHERE clauses; avoid SQL injection by using parameters
    clauses = []
    vals = {}
    i = 0
    for k, v in filters.items():
        if v is None or v == "":
            continue
        i += 1
        pname = f"p{i}"
        if k.endswith("_like"):
            col = k[:-5]
            clauses.append(f"{col} LIKE %({pname})s")
            vals[pname] = f"%{v}%"
        else:
            clauses.append(f"{k} = %({pname})s")
            vals[pname] = v
    where = " AND ".join(clauses) if clauses else "1=1"
    return where, vals

def estimate_credits_for_limit(limit: int) -> int:
    # 1 credit per 100 records (configurable)
    return max(1, (limit + 99) // 100 * CREDITS_PER_100_RECORDS)
