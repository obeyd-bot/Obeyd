from datetime import datetime

import pytz
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from obeyd.config import REVIEW_JOKES_CHAT_ID
from obeyd.db import db
from obeyd.middlewares import authenticated, log_activity

FEEDBACK_STATES_FEEDBACK = 1


@log_activity("feedback")
async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def feedback_handler_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert update.message.text
    assert update.effective_user
    assert context.job_queue

    feedback = {
        "user_id": update.effective_user.id,
        "timestamp": datetime.now(tz=pytz.utc),
        "feedback": update.message.text,
    }

    await db["feedbacks"].insert_one(feedback)

    await update.message.reply_text(
        "ممنونم از فیدبکت 😉 به زودی اعضای تیم عبید فیدبکت رو میخونن و اگر لازم باشه بهت پیام میدن."
    )

    # notify admin on new feedbacks
    context.job_queue.run_once(feedback_notify_admin, when=0, data=feedback)

    return ConversationHandler.END


async def feedback_notify_admin(context: ContextTypes.DEFAULT_TYPE):
    assert context.job
    assert isinstance(context.job.data, dict)

    feedback = context.job.data

    user = await db["users"].find_one({"user_id": feedback["user_id"]})

    if user is not None:
        text = f"فیدبک جدیدی از طرف <b>{user['nickname']}</b> دریافت شد:\n\n{feedback['feedback']}"
    else:
        text = f"فیدبک جدیدی دریافت شد:\n\n{feedback['feedback']}"

    await context.bot.send_message(
        chat_id=REVIEW_JOKES_CHAT_ID,
        text=text,
    )
