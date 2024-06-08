from aiogram import html
from aiogram.methods import SendMessage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from obeyd.jokes.callbacks import ReviewJokeCallback

REVIEW_SUBMITTED_JOKES_CHAT_ID = "-4226479784"


async def notify_admin_submit_joke(
    joke_id, joke_text, joke_creator_nickname, from_user
):
    await SendMessage(
        chat_id=REVIEW_SUBMITTED_JOKES_CHAT_ID,
        text=f"""
جوک جدیدی از طرف {from_user} ارسال شده است:

{joke_text}

{html.bold(joke_creator_nickname)}
""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="رد",
                        callback_data=ReviewJokeCallback(
                            joke_id=joke_id, command="reject"
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="تایید",
                        callback_data=ReviewJokeCallback(
                            joke_id=joke_id, command="accept"
                        ).pack(),
                    ),
                ]
            ]
        ),
    )
