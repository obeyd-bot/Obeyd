from datetime import datetime, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from obeyd.config import FILES_BASE_DIR, SCORES
from obeyd.db import db
from obeyd.jokes.thompson import thompson_sampled_joke


def format_text_joke(joke: dict):
    return f"{joke['text']}\n\n<b>{joke['creator_nickname']}</b>"


async def send_joke(
    joke: dict,
    user_id: str | int | None,
    chat_id: str | int,
    context: ContextTypes.DEFAULT_TYPE,
    kwargs: dict,
):
    if joke["kind"] == "text":
        await context.bot.send_message(
            chat_id=chat_id,
            text=format_text_joke(joke),
            **kwargs,
        )
    elif joke["kind"] == "voice":
        await context.bot.send_voice(
            chat_id=chat_id,
            voice=Path(f"{FILES_BASE_DIR}/{joke['file_id']}.bin"),
            caption=format_text_joke(joke),
            **kwargs,
        )
    elif joke["kind"] == "video_note":
        await context.bot.send_video_note(
            chat_id=chat_id,
            video_note=Path(f"{FILES_BASE_DIR}/{joke['file_id']}.bin"),
            **kwargs,
        )
    elif joke["kind"] == "photo":
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=Path(f"{FILES_BASE_DIR}/{joke['file_id']}.bin"),
            caption=format_text_joke(joke),
            **kwargs,
        )
    else:
        raise Exception(
            "expected 'kind' to be one of 'text' or 'voice' or 'video_note' or 'photo'"
        )

    if user_id is not None:
        await db["joke_views"].insert_one(
            {
                "user_id": user_id,
                "joke_id": joke["_id"],
                "score": None,
                "viewed_at": datetime.now(tz=timezone.utc),
                "scored_at": None,
            }
        )

    await db["joke_views_chat"].insert_one(
        {
            "chat_id": chat_id,
            "joke_id": joke["_id"],
            "viewed_at": datetime.now(tz=timezone.utc),
        }
    )


def scorejoke_inline_keyboard_markup(joke: dict):
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


async def select_joke_for(
    chat_type: str | None = None,
    chat_id: str | int | None = None,
    user_id: int | None = None,
) -> dict | None:
    exclude_jokes = []

    if (chat_type is None and chat_id is not None) or (
        chat_type is not None and chat_id is None
    ):
        raise Exception(
            "expected 'chat_type' and 'chat_id' to be both not None or both None"
        )

    if chat_type == "private":
        assert user_id is not None
        views = await db["joke_views"].find({"user_id": user_id}).to_list(None)
        exclude_jokes += [view["joke_id"] for view in views]
    elif chat_type in ["group", "supergroup"]:
        assert user_id is not None
        assert chat_id is not None
        views = await db["joke_views_chat"].find({"chat_id": chat_id}).to_list(None)
        exclude_jokes += [view["joke_id"] for view in views]
    else:
        raise Exception(
            "expected 'chat_type' to be one of 'private', 'group','supergroup'"
        )

    return await thompson_sampled_joke(exclude_jokes=exclude_jokes)
