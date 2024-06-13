import datetime
import os
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import expression
from sqlalchemy.types import String

engine = create_async_engine(os.environ["SQLALCHEMY_DATABASE_URI"])
async_session = async_sessionmaker(engine, expire_on_commit=False)


NICKNAME_MAX_LENGTH = 100


class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON}


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )

    nickname: Mapped[str] = mapped_column(
        String(NICKNAME_MAX_LENGTH), unique=True, nullable=True, server_default=None
    )

    joined_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class Joke(Base):
    __tablename__ = "jokes"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(3500))

    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    creator: Mapped[User] = relationship()

    creator_nickname: Mapped[str] = mapped_column(String(NICKNAME_MAX_LENGTH))

    accepted: Mapped[bool] = mapped_column(server_default=expression.false())

    updated_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class SeenJoke(Base):
    __tablename__ = "seen_jokes"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    user: Mapped[User] = relationship()
    joke_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jokes.id"))
    joke: Mapped[Joke] = relationship()

    seen_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "joke_id", name="seen_jokes_user_id_joke_id_key"),
    )


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    user: Mapped[User] = relationship()
    joke_id: Mapped[int] = mapped_column(ForeignKey("jokes.id"))
    joke: Mapped[Joke] = relationship()
    score: Mapped[int]

    liked_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "joke_id", name="user_id_joke_id_key"),
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)

    kind: Mapped[str]
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    user: Mapped[User] = relationship()
    data: Mapped[dict[str, Any]]

    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
