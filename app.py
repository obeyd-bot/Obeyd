import asyncio
import logging
import sys

from aiogram import Dispatcher, Router, html
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
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import expression

from callbacks import LikeCallback, ReviewJokeCallback
from models import Joke, Like, async_session
from tasks import notify_admin_submit_joke, notify_creator_like_joke
from telegram import new_bot

storage = MemoryStorage()

dp = Dispatcher(storage=storage)

submit_joke_router = Router()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    assert message.from_user
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
                        callback_data=LikeCallback(
                            joke_id=selected_joke.id, score=int(score)
                        ).pack(),
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
    assert message.from_user

    data = await state.update_data(joke=message.text)
    await state.clear()

    async with async_session() as session:
        joke = Joke(
            text=data["joke"],
            creator_user_id=message.from_user.id,
        )
        session.add(joke)
        await session.commit()
        await session.refresh(joke)

    notify_admin_submit_joke.delay(joke.id, joke.text, message.from_user.full_name)

    await message.answer("😂😂😂")


@dp.callback_query(LikeCallback.filter())
async def like_callback_handler(
    query: CallbackQuery, callback_data: LikeCallback
) -> None:
    async with async_session() as session:
        await session.execute(
            insert(Like)
            .values(
                user_id=query.from_user.id,
                joke_id=callback_data.joke_id,
                score=callback_data.score,
            )
            .on_conflict_do_update(
                constraint="user_id_joke_id_key", set_={"score": callback_data.score}
            )
        )
        await session.commit()

    notify_creator_like_joke.delay(joke_id, callback_data.score)

    await query.answer(text=SCORES[str(callback_data.score)]["notif"])


@dp.callback_query(ReviewJokeCallback.filter())
async def review_joke_callback_handler(
    query: CallbackQuery, callback_data: ReviewJokeCallback
):
    # TODO: check if the callback is sent from admin users

    async with async_session() as session:
        if callback_data.command == "accept":
            await session.execute(
                update(Joke)
                .where(Joke.id == callback_data.joke_id)
                .values(accepted=True)
            )
        elif callback_data.command == "reject":
            await session.execute(
                update(Joke)
                .where(Joke.id == callback_data.joke_id)
                .values(accepted=False)
            )
        elif callback_data.command == "delete":
            await session.execute(delete(Joke).where(Joke.id == callback_data.joke_id))
        else:
            await query.answer(text="دوباره تلاش کنید.")
        await session.commit()

    await query.answer(text="انجام شد.")


async def main() -> None:
    bot = new_bot()

    dp.include_router(submit_joke_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
