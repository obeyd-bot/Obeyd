import logging
import os

import sentry_sdk
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    Defaults,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from obeyd.broadcast import (
    BROADCAST_CONFIRM,
    BROADCAST_TEXT,
    broadcast_handler,
    broadcast_handler_confirm,
    broadcast_handler_text,
)
from obeyd.jokes import (
    NEWJOKE_STATES_JOKE,
    NEWJOKE_STATES_JOKE_TEXT,
    inline_query_handler,
    joke_handler,
    newjoke_handler,
    newjoke_handler_joke,
    newjoke_handler_joke_text,
    reviewjoke_callback_query_handler,
)
from obeyd.middlewares import log_activity
from obeyd.recurrings import (
    SETRECURRING_STATES_INTERVAL,
    deleterecurring_handler,
    schedule_recurrings,
    setrecurring_handler,
    setrecurring_handler_interval,
)
from obeyd.scores import scorejoke_callback_query_handler
from obeyd.users import (
    SETNAME_STATES_NAME,
    START_STATES_NAME,
    getname_handler,
    setname_handler,
    setname_handler_name,
    start_handler,
    start_handler_name,
)


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
            ],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ConversationHandler.END


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

    defaults = Defaults(parse_mode=ParseMode.HTML)

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
    app.add_handler(CommandHandler("joke", joke_handler))  # type: ignore
    app.add_handler(
        CallbackQueryHandler(scorejoke_callback_query_handler, pattern="^scorejoke")
    )
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
    app.add_handler(CommandHandler("deleterecurring", deleterecurring_handler))
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("newjoke", newjoke_handler)],  # type: ignore
            states={
                NEWJOKE_STATES_JOKE: [
                    MessageHandler(
                        (filters.TEXT | filters.VOICE | filters.VIDEO_NOTE | filters.PHOTO) & ~filters.COMMAND, newjoke_handler_joke  # type: ignore
                    )
                ],
                NEWJOKE_STATES_JOKE_TEXT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, newjoke_handler_joke_text  # type: ignore
                    )
                ],
            },  # type: ignore
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(InlineQueryHandler(inline_query_handler))  # type: ignore

    # admin handlers
    app.add_handler(
        CallbackQueryHandler(reviewjoke_callback_query_handler, pattern="^reviewjoke")
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("broadcast", broadcast_handler)],
            states={
                BROADCAST_TEXT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, broadcast_handler_text
                    )
                ],
                BROADCAST_CONFIRM: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, broadcast_handler_confirm
                    )
                ],
            },  # type: ignore
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )

    job_queue.run_once(schedule_recurrings, when=0)

    app.run_polling()
