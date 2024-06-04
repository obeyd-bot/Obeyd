import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from models import Base
import os

db_host = os.environ["DB_HOST"]
db_port = os.environ["DB_PORT"]
db_user = os.environ["DB_USER"]
db_pass = os.environ["DB_PASS"]
db_name = os.environ["DB_NAME"]

engine = create_async_engine(
    f"postgresql+aiopg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}",
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def sync_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(sync_db())
