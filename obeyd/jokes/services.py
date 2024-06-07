from typing import Tuple
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from obeyd.models import Joke, Like, SeenJoke


def accepted_jokes() -> Select[Tuple[Joke]]:
    return select(Joke).filter(Joke.accepted.is_(True))


def filter_seen_jokes(
    filter: Select[Tuple[Joke]], by_user_id: int
) -> Select[Tuple[Joke]]:
    seen_jokes = (
        select(SeenJoke.joke_id).where(SeenJoke.user_id == by_user_id).subquery()
    )
    return filter.join(seen_jokes, Joke.id == seen_jokes.c.joke_id, isouter=True).where(
        seen_jokes.c.joke_id.is_(None)
    )


async def random_joke(
    session: AsyncSession, filter: Select[Tuple[Joke]]
) -> Joke | None:
    return await session.scalar(filter.order_by(func.random()).limit(1))


async def most_rated_joke(
    session: AsyncSession, filter: Select[Tuple[Joke]]
) -> Joke | None:
    jokes_scores = (
        select(Like.joke_id, func.avg(Like.score).label("avg_score"))
        .group_by(Like.joke_id)
        .subquery()
    )
    return await session.scalar(
        filter.join(
            jokes_scores,
            Joke.id == jokes_scores.c.joke_id,
            isouter=True,
        )
        .order_by(jokes_scores.c.avg_score)
        .limit(1)
    )
