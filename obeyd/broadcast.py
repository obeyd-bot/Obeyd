from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from obeyd.db import db
from obeyd.middlewares import admin_only

BROADCAST_TEXT = 1
BROADCAST_CONFIRM = 2


@admin_only
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    await update.message.reply_text(
        text="متنی که میخوای برای همه ارسال بشه رو توی یک پیام بنویس",
    )

    return BROADCAST_TEXT


@admin_only
async def broadcast_handler_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    context.user_data["broadcast"] = {"text": update.message.text}  # type: ignore

    await update.message.reply_text(
        "مطمئنی؟",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[["بله", "نه"]], resize_keyboard=True, one_time_keyboard=True
        ),
    )

    return BROADCAST_CONFIRM


@admin_only
async def broadcast_handler_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert context.user_data
    assert context.job_queue

    if update.message.text == "نه":
        await update.message.reply_text("باشه")
        return ConversationHandler.END

    text = context.user_data["broadcast"]["text"]

    context.job_queue.run_once(
        broadcast_to_all,
        when=0,
        data={
            "text": text,
        },
    )

    return ConversationHandler.END


async def broadcast_to_all(context: ContextTypes.DEFAULT_TYPE):
    assert context.job
    assert isinstance(context.job.data, dict)

    text = context.job.data["text"]

    users = db["users"].find({})

    async for user in users:
        await context.bot.send_message(
            chat_id=user["user_id"],
            text=text,
        )
