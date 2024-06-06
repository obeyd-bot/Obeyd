from sqlalchemy import select

from obeyd.bot import new_bot
from obeyd.models import Joke, async_session

LIKE_JOKE_NOTIF_CREATOR_MESSAGE_TEMPLATE = """
کسی به جوکت امتیاز {score} رو داده. متن جوک:

{joke_text}
"""


async def notify_creator_like_joke_async(joke_id, score):
    bot = new_bot()

    async with async_session() as session:
        joke = await session.scalar(select(Joke).where(Joke.id == joke_id))

    if joke is None:
        return

    await bot.send_message(
        chat_id=joke.creator_user_id,
        text=LIKE_JOKE_NOTIF_CREATOR_MESSAGE_TEMPLATE.format(
            score=score, joke_text=joke.text
        ),
    )
