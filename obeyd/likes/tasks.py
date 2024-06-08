from aiogram import html
from aiogram.methods import SendMessage
from sqlalchemy import select

from obeyd.models import Joke, async_session

LIKE_MESSAGE_TEMPLATE_BY_SCORE = {
    5: "{name} زیر دلش درد گرفت! 😂",
    4: "{name} به جوکت خندید! 😁",
    3: "{name} به جوکت لبخند زد! 🙂",
    2: "{name} با جوکت حال نکرد! 😐",
    1: "{name} به نظرش بهتر بود جوک ننویسی! 💩",
}


async def notify_creator_like_joke(joke_id, score, from_user_nickname):
    async with async_session() as session:
        joke = await session.scalar(select(Joke).where(Joke.id == joke_id))

    if joke is None or joke.creator_id is None:
        return

    await SendMessage(
        chat_id=joke.creator_id,
        text=f"""
{LIKE_MESSAGE_TEMPLATE_BY_SCORE[score].format(name=html.bold(from_user_nickname))}

جوک شما: {joke.text}
""",
    )
