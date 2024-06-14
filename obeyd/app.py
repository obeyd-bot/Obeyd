import logging
import os
from datetime import datetime, timedelta
from functools import wraps

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import sentry_sdk
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

SHOW_RANDOM_JOKE_PROB = 0.25

START_STATES_NAME = 1
SETNAME_STATES_NAME = 1
NEWJOKE_STATES_TEXT = 1

REVIEW_JOKES_CHAT_ID = os.environ["REVIEW_JOKES_CHAT_ID"]
ALERTS_CHAT_ID = os.environ["ALERTS_CHAT_ID"]


async def alert_admin(context: ContextTypes.DEFAULT_TYPE, msg: str):
    await context.bot.send_message(chat_id=ALERTS_CHAT_ID, text=msg)


def format_joke(joke: dict):
    return f"{joke['text']}\n\n*{joke['creator_nickname']}*"


def log_activity(kind):
    def g(f):
        @wraps(f)
        async def h(update: Update, context: ContextTypes.DEFAULT_TYPE, **kwargs):
            assert update.effective_user

            await db["activities"].insert_one(
                {"kind": kind, "user_id": update.effective_user.id, "data": {}}
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
                    f"من شما رو میشناسم. تو {user['nickname']} هستی."
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
                await update.message.reply_text("من شما رو میشناسم؟")
            return

        return await f(update, context, user=user)

    return g


@not_authenticated
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    await update.message.reply_text("سلام. اسمت رو بهم بگو!")

    return START_STATES_NAME


@not_authenticated
async def start_handler_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert update.effective_user

    await db["users"].insert_one(
        {
            "user_id": update.effective_user.id,
            "nickname": update.message.text,
        }
    )

    await update.message.reply_text(f"سلام {update.message.text}!")

    return ConversationHandler.END


@authenticated
@log_activity("setname")
async def setname_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message

    await update.message.reply_text("اسمت رو بهم بگو.")

    return SETNAME_STATES_NAME


@authenticated
async def setname_handler_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert update.effective_user

    await db["users"].update_one(
        {"user_id": user["user_id"]}, {"$set": {"nickname": update.message.text}}
    )

    await update.message.reply_text(f"سلام {update.message.text}!")

    return ConversationHandler.END


@authenticated
@log_activity("getname")
async def getname_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert update.effective_user

    await update.message.reply_text(f"تو {user['nickname']} هستی!")


@authenticated
@log_activity("joke")
async def joke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict):
    assert update.message
    assert update.effective_user

    joke = (
        await db["jokes"]
        .aggregate([{"$match": {"accepted": True}}, {"$sample": {"size": 1}}])
        .next()
    )

    if not joke:
        await update.message.reply_text("جوکی ندارم که برات بگم :(")
        return

    await update.message.reply_text(
        f"{joke['text']}\n\n*{joke['creator_nickname']}*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=score_data["emoji"],
                        callback_data=f"scorejoke:{joke['_id']}:{score}",
                    )
                    for score, score_data in SCORES.items()
                ]
            ]
        ),
    )


@authenticated
@log_activity("newjoke")
async def newjoke_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message

    await update.message.reply_text("جوکت رو توی یک پیام برام بنویس")

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
    }
    await db["jokes"].insert_one(joke)

    context.job_queue.run_once(
        callback=newjoke_callback_notify_admin,
        when=0,
        data=joke,
    )

    await update.message.reply_text("دریافت شد!")

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

    joke_score = {"user_id": user["_id"], "joke_id": joke_id, "score": int(score)}
    await db["scores"].insert_one(joke_score)

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

    joke = await db["jokes"].find_one({"_id": joke_score["joke_id"]})
    scored_by_user = await db["users"].find_one({"_id": joke_score["user_id"]})
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
    await update.message.reply_text("لغو شد.")

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
            )
        ],
        cache_time=0,
    )


async def notify_inactive_users_callback(context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.now()

    inactive_users = db["activities"].aggregate(
        [
            {"$group": {"_id": "$user_id", "last_activity": {"$max": "$created_at"}}},
            {"$match": {"last_activity": {"$lt": current_time - timedelta(days=1)}}},
        ]
    )

    async for user in inactive_users:
        await context.bot.send_message(
            chat_id=user["_id"],
            text=f"یه جوک بگم؟",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/joke")]], one_time_keyboard=True
            ),
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

    app = ApplicationBuilder().token(os.environ["API_TOKEN"]).build()
    job_queue = app.job_queue
    assert job_queue

    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = client[os.environ["MONGODB_DB"]]

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

    # jobs
    job_queue.run_repeating(
        callback=notify_inactive_users_callback,
        interval=timedelta(hours=1).total_seconds(),
    )

    app.run_polling()
