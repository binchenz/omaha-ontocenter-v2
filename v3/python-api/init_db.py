# For SQLite local dev
import asyncio
from app.database import engine, Base
from app.models import *  # noqa: F401,F403


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init())
    print("Database initialized")
