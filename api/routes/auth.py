from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.db.postgres import get_db
from api.models.db_models import User, ApiKey, Credit
from api.utils.security import generate_api_key
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])


class SignupRequest(BaseModel):
    name: str
    email: str


@router.post("/signup")
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    # STEP 1: Check if user already exists
    q = await db.execute(select(User).where(User.email == payload.email))
    existing = q.scalars().first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # STEP 2: Create new user
    new_user = User(
        name=payload.name,
        email=payload.email,
        is_admin=False
    )
    db.add(new_user)
    await db.flush()  # Assigns new_user.id

    # STEP 3: Generate API key
    plain_api_key, hashed_api_key = generate_api_key()

    new_key = ApiKey(
        user_id=new_user.id,
        api_key=hashed_api_key
    )
    db.add(new_key)

    # STEP 4: Give starting credits
    credit = Credit(
        user_id=new_user.id,
        credits_balance=100  # default signup credits
    )
    db.add(credit)

    # STEP 5: Commit
    await db.commit()

    # STEP 6: Return the plain key (only time it will be shown!)
    return {
        "message": "Signup successful",
        "user_id": new_user.id,
        "api_key": plain_api_key,
        "credits": 100
    }
