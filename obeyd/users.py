from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from obeyd.activities import log_activity_custom
from obeyd.db import db
from obeyd.middlewares import authenticated, log_activity, not_authenticated

START_STATES_NAME = 1
SETNAME_STATES_NAME = 1


class InvalidNicknameError(Exception):
    def __init__(self, nickname: str, reason: str):
        self.nickname = nickname
        self.reason = reason


def validate_nickname(nickname: str):
    nickname = nickname.strip()
    if len(nickname) == 0:
        raise InvalidNicknameError(nickname, "اسمت نمیتونه خالی باشه")
    if len(nickname) > 20:
        raise InvalidNicknameError(
            nickname, "طول اسمت نمیتونه بیشتر از ۲۰ کاراکتر باشه"
        )


@not_authenticated
@log_activity("start")
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    await update.message.reply_text(
        "به به خوش اومدی 😀 میتونی من رو توی هر چتی منشن کنی تا جوک بفرستم 😁 اسمت رو بهم میگی؟",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/cancel")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return START_STATES_NAME


@not_authenticated
async def start_handler_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert update.message.text
    assert update.effective_user

    chosen_nickname = update.message.text

    try:
        chosen_nickname = validate_nickname(chosen_nickname)
    except InvalidNicknameError as e:
        await update.message.reply_text(
            text=e.reason,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/cancel")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return START_STATES_NAME

    try:
        await db["users"].insert_one(
            {
                "user_id": update.effective_user.id,
                "user_name": update.effective_user.username,
                "user_fullname": update.effective_user.full_name,
                "nickname": chosen_nickname,
                "joined_at": datetime.now(tz=timezone.utc),
            }
        )
    except DuplicateKeyError:
        await log_activity_custom(
            update, "duplicate_nickname", {"nickname": chosen_nickname}
        )
        await update.message.reply_text(
            text="این اسم رو قبلا یکی استفاده کرده 🙁 یک اسم دیگه انتخاب کن",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/cancel")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return START_STATES_NAME

    await update.message.reply_text(
        f"سلام <b>{chosen_nickname}</b> 🫡 برای اینکه برات جوک بفرستم از دستور /joke استفاده کن 🙂",
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
        "بگو 😁",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/cancel")]],
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
    assert update.message.text
    assert update.effective_user

    chosen_nickname = update.message.text

    try:
        chosen_nickname = validate_nickname(chosen_nickname)
    except InvalidNicknameError as e:
        await update.message.reply_text(
            text=e.reason,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/cancel")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return SETNAME_STATES_NAME

    try:
        await db["users"].update_one(
            {"user_id": user["user_id"]}, {"$set": {"nickname": chosen_nickname}}
        )
    except DuplicateKeyError:
        await update.message.reply_text(
            text="این اسم رو قبلا یکی استفاده کرده 🙁 یک اسم دیگه انتخاب کن",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/cancel")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return SETNAME_STATES_NAME

    await update.message.reply_text(
        f"سلام <b>{chosen_nickname}</b> 🫡 برای اینکه برات جوک بفرستم از دستور /joke استفاده کن 🙂",
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
        f"<b>{user['nickname']}</b>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/joke")]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
