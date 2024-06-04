import asyncio
import json
import logging
import os
import sys

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import func, select

from db import async_session
from models import Joke, Like

dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"سلام {html.bold(message.from_user.full_name)}!")


@dp.message(Command("joke"))
async def like_handler(message: Message) -> None:
    async with async_session() as session:
        result = await session.execute(select(Joke).order_by(func.random()))

    selected_joke = result.scalar()
    if not selected_joke:
        await message.answer("جوکی ندارم که برات بگم :(")
        return

    await message.answer(
        selected_joke.text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💩",
                        callback_data=json.dumps(
                            {"score": 1, "joke_id": selected_joke.id}
                        ),
                    ),
                    InlineKeyboardButton(
                        text="😐",
                        callback_data=json.dumps(
                            {"score": 2, "joke_id": selected_joke.id}
                        ),
                    ),
                    InlineKeyboardButton(
                        text="🙂",
                        callback_data=json.dumps(
                            {"score": 3, "joke_id": selected_joke.id}
                        ),
                    ),
                    InlineKeyboardButton(
                        text="😁",
                        callback_data=json.dumps(
                            {"score": 4, "joke_id": selected_joke.id}
                        ),
                    ),
                    InlineKeyboardButton(
                        text="😂",
                        callback_data=json.dumps(
                            {"score": 5, "joke_id": selected_joke.id}
                        ),
                    ),
                ]
            ]
        ),
    )


@dp.callback_query()
async def like_handler(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    data = json.loads(query.data)
    joke_id = data["joke_id"]
    score = data["score"]

    async with async_session() as session:
        like = Like(user_id=user_id, joke_id=joke_id, score=score)
        session.add(like)
        await session.commit()

    query.answer(text="دریافت شد")


async def main() -> None:
    bot = Bot(
        token=os.environ["API_TOKEN"],
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
