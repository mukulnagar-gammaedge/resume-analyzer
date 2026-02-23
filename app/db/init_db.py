import asyncio
from app.db.session import async_engine
from app.db.base import Base
from app.models import job  # important import

async def init_models():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_models())
