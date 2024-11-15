import os
from dotenv import load_dotenv
from datetime import datetime

from sqlalchemy import BigInteger, String, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs

load_dotenv()

database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+asyncpg://', 1)

engine = create_async_engine(database_url)
async_session = async_sessionmaker(engine)


# Define Base class
class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)  # Added unique constraint
    is_authorized: Mapped[bool] = mapped_column(default=False)


class Person(Base):
    __tablename__ = 'persons'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(15), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Loan(Base):
    __tablename__ = 'loans'

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('persons.id'))
    total_amount: Mapped[float] = mapped_column(Float)
    remaining_amount: Mapped[float] = mapped_column(Float)
    payment_frequency: Mapped[str] = mapped_column(String(10))  # 'weekly' or 'monthly'
    number_of_payments: Mapped[int] = mapped_column(Integer)
    payment_amount: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[str] = mapped_column(String(20), default='active')


class BannedUser(Base):
    __tablename__ = 'banned_users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    banned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    reason: Mapped[str] = mapped_column(String(100))


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def recreate_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
