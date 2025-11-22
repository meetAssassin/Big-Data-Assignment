from fastapi import APIRouter, Depends, HTTPException
from api.deps.auth import get_current_user
from api.deps.clickhouse import get_clickhouse_client
from api.db.postgres import AsyncSessionLocal
from api.services.credit_service import deduct_credits, log_usage
from api.services.clickhouse_service import estimate_credits_for_limit
import time

router = APIRouter()

@router.get("/record/{canonical_key}")
async def get_record(canonical_key: str, current_user = Depends(get_current_user)):
    # single record fetch costs at least 1 credit
    credits_needed = estimate_credits_for_limit(1)

    async with AsyncSessionLocal() as session:
        try:
            await deduct_credits(session, current_user.id, credits_needed)
        except ValueError:
            raise HTTPException(status_code=402, detail="Insufficient Credits")

        start = time.time()
        client = get_clickhouse_client()
        sql = "SELECT * FROM master_records WHERE canonical_key = %s LIMIT 1"
        query_result = client.query(sql, parameters=[canonical_key])
        result = query_result.result_rows
        columns = query_result.column_names
        duration_ms = int((time.time() - start) * 1000)

        await log_usage(session,
                        user_id=current_user.id,
                        endpoint="/record/{canonical_key}",
                        query_params={"key": canonical_key},
                        records_returned=len(result),
                        credits_used=credits_needed,
                        response_time_ms=duration_ms)

    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    # column mapping
    row = dict(zip(columns, result[0]))
    return {"data": row, "metadata": {"credits_used": credits_needed, "response_time_ms": duration_ms}}
