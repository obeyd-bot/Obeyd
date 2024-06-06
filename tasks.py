import asyncio
import aiogram
from celery import Celery

from telegram import new_bot

app = Celery("tasks", broker="redis://localhost:6379/0")

REVIEW_SUBMITTED_JOKES_CHAT_ID = "-1002196165890"
REVIEW_SUBMITTED_JOKES_TOPIC_ID = 34

SUBMIT_JOKE_NOTIF_ADMIN_MESSAGE_TEMPLATE = """
جوک جدیدی از طرف {from_user} ارسال شده است.

{joke}
"""


async def notify_admin_submit_joke_async(joke, from_user):
    bot = new_bot()
    await bot.send_message(
        chat_id=REVIEW_SUBMITTED_JOKES_CHAT_ID,
        message_thread_id=REVIEW_SUBMITTED_JOKES_TOPIC_ID,
        text=SUBMIT_JOKE_NOTIF_ADMIN_MESSAGE_TEMPLATE.format(
            from_user=from_user, joke=joke
        ),
    )


@app.task
def notify_admin_submit_joke(joke, from_user):
    asyncio.run(notify_admin_submit_joke_async(joke, from_user))
