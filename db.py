import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from models import Base

engine = create_async_engine("sqlite+aiosqlite:///db.sqlite", echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def sync_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(sync_db())
