from functools import wraps
from typing import Any, Optional

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from obeyd.activities import log_activity_custom
from obeyd.db import db


def log_activity(kind, data: Optional[dict[str, Any]] = None):
    def g(f):
        @wraps(f)
        async def h(update: Update, context: ContextTypes.DEFAULT_TYPE, **kwargs):
            await log_activity_custom(update, kind, data)
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
                    f"ما قبلا با هم آشنا شدیم {user['nickname']} 😉 برای اینکه برات جوک بفرستم از دستور /joke استفاده کن",
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
                    "قبل از هر چیز از دستور /start استفاده کن تا با هم آشنا بشیم 😉",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[[KeyboardButton(text="/start")]],
                        one_time_keyboard=True,
                        resize_keyboard=True,
                    ),
                )
            return

        return await f(update, context, user=user)

    return g
