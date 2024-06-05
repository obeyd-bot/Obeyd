import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import String


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Joke(Base):
    __tablename__ = "jokes"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(280))

    creator_user_id: Mapped[int] = mapped_column(nullable=True)

    updated_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), server_onupdate=func.now()
    )
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    joke_id: Mapped[int] = mapped_column(ForeignKey("jokes.id"))
    joke: Mapped[Joke] = relationship()
    score: Mapped[int]

    liked_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "joke_id", name="user_id_joke_id_key"),
    )
