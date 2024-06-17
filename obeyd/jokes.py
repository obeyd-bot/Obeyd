from pathlib import Path
from typing import Optional

from bson import ObjectId
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from obeyd.config import SCORES, VOICES_BASE_DIR
from obeyd.db import db


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
