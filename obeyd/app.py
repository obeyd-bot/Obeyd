import html
import json
import logging
import os
from datetime import datetime, time, timedelta, timezone
from functools import wraps
import traceback

import pytz
import sentry_sdk
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from obeyd.db import db

SCORES = {
    "1": {
        "emoji": "💩",
        "notif": "💩💩💩",
        "score_notif": "{s} با جوکت اصلا حال نکرد 💩💩💩",
    },
    "2": {
        "emoji": "😐",
        "notif": "😐😐😐",
        "score_notif": "{s} با جوکت حال نکرد 😐😐😐",
    },
    "3": {
        "emoji": "🙂",
        "notif": "🙂🙂🙂",
        "score_notif": "{s} فکر میکنه جوکت بد هم نبوده 🙂🙂🙂",
    },
    "4": {
        "emoji": "😁",
        "notif": "😁😁😁",
        "score_notif": "{s} با جوکت حال کرد 😁😁😁",
    },
    "5": {
        "emoji": "😂",
        "notif": "😂😂😂",
        "score_notif": "{s} با جوکت خیلی حال کرد 😂😂😂",
    },
}

RECURRING_INTERVALS = {
    "هر دقیقه": {
        "code": "minutely",
        "text": "هر دقیقه",
    },
    "هر ساعت": {
        "code": "hourly",
        "text": "هر ساعت",
    },
    "هر روز": {
        "code": "daily",
        "text": "هر روز ساعت ۶ عصر",
    },
}


SHOW_RANDOM_JOKE_PROB = 0.25

START_STATES_NAME = 1
SETNAME_STATES_NAME = 1
NEWJOKE_STATES_TEXT = 1
SETRECURRING_STATES_INTERVAL = 1

REVIEW_JOKES_CHAT_ID = os.environ["REVIEW_JOKES_CHAT_ID"]
ALERTS_CHAT_ID = os.environ["ALERTS_CHAT_ID"]


async def alert_admin(context: ContextTypes.DEFAULT_TYPE, msg: str):
    await context.bot.send_message(chat_id=ALERTS_CHAT_ID, text=msg)


def joke_msg(joke: dict):
    return {
        "text": f"{joke['text']}\n\n*{joke['creator_nickname']}*",
        "parse_mode": ParseMode.MARKDOWN_V2,
        "reply_markup": InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=score_data["emoji"],
                        callback_data=f"scorejoke:{str(joke['_id'])}:{score}",
                    )
                    for score, score_data in SCORES.items()
                ]
            ]
        ),
    }


def format_joke(joke: dict):
    return f"{joke['text']}\n\n*{joke['creator_nickname']}*"


def log_activity(kind):
    def g(f):
        @wraps(f)
        async def h(update: Update, context: ContextTypes.DEFAULT_TYPE, **kwargs):
            assert update.effective_user

            await db["activities"].insert_one(
                {
                    "kind": kind,
                    "user_id": update.effective_user.id,
                    "data": {},
                    "created_at": datetime.now(tz=timezone.utc),
                }
            )

            return await f(update, context, **kwargs)

        return h

    return g


def not_authenticated(f):
    @wraps(f)
    async def g(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_user

        user = await db["users"].find_one({"user_id": update.effective_user.id})

        if user is not None:
            if update.message:
                await update.message.reply_text(
                    f"{user['nickname']}! ما قبلا با هم آشنا شدیم! برای اینکه برات جوک بفرستم از دستور /joke استفاده کن.",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[[KeyboardButton(text="/joke")]],
                        one_time_keyboard=True,
                        resize_keyboard=True,
                    ),
                )
            return

        return await f(update, context)

    return g


def authenticated(f):
    @wraps(f)
    async def g(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_user

        user = await db["users"].find_one({"user_id": update.effective_user.id})

        if user is None:
            if update.message:
                await update.message.reply_text(
                    "قبل از هر چیز، از دستور /start استفاده کن تا با هم آشنا بشیم.",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[[KeyboardButton(text="/start")]],
                        one_time_keyboard=True,
                        resize_keyboard=True,
                    ),
                )
            return

        return await f(update, context, user=user)

    return g


