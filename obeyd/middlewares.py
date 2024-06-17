from datetime import datetime, timezone
from functools import wraps

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from obeyd.db import db


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
