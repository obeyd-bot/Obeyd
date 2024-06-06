import asyncio
import json
import logging
import os
import sys

from aiogram import Bot, Dispatcher, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import expression

from models import Joke, Like, async_session
from tasks import notify_admin_submit_joke

storage = MemoryStorage()

dp = Dispatcher(storage=storage)

submit_joke_router = Router()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"سلام {html.bold(message.from_user.full_name)}!")


SCORES = {
    "1": {"emoji": "💩", "notif": "💩💩💩"},
    "2": {"emoji": "😐", "notif": "😐😐😐"},
    "3": {"emoji": "🙂", "notif": "🙂🙂🙂"},
    "4": {"emoji": "😁", "notif": "😁😁😁"},
    "5": {"emoji": "😂", "notif": "😂😂😂"},
}


@dp.message(Command("new_joke"))
async def new_joke_handler(message: Message) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Joke)
            .filter(Joke.accepted == expression.true())
            .order_by(func.random())
        )

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
                        text=score_data["emoji"],
                        callback_data=json.dumps(
                            {"score": int(score), "joke_id": selected_joke.id}
                        ),
                    )
                    for score, score_data in SCORES.items()
                ]
            ]
        ),
    )


class NewJokeForm(StatesGroup):
    joke = State()


@submit_joke_router.message(Command("submit_joke"))
async def submit_joke_start_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(NewJokeForm.joke)
    await message.answer(
        "جوکت رو توی یک پیام برام بنویس", reply_markup=ReplyKeyboardRemove()
    )


@dp.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("اشکالی نداره :)", reply_markup=ReplyKeyboardRemove())


@submit_joke_router.message(NewJokeForm.joke)
async def submit_joke_end_handler(message: Message, state: FSMContext) -> None:
    data = await state.update_data(joke=message.text)
    await state.clear()

    async with async_session() as session:
        joke = Joke(
            text=data["joke"],
            creator_user_id=message.from_user.id,
        )
        session.add(joke)
        await session.commit()

    notify_admin_submit_joke.delay(data["joke"], message.from_user.full_name)

    await message.answer("😂😂😂")


@dp.callback_query()
async def like_handler(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    data = json.loads(query.data)
    joke_id = data["joke_id"]
    score = data["score"]

    async with async_session() as session:
        await session.execute(
            insert(Like)
            .values(user_id=user_id, joke_id=joke_id, score=score)
            .on_conflict_do_update(
                constraint="user_id_joke_id_key", set_={"score": score}
            )
        )
        await session.commit()

    await query.answer(text=SCORES[str(score)]["notif"])


async def main() -> None:
    bot = Bot(
        token=os.environ["API_TOKEN"],
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp.include_router(submit_joke_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