@not_authenticated
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    await update.message.reply_text(
        "به به! خوش اومدی! من ایرجم. میتونی من رو توی هر چتی منشن کنی تا جوک بفرستم 😁 اسمت رو بهم میگی؟"
    )

    return START_STATES_NAME


@not_authenticated
async def start_handler_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert update.effective_user

    try:
        await db["users"].insert_one(
            {
                "user_id": update.effective_user.id,
                "nickname": update.message.text,
                "joined_at": datetime.now(tz=timezone.utc),
            }
        )
    except DuplicateKeyError:
        await update.message.reply_text(
            "این اسم رو قبلا یکی استفاده کرده. یک اسم دیگه برای خودت انتخاب کن."
        )
        return START_STATES_NAME

    await update.message.reply_text(
        f"سلام *{update.message.text}*! برای اینکه برات جوک بفرستم از دستور /joke استفاده کن.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/joke")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ConversationHandler.END


@authenticated
@log_activity("setname")
async def setname_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message

    await update.message.reply_text(
        "حواست باشه که اسمت قبلیت روی جوک هایی که تا الان نوشتی باقی میمونه. حالا اسمت رو بهم بگو.",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(text="/cancel")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return SETNAME_STATES_NAME


@authenticated
async def setname_handler_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert update.effective_user

    try:
        await db["users"].update_one(
            {"user_id": user["user_id"]}, {"$set": {"nickname": update.message.text}}
        )
    except DuplicateKeyError:
        await update.message.reply_text(
            "این اسم رو قبلا یکی استفاده کرده. یک اسم دیگه انتخاب کن."
        )
        return SETNAME_STATES_NAME

    await update.message.reply_text(
        f"سلام *{update.message.text}*! برای اینکه برات جوک بفرستم از دستور /joke استفاده کن.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/joke")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ConversationHandler.END


@authenticated
@log_activity("getname")
async def getname_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert update.effective_user

    await update.message.reply_text(
        f"*user['nickname']*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/joke")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )


async def random_joke():
    try:
        return (
            await db["jokes"]
            .aggregate([{"$match": {"accepted": True}}, {"$sample": {"size": 1}}])
            .next()
        )
    except StopAsyncIteration:
        return None


@authenticated
@log_activity("joke")
async def joke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict):
    assert update.message
    assert update.effective_user

    joke = await random_joke()

    if joke is None:
        await update.message.reply_text(
            "دیگه جوکی ندارم که بهت بگم 😁 میتونی به جاش تو یک جوک بهم بگی!",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/newjoke")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return

    await update.message.reply_text(**joke_msg(joke))

    return ConversationHandler.END


@authenticated
@log_activity("newjoke")
async def newjoke_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message

    await update.message.reply_text("بگو 😁")

    return NEWJOKE_STATES_TEXT


async def newjoke_callback_notify_admin(context: ContextTypes.DEFAULT_TYPE):
    assert context.job
    assert isinstance(context.job.data, dict)

    joke = context.job.data

    await context.bot.send_message(
        chat_id=REVIEW_JOKES_CHAT_ID,
        text=f"جوک جدیدی ارسال شده است:\n\n{format_joke(joke)}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="رد",
                        callback_data=f"reviewjoke:{joke['_id']}:reject",
                    ),
                    InlineKeyboardButton(
                        text="تایید",
                        callback_data=f"reviewjoke:{joke['_id']}:accept",
                    ),
                ]
            ]
        ),
    )


