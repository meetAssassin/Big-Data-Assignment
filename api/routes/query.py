from fastapi import APIRouter, Depends, HTTPException, Query
from api.deps.auth import get_current_user
from api.db.postgres import AsyncSessionLocal
from api.services.clickhouse_service import build_filter_clause, estimate_credits_for_limit, count_query, execute_query
from api.services.credit_service import deduct_credits, log_usage
import time
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/query")
async def query_endpoint(
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    name_like: str | None = None,
    email_like: str | None = None,
    current_user = Depends(get_current_user)
):
    # enforce max limit
    from api.config import MAX_LIMIT
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT

    filters = {}
    if name_like:
        filters["name_like"] = name_like
    if email_like:
        filters["email_like"] = email_like

    where, params = build_filter_clause(filters)
    count_sql = f"SELECT count(*) FROM master_records WHERE {where}"
    total_records = count_query(count_sql, params)

    credits_needed = estimate_credits_for_limit(limit)

    # Deduct credits (use Postgres transaction)
    async with AsyncSessionLocal() as session:
        user = current_user
        try:
            await deduct_credits(session, user.id, credits_needed)
        except ValueError:
            raise HTTPException(status_code=402, detail="Insufficient Credits")

        start = time.time()
        # Query ClickHouse
        sql = f"SELECT * FROM master_records WHERE {where} LIMIT {limit} OFFSET {offset}"
        rows = execute_query(sql, params)
        duration_ms = int((time.time() - start) * 1000)

        # log usage
        await log_usage(session,
                        user_id=user.id,
                        endpoint="/query",
                        query_params={"limit": limit, "offset": offset, **filters},
                        records_returned=len(rows),
                        credits_used=credits_needed,
                        response_time_ms=duration_ms)

    # Return results + metadata
    return {
        "data": rows,
        "metadata": {
            "total_records": total_records,
            "credits_used": credits_needed,
            "response_time_ms": duration_ms
        }
    }
