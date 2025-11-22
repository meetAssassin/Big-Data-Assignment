from fastapi import HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.db.postgres import get_db
from api.models.db_models import ApiKey, User
from api.utils.security import hash_api_key

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def get_current_user(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db)
):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    hashed_key = hash_api_key(api_key)
    q = await db.execute(select(ApiKey).where(ApiKey.api_key == hashed_key))
    api_key_row = q.scalars().first()

    if not api_key_row:
        raise HTTPException(status_code=401, detail="Invalid API key")

    q = await db.execute(select(User).where(User.id == api_key_row.user_id))
    user = q.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