@authenticated
async def newjoke_handler_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert update.effective_user
    assert context.job_queue

    joke = {
        "text": update.message.text,
        "creator_id": user["user_id"],
        "creator_nickname": user["nickname"],
        "created_at": datetime.now(tz=timezone.utc),
    }
    await db["jokes"].insert_one(joke)

    context.job_queue.run_once(
        callback=newjoke_callback_notify_admin,
        when=0,
        data=joke,
    )

    await update.message.reply_text(
        "😂👍",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/joke"), KeyboardButton(text="/newjoke")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ConversationHandler.END


async def reviewjoke_callback_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.callback_query
    assert isinstance(update.callback_query.data, str)

    _, joke_id, action = tuple(update.callback_query.data.split(":"))
    accepted = None
    if action == "accept":
        accepted = True
    elif action == "reject":
        accepted = False
    else:
        raise Exception("expected accept or reject")

    await db["jokes"].update_one(
        {"_id": ObjectId(joke_id)}, {"$set": {"accepted": accepted}}
    )

    if accepted:
        await update.callback_query.answer("تایید شد")
    else:
        await update.callback_query.answer("رد شد")


@authenticated
@log_activity("scorejoke")
async def scorejoke_callback_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.effective_user
    assert update.callback_query
    assert isinstance(update.callback_query.data, str)

    _, joke_id, score = tuple(update.callback_query.data.split(":"))

    joke_score = {
        "user_id": user["user_id"],
        "joke_id": joke_id,
        "score": int(score),
        "created_at": datetime.now(tz=timezone.utc),
    }
    try:
        await db["scores"].insert_one(joke_score)
    except DuplicateKeyError:
        await update.callback_query.answer("قبلا به این جوک رای دادی")
        return

    await update.callback_query.answer(SCORES[score]["notif"])
    assert context.job_queue
    context.job_queue.run_once(
        callback=scorejoke_callback_notify_creator,
        when=0,
        data=joke_score,
    )


async def scorejoke_callback_notify_creator(context: ContextTypes.DEFAULT_TYPE):
    assert context.job
    assert isinstance(context.job.data, dict)

    joke_score = context.job.data

    joke = await db["jokes"].find_one({"_id": ObjectId(joke_score["joke_id"])})
    scored_by_user = await db["users"].find_one({"user_id": joke_score["user_id"]})
    assert joke
    assert scored_by_user

    await context.bot.send_message(
        chat_id=joke["creator_id"],
        text=SCORES[str(joke_score["score"])]["score_notif"].format(
            s=scored_by_user["nickname"]
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@log_activity("cancel")
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    if context.user_data is not None:
        context.user_data.clear()
    await update.message.reply_text(
        "حرفی نیست",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/joke")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ConversationHandler.END


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.inline_query

    joke = (
        await db["jokes"]
        .aggregate([{"$match": {"accepted": True}}, {"$sample": {"size": 1}}])
        .next()
    )
    assert joke is not None

    await update.inline_query.answer(
        results=[
            InlineQueryResultArticle(
                id="joke",
                title="جوک بگو!",
                input_message_content=InputTextMessageContent(
                    message_text=format_joke(joke), parse_mode=ParseMode.MARKDOWN_V2
                ),
            ),
            InlineQueryResultArticle(
                id="setrecurring",
                title="چند وقت یک بار جوک بگو!",
                input_message_content=InputTextMessageContent(
                    message_text="/setrecurring", parse_mode=ParseMode.MARKDOWN_V2
                ),
            ),
        ],
        cache_time=0,
    )


async def notify_inactive_users_callback(context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.now(tz=timezone.utc)

    inactive_users = db["activities"].aggregate(
        [
            {"$group": {"_id": "$user_id", "last_activity": {"$max": "$created_at"}}},
            {"$match": {"last_activity": {"$lt": current_time - timedelta(days=1)}}},
        ]
    )

    async for user in inactive_users:
        await context.bot.send_message(
            chat_id=user["_id"],
            text=f"یک جوک بگم؟",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/joke")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )


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

    assert job_queue
    current_jobs = job_queue.get_jobs_by_name(name=job_name)

    await db["recurrings"].delete_one({"chat_id": chat_id})
    for job in current_jobs:
        job.schedule_removal()

    await update.message.reply_text(text="باشه دیگه جوک نمیفرستم 😁")


async def setrecurring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    await update.message.reply_text(
        text="باشه 😁 چند وقت یک بار جوک بفرستم؟",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=interval)
                    for interval in RECURRING_INTERVALS.keys()
                ]
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
    interval = RECURRING_INTERVALS[update.message.text]

    recurring = {
        "chat_id": chat_id,
        "created_by_user_id": created_by_user_id,
        "interval": interval["code"],
        "created_at": datetime.now(),
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

    schedule_recurring(recurring)

    await update.message.reply_text(
        text=f"{interval['text']} همینجا جوک میفرستم 😁",
    )

    return ConversationHandler.END


def schedule_recurring(recurring: dict):
    assert job_queue

    job_name = f"recurring-{recurring['chat_id']}"

    current_jobs = job_queue.get_jobs_by_name(name=job_name)
    for job in current_jobs:
        job.schedule_removal()

    if recurring["interval"] == "daily":
        job_queue.run_daily(
            recurring_joke_callback,
            data=recurring,
            time=time(hour=18, tzinfo=pytz.timezone("Asia/Tehran")),
            name=job_name,
        )
    elif recurring["interval"] == "hourly":
        job_queue.run_repeating(
            recurring_joke_callback,
            data=recurring,
            interval=timedelta(hours=1),
            name=job_name,
        )
    elif recurring["interval"] == "minutely":
        job_queue.run_repeating(
            recurring_joke_callback,
            data=recurring,
            interval=timedelta(minutes=1),
            name=job_name,
        )


async def schedule_recurrings(context: ContextTypes.DEFAULT_TYPE):
    assert job_queue

    async for recurring in db["recurrings"].find():
        schedule_recurring(recurring)


async def recurring_joke_callback(context: ContextTypes.DEFAULT_TYPE):
    assert context.job

    recurring = context.job.data
    assert isinstance(recurring, dict)

    joke = await random_joke()
    assert joke is not None

    await context.bot.send_message(
        **joke_msg(joke),
        chat_id=recurring["chat_id"],
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    assert context.error

    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=ALERTS_CHAT_ID, text=message, parse_mode=ParseMode.HTML
    )


if __name__ == "__main__":
    sentry_sdk.init(
        dsn="https://843cb5c0e82dfa5f061f643a1422a9cf@sentry.hamravesh.com/6750",
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    app = (
        ApplicationBuilder()
        .read_timeout(30)
        .write_timeout(30)
        .token(os.environ["API_TOKEN"])
        .build()
    )
    job_queue = app.job_queue
    assert job_queue

    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("start", start_handler)],
            states={
                START_STATES_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, start_handler_name)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("setname", setname_handler)],
            states={
                SETNAME_STATES_NAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, setname_handler_name
                    )
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(CommandHandler("getname", getname_handler))
    app.add_handler(CommandHandler("joke", joke_handler))
    app.add_handler(CommandHandler("deleterecurring", deleterecurring_handler))
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("setrecurring", setrecurring_handler)],
            states={
                SETRECURRING_STATES_INTERVAL: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, setrecurring_handler_interval
                    )
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("newjoke", newjoke_handler)],
            states={
                NEWJOKE_STATES_TEXT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, newjoke_handler_text
                    )
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(
        CallbackQueryHandler(scorejoke_callback_query_handler, pattern="^scorejoke")
    )
    app.add_handler(
        CallbackQueryHandler(reviewjoke_callback_query_handler, pattern="^reviewjoke")
    )
    app.add_handler(InlineQueryHandler(inline_query_handler))

    app.add_error_handler(error_handler)

    # jobs
    job_queue.run_repeating(
        callback=notify_inactive_users_callback,
        interval=timedelta(hours=1).total_seconds(),
    )

    job_queue.run_once(schedule_recurrings, when=0)

    app.run_polling()
