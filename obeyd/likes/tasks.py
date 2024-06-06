from sqlalchemy import select

from obeyd.bot import new_bot
from obeyd.models import Joke, async_session

LIKE_MESSAGE_TEMPLATE_BY_SCORE = {
    5: "یک نفر به جوک شما خیلی خندید 😂",
    4: "یک نفر به جوک شما خندید 😁",
    3: "یک نفر به جوک شما لبخند زد 🙂",
    2: "یک نفر متوجه جوک شما نشد 😐",
    1: "یک نفر از جوک شما خوشش نیومد 💩",
}


async def notify_creator_like_joke_async(joke_id, score):
    bot = new_bot()

    async with async_session() as session:
        joke = await session.scalar(select(Joke).where(Joke.id == joke_id))

    if joke is None or joke.creator_id is None:
        return

    await bot.send_message(
        chat_id=joke.creator_id,
        text=f"""
{LIKE_MESSAGE_TEMPLATE_BY_SCORE[score]}

جوک شما: {joke.text}
""",
    )

    await bot.close()
