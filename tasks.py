import asyncio
import json

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from celery import Celery

from telegram import new_bot

app = Celery("tasks", broker="redis://localhost:6379/0")

REVIEW_SUBMITTED_JOKES_CHAT_ID = "-1002196165890"
REVIEW_SUBMITTED_JOKES_TOPIC_ID = 34

SUBMIT_JOKE_NOTIF_ADMIN_MESSAGE_TEMPLATE = """
جوک جدیدی از طرف {from_user} ارسال شده است:

{joke_text}
"""


async def notify_admin_submit_joke_async(joke_id, joke_text, from_user):
    bot = new_bot()
    await bot.send_message(
        chat_id=REVIEW_SUBMITTED_JOKES_CHAT_ID,
        message_thread_id=REVIEW_SUBMITTED_JOKES_TOPIC_ID,
        text=SUBMIT_JOKE_NOTIF_ADMIN_MESSAGE_TEMPLATE.format(
            from_user=from_user,
            joke=joke_text,
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="تایید",
                        callback_data=json.dumps(
                            {
                                "type": "reject_joke",
                                "joke_id": joke_id,
                            }
                        ),
                    ),
                    InlineKeyboardButton(
                        text="رد",
                        callback_data=json.dumps(
                            {
                                "type": "accept_joke",
                                "joke_id": joke_id,
                            }
                        ),
                    ),
                ]
            ]
        ),
    )


@app.task
def notify_admin_submit_joke(joke_id, joke_text, from_user):
    asyncio.run(notify_admin_submit_joke_async(joke_id, joke_text, from_user))
