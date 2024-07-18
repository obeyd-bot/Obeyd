from datetime import datetime

import pytz
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from obeyd.db import db
from obeyd.middlewares import authenticated, log_activity

FEEDBACK_STATES_FEEDBACK = 1


@authenticated
@log_activity("feedback")
async def feedback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message

    await update.message.reply_text(
        "ممنون از اینکه داری وقت میذاری تا بهمون فیدبک بدی. فیدبکت رو توی یک پیام برامون بنویس.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/cancel")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return FEEDBACK_STATES_FEEDBACK


@authenticated
async def feedback_handler_feedback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert update.message.text
    assert update.effective_user

    user_id = update.effective_user.id
    msg = update.message.text

    await db["feedbacks"].insert_one(
        {
            "user_id": user_id,
            "nickname": user["nickname"],
            "timestamp": datetime.now(tz=pytz.utc),
            "feedback": msg,
        }
    )

    await update.message.reply_text(
        "ممنونم از فیدبکت 😉 به زودی اعضای تیم عبید فیدبکت رو میخونن و اگر لازم باشه بهت پیام میدن."
    )

    return ConversationHandler.END
