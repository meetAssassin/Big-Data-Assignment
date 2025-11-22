from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete")
    credits = relationship("Credit", uselist=False, back_populates="user", cascade="all, delete")

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_key = Column(String(64), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="api_keys")

class Credit(Base):
    __tablename__ = "credits"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    credits_balance = Column(Integer, default=1000)
    updated_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="credits")

class UsageLog(Base):
    __tablename__ = "usage_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    endpoint = Column(String(255))
    query_params = Column(JSON)
    records_returned = Column(Integer)
    credits_used = Column(Integer)
    response_time_ms = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())
