from fastapi import APIRouter, HTTPException, Header
from api.db.postgres import AsyncSessionLocal
from api.models.db_models import Credit, User
from sqlalchemy import insert, update, select

router = APIRouter()

@router.post("/admin/topup")
async def topup_user(user_email: str, amount: int, x_admin_key: str | None = Header(None)):
    from api.config import ADMIN_API_KEY
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    async with AsyncSessionLocal() as session:
        # find user
        res = await session.execute(select(User).where(User.email == user_email))
        user = res.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # upsert credits
        res = await session.execute(select(Credit).where(Credit.user_id == user.id))
        credit = res.scalars().first()
        if credit:
            new_balance = credit.credits_balance + amount
            await session.execute(update(Credit).where(Credit.user_id == user.id).values(credits_balance=new_balance))
        else:
            stmt = insert(Credit).values(user_id=user.id, credits_balance=amount)
            await session.execute(stmt)
        await session.commit()

    return {"status": "ok", "user_id": user.id, "added": amount}
