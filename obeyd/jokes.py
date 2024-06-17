from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from bson import ObjectId
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler

from obeyd.config import SCORES, VOICES_BASE_DIR
from obeyd.db import db
from obeyd.middlewares import authenticated, log_activity
from obeyd.review import newjoke_callback_notify_admin


def format_text_joke(joke: dict):
    return f"{joke['text']}\n\n*{joke['creator_nickname']}*"


async def send_joke(
    joke: dict,
    chat_id: str | int,
    context: ContextTypes.DEFAULT_TYPE,
    kwargs: dict,
):
    if "text" in joke:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{format_text_joke(joke)}",
            **kwargs,
        )
    elif "voice_file_id" in joke:
        await context.bot.send_voice(
            chat_id=chat_id,
            voice=Path(f"{VOICES_BASE_DIR}/{joke['voice_file_id']}.bin"),
            caption=f"*{joke['creator_nickname']}*",
            **kwargs,
        )
    else:
        raise Exception("expected 'text' or 'voice_file_id' to be present in the joke")


def score_inline_keyboard_markup(joke: dict):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=score_data["emoji"],
                    callback_data=f"scorejoke:{str(joke['_id'])}:{score}",
                )
                for score, score_data in SCORES.items()
            ]
        ]
    )


async def send_joke_to_user(
    joke: dict, chat_id: str | int, context: ContextTypes.DEFAULT_TYPE
):
    common = {
        "reply_markup": score_inline_keyboard_markup(joke),
    }

    await send_joke(joke, chat_id, context, common)


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


async def random_joke():
    try:
        return (
            await db["jokes"]
            .aggregate([{"$match": {"accepted": True}}, {"$sample": {"size": 1}}])
            .next()
        )
    except StopAsyncIteration:
        return None


async def most_rated_joke(not_viewed_by_user_id: Optional[int]):
    views = (
        await db["joke_views"].find({"user_id": not_viewed_by_user_id}).to_list(None)
    )

    try:
        joke_id = (
            await db["jokes"]
            .aggregate(
                [
                    {
                        "$match": {
                            "accepted": True,
                            "_id": {
                                "$nin": [ObjectId(view["joke_id"]) for view in views]
                            },
                        }
                    },
                    {
                        "$lookup": {
                            "from": "joke_views",
                            "localField": "_id",
                            "foreignField": "joke_id",
                            "as": "views",
                        },
                    },
                    {"$unwind": {"path": "$views", "preserveNullAndEmptyArrays": True}},
                    {"$set": {"views.score": {"$ifNull": ["$views.score", 3]}}},
                    {"$group": {"_id": "$_id", "avg_score": {"$avg": "$views.score"}}},
                    {"$sort": {"avg_score": -1}},
                ]
            )
            .next()
        )["_id"]
        return await db["jokes"].find_one({"_id": joke_id})
    except StopAsyncIteration:
        return None
