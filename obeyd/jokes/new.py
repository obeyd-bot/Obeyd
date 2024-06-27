from datetime import datetime, timezone
from uuid import uuid4

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler

from obeyd.config import FILES_BASE_DIR, REVIEW_JOKES_CHAT_ID
from obeyd.db import db
from obeyd.jokes.functions import send_joke
from obeyd.middlewares import authenticated, log_activity, user_has_nickname

NEWJOKE_STATES_JOKE = 1
NEWJOKE_STATES_JOKE_TEXT = 2


@authenticated
@user_has_nickname
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

    return NEWJOKE_STATES_JOKE


def jokereview_inline_keyboard_markup(joke: dict):
    return InlineKeyboardMarkup(
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
    )


async def newjoke_callback_notify_admin(context: ContextTypes.DEFAULT_TYPE):
    assert context.job
    assert isinstance(context.job.data, dict)

    joke = context.job.data

    await send_joke(
        joke=joke,
        user_id=None,
        chat_id=REVIEW_JOKES_CHAT_ID,
        chat_type=None,
        context=context,
        kwargs={"reply_markup": jokereview_inline_keyboard_markup(joke)},
    )


@authenticated
@user_has_nickname
async def newjoke_handler_joke_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert context.user_data
    assert context.job_queue

    joke = context.user_data.pop("joke")
    assert joke is not None
    joke["text"] = update.message.text

    await db["jokes"].insert_one(joke)

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

    context.job_queue.run_once(
        callback=newjoke_callback_notify_admin,
        when=0,
        data=joke,
    )

    return ConversationHandler.END


@authenticated
@user_has_nickname
async def newjoke_handler_joke(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict
):
    assert update.message
    assert update.effective_user
    assert context.job_queue

    joke = {
        "creator_id": user["user_id"],
        "creator_nickname": user["nickname"],
        "accepted": False,
        "visible": False,
        "created_at": datetime.now(tz=timezone.utc),
    }

    if update.message.voice is not None:
        file = await update.message.voice.get_file()
        file_id = str(uuid4())
        await file.download_to_drive(custom_path=f"{FILES_BASE_DIR}/{file_id}.bin")
        joke.update({"kind": "voice", "file_id": file_id})
        context.user_data["joke"] = joke  # type: ignore
        await update.message.reply_text(
            "😂👍 میتونی توضیح کوتاهی هم در مورد وویسی که فرستادی بدی",
            reply_markup=ReplyKeyboardRemove(),
        )
        return NEWJOKE_STATES_JOKE_TEXT
    elif update.message.video_note is not None:
        file = await update.message.video_note.get_file()
        file_id = str(uuid4())
        await file.download_to_drive(custom_path=f"{FILES_BASE_DIR}/{file_id}.bin")
        joke.update({"kind": "video_note", "file_id": file_id})
        context.user_data["joke"] = joke  # type: ignore
        await update.message.reply_text(
            "😂👍 میتونی توضیح کوتاهی هم در مورد ویدیو مسیجی که فرستادی بدی",
            reply_markup=ReplyKeyboardRemove(),
        )
        return NEWJOKE_STATES_JOKE_TEXT
    elif len(update.message.photo) > 0:
        file = await update.message.photo[-1].get_file()
        file_id = str(uuid4())
        await file.download_to_drive(custom_path=f"{FILES_BASE_DIR}/{file_id}.bin")
        joke.update({"kind": "photo", "file_id": file_id})
        context.user_data["joke"] = joke  # type: ignore
        await update.message.reply_text(
            "😂👍 میتونی توضیح کوتاهی هم در مورد عکسی که فرستادی بدی",
            reply_markup=ReplyKeyboardRemove(),
        )
        return NEWJOKE_STATES_JOKE_TEXT

    joke.update(
        {
            "kind": "text",
            "text": update.message.text,
        }
    )

    await db["jokes"].insert_one(joke)

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

    context.job_queue.run_once(
        callback=newjoke_callback_notify_admin,
        when=0,
        data=joke,
    )

    return ConversationHandler.END
