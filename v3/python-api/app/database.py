from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine = None
_sessionmaker = None


def _get_sessionmaker():
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _sessionmaker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _sessionmaker


async def get_db() -> AsyncSession:
    maker = _get_sessionmaker()
    async with maker() as session:
        yield session
