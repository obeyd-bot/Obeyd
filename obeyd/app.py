import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import sentry_sdk
from bson import ObjectId
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
    Defaults,
    MessageHandler,
    filters,
)

from obeyd.config import SCORES, VOICES_BASE_DIR
from obeyd.db import db
from obeyd.jokes import most_rated_joke, send_joke, send_joke_to_user
from obeyd.middlewares import authenticated, log_activity
from obeyd.recurrings import (
    SETRECURRING_STATES_INTERVAL,
    deleterecurring_handler,
    schedule_recurrings,
    setrecurring_handler,
    setrecurring_handler_interval,
)
from obeyd.review import (
    newjoke_callback_notify_admin,
    reviewjoke_callback_query_handler,
)
from obeyd.scores import scorejoke_callback_query_handler
from obeyd.users import (
    SETNAME_STATES_NAME,
    START_STATES_NAME,
    start_handler,
    start_handler_name,
)

NEWJOKE_STATES_TEXT = 1


@log_activity("joke")
async def joke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert update.effective_user
    assert update.effective_chat

    joke = await most_rated_joke(not_viewed_by_user_id=update.effective_user.id)

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

    await db["joke_views"].insert_one(
        {
            "user_id": update.effective_user.id,
            "joke_id": str(joke["_id"]),
            "score": None,
            "viewed_at": datetime.now(tz=timezone.utc),
            "scored_at": None,
        }
    )

    chat_id = update.effective_chat.id
    await send_joke_to_user(joke, chat_id, context)

    return ConversationHandler.END


@authenticated
@log_activity("newjoke")
async def newjoke_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message

    await update.message.reply_text(
        text="بگو 😁",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/cancel")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return NEWJOKE_STATES_TEXT


@authenticated
async def newjoke_handler_joke(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert update.effective_user
    assert context.job_queue

    if update.message.voice is not None:
        file = await update.message.voice.get_file()
        file_id = str(uuid4())
        await file.download_to_drive(custom_path=f"{VOICES_BASE_DIR}/{file_id}.bin")
        joke = {"voice_file_id": file_id}
    else:
        joke = {"text": update.message.text}

    joke = {
        **joke,
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
            keyboard=[
                [KeyboardButton(text="/joke")],
                [KeyboardButton(text="/newjoke")],
            ],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ConversationHandler.END


@log_activity("cancel")
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    if context.user_data is not None:
        context.user_data.clear()
    await update.message.reply_text(
        "باشه 🙄 یه جوک بگم؟",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="/joke")],
                [KeyboardButton(text="/newjoke")],
            ],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ConversationHandler.END


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
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/joke")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )


if __name__ == "__main__":
    if os.environ.get("SENTRY_ENABLED", "False") == "True":
        sentry_sdk.init(
            dsn="https://843cb5c0e82dfa5f061f643a1422a9cf@sentry.hamravesh.com/6750",
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    defaults = Defaults(parse_mode=ParseMode.MARKDOWN_V2)

    app = (
        ApplicationBuilder()
        .read_timeout(30)
        .write_timeout(30)
        .token(os.environ["API_TOKEN"])
        .defaults(defaults)
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
            entry_points=[CommandHandler("setname", setname_handler)],  # type: ignore
            states={
                SETNAME_STATES_NAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, setname_handler_name  # type: ignore
                    )
                ]
            },  # type: ignore
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(CommandHandler("getname", getname_handler))  # type: ignore
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
            },  # type: ignore
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("newjoke", newjoke_handler)],  # type: ignore
            states={
                NEWJOKE_STATES_TEXT: [
                    MessageHandler(
                        (filters.TEXT | filters.VOICE) & ~filters.COMMAND, newjoke_handler_joke  # type: ignore
                    )
                ]
            },  # type: ignore
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(
        CallbackQueryHandler(scorejoke_callback_query_handler, pattern="^scorejoke")
    )
    app.add_handler(
        CallbackQueryHandler(reviewjoke_callback_query_handler, pattern="^reviewjoke")
    )

    # jobs
    job_queue.run_repeating(
        callback=notify_inactive_users_callback,
        interval=timedelta(hours=1).total_seconds(),
    )

    job_queue.run_once(schedule_recurrings, when=0)

    app.run_polling()
