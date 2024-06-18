from datetime import datetime, time, timedelta, timezone

import pytz
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from obeyd.config import RECURRING_INTERVALS
from obeyd.db import db
from obeyd.jokes import random_joke, send_joke_to_chat, thompson_sampled_joke
from obeyd.middlewares import log_activity

SETRECURRING_STATES_INTERVAL = 1


@log_activity("setrecurring")
async def setrecurring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    await update.message.reply_text(
        text="باشه 😁 چند وقت یک بار جوک بفرستم؟",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=interval)
                    for interval in RECURRING_INTERVALS.keys()
                ],
                [KeyboardButton(text="/cancel")],
            ],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return SETRECURRING_STATES_INTERVAL


async def setrecurring_handler_interval(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.message
    assert update.message.text
    assert update.effective_chat
    assert update.effective_user

    chat_id = update.effective_chat.id
    created_by_user_id = update.effective_user.id
    interval = RECURRING_INTERVALS.get(update.message.text.strip())

    if interval is None:
        await update.message.reply_text(
            "هان؟ متوجه نشدم 🤔",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/cancel")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return SETRECURRING_STATES_INTERVAL

    recurring = {
        "chat_id": chat_id,
        "created_by_user_id": created_by_user_id,
        "interval": interval["code"],
        "created_at": datetime.now(tz=timezone.utc),
    }
    await db["recurrings"].update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "created_by_user_id": recurring["created_by_user_id"],
                "interval": recurring["interval"],
            },
            "$setOnInsert": {
                "created_at": recurring["created_at"],
            },
        },
        upsert=True,
    )

    schedule_recurring(recurring, context)

    await update.message.reply_text(
        text=f"{interval['text']} همینجا جوک میفرستم 😁",
    )

    return ConversationHandler.END


@log_activity("deleterecurring")
async def deleterecurring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert update.effective_chat

    chat_id = update.effective_chat.id

    recurring = await db["recurrings"].find_one({"chat_id": chat_id})
    if recurring is None:
        await update.message.reply_text(
            "اصلا قرار نبود جوکی رو هر چند وقت یک بار بفرستم اینجا 🫤"
        )
        return

    job_name = f"recurring-{recurring['chat_id']}"

    assert context.job_queue
    current_jobs = context.job_queue.get_jobs_by_name(name=job_name)

    await db["recurrings"].delete_one({"chat_id": chat_id})
    for job in current_jobs:
        job.schedule_removal()

    await update.message.reply_text(text="باشه دیگه جوک نمیفرستم 😁")


def schedule_recurring(recurring: dict, context: ContextTypes.DEFAULT_TYPE):
    assert context.job_queue

    job_name = f"recurring-{recurring['chat_id']}"

    current_jobs = context.job_queue.get_jobs_by_name(name=job_name)
    for job in current_jobs:
        job.schedule_removal()

    if recurring["interval"] == "daily":
        context.job_queue.run_daily(
            recurring_joke_callback,
            data=recurring,
            time=time(hour=20, tzinfo=pytz.timezone("Asia/Tehran")),
            name=job_name,
        )
    elif recurring["interval"] == "weekly":
        context.job_queue.run_daily(
            recurring_joke_callback,
            data=recurring,
            time=time(hour=20, tzinfo=pytz.timezone("Asia/Tehran")),
            days=(4,),
            name=job_name,
        )
    elif recurring["interval"] == "minutely":
        context.job_queue.run_repeating(
            recurring_joke_callback,
            data=recurring,
            interval=timedelta(minutes=1),
            name=job_name,
        )


async def schedule_recurrings(context: ContextTypes.DEFAULT_TYPE):
    async for recurring in db["recurrings"].find():
        schedule_recurring(recurring, context)


async def recurring_joke_callback(context: ContextTypes.DEFAULT_TYPE):
    assert context.job

    recurring = context.job.data
    assert isinstance(recurring, dict)

    joke = await thompson_sampled_joke(for_user_id=None)
    assert joke is not None

    await send_joke_to_chat(joke, recurring["chat_id"], context)
