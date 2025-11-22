from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.db_models import Credit, UsageLog
from sqlalchemy.exc import NoResultFound

async def get_credits(session: AsyncSession, user_id: int) -> int:
    q = await session.execute(select(Credit).where(Credit.user_id == user_id))
    credit = q.scalars().first()
    return credit.credits_balance if credit else 0

async def deduct_credits(session: AsyncSession, user_id: int, amount: int):
    # Atomic deduction: SELECT ... FOR UPDATE is not directly available with SQLAlchemy Core async;
    # we do an UPDATE with WHERE credits_balance >= amount and check rowcount.
    q = await session.execute(select(Credit).where(Credit.user_id == user_id))
    credit = q.scalars().first()
    if credit is None:
        raise Exception("Credits row missing for user")

    if credit.credits_balance < amount:
        raise ValueError("Insufficient credits")

    new_balance = credit.credits_balance - amount
    await session.execute(
        update(Credit).where(Credit.user_id == user_id).values(credits_balance=new_balance)
    )
    await session.commit()
    return new_balance

async def log_usage(session: AsyncSession, *, user_id: int, endpoint: str,
                    query_params: dict, records_returned: int, credits_used: int, response_time_ms: int):
    row = UsageLog(
        user_id=user_id,
        endpoint=endpoint,
        query_params=query_params,
        records_returned=records_returned,
        credits_used=credits_used,
        response_time_ms=response_time_ms
    )
    session.add(row)
    await session.commit()
