from aiogram import html
from sqlalchemy import select

from obeyd.bot import new_bot
from obeyd.models import Joke, async_session

LIKE_MESSAGE_TEMPLATE_BY_SCORE = {
    5: "{name} با جوکت زیر دلش درد گرفت! 😂",
    4: "{name} به جوکت خندید! 😁",
    3: "{name} به جوکت لبخند زد! 🙂",
    2: "{name} با جوکت حال نکرد! 😐",
    1: "{name} به نظرش بهتر بود جوک ننویسی! 💩",
}


async def notify_creator_like_joke_async(joke_id, score, from_user_nickname):
    bot = new_bot()

    async with async_session() as session:
        joke = await session.scalar(select(Joke).where(Joke.id == joke_id))

    if joke is None or joke.creator_id is None:
        return

    await bot.send_message(
        chat_id=joke.creator_id,
        text=f"""
{LIKE_MESSAGE_TEMPLATE_BY_SCORE[score].format(name=html.bold(from_user_nickname))}

جوک شما: {joke.text}
""",
    )

    await bot.close()
