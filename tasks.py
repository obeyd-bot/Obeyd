import asyncio

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from celery import Celery
from sqlalchemy import select

from callbacks import ReviewJokeCallback
from telegram import new_bot

from models import Joke, async_session

app = Celery("tasks", broker="redis://localhost:6379/0")

REVIEW_SUBMITTED_JOKES_CHAT_ID = "-1002196165890"
REVIEW_SUBMITTED_JOKES_TOPIC_ID = 34

SUBMIT_JOKE_NOTIF_ADMIN_MESSAGE_TEMPLATE = """
جوک جدیدی از طرف {from_user} ارسال شده است:

{joke_text}
"""


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


async def notify_admin_submit_joke_async(joke_id, joke_text, from_user):
    bot = new_bot()
    await bot.send_message(
        chat_id=REVIEW_SUBMITTED_JOKES_CHAT_ID,
        message_thread_id=REVIEW_SUBMITTED_JOKES_TOPIC_ID,
        text=SUBMIT_JOKE_NOTIF_ADMIN_MESSAGE_TEMPLATE.format(
            from_user=from_user,
            joke_text=joke_text,
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="حذف",
                        callback_data=ReviewJokeCallback(
                            joke_id=joke_id, command="delete"
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="رد",
                        callback_data=ReviewJokeCallback(
                            joke_id=joke_id, command="reject"
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="تایید",
                        callback_data=ReviewJokeCallback(
                            joke_id=joke_id, command="accept"
                        ).pack(),
                    ),
                ]
            ]
        ),
    )


@app.task
def notify_creator_like_joke(joke_id, score):
    asyncio.run(notify_creator_like_joke_async(joke_id, score))


@app.task
def notify_admin_submit_joke(joke_id, joke_text, from_user):
    asyncio.run(notify_admin_submit_joke_async(joke_id, joke_text, from_user))
