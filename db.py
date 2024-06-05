import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine(os.environ["SQLALCHEMY_DATABASE_URI"])
async_session = async_sessionmaker(engine, expire_on_commit=False)
