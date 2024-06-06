from aiogram import Router, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from obeyd.jokes.callbacks import ReviewJokeCallback
from obeyd.jokes.states import NewJokeForm
from obeyd.likes.callbacks import LikeCallback
from obeyd.likes.enums import SCORES
from obeyd.middlewares import AuthenticateMiddleware, AuthorizeMiddleware
from obeyd.models import Joke, Like, SeenJoke, async_session
from obeyd.tasks import notify_admin_submit_joke

jokes_router = Router()
jokes_router.message.middleware(AuthenticateMiddleware())
jokes_router.message.middleware(AuthorizeMiddleware())
jokes_router.callback_query.middleware(AuthenticateMiddleware())
jokes_router.callback_query.middleware(AuthorizeMiddleware())


@jokes_router.message(Command("new_joke"))
async def new_joke_handler(message: Message) -> None:
    assert message.from_user

    async with async_session() as session:
        jokes_scores = (
            select(Like.joke_id, func.avg(Like.score).label("avg_score"))
            .group_by(Like.joke_id)
            .subquery()
        )
        seen_jokes = (
            select(SeenJoke.joke_id)
            .where(SeenJoke.user_id == message.from_user.id)
            .subquery()
        )
        joke = await session.scalar(
            select(Joke)
            .options(selectinload(Joke.creator))
            .filter(Joke.accepted.is_(True))
            .join(seen_jokes, Joke.id == seen_jokes.c.joke_id, isouter=True)
            .where(seen_jokes.c.joke_id.is_(None))
            .join(
                jokes_scores,
                Joke.id == jokes_scores.c.joke_id,
                isouter=True,
            )
            .order_by(jokes_scores.c.avg_score)
            .limit(1)
        )

        if not joke:
            await message.answer("جوکی ندارم که برات بگم :(")
            return

        await message.answer(
            f"""
{joke.text}

{html.bold(joke.creator.nickname)}
""",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=score_data["emoji"],
                            callback_data=LikeCallback(
                                joke_id=joke.id, score=int(score)
                            ).pack(),
                        )
                        for score, score_data in SCORES.items()
                    ]
                ]
            ),
        )

        await session.execute(
            insert(SeenJoke)
            .values(user_id=message.from_user.id, joke_id=joke.id)
            .on_conflict_do_nothing(constraint="seen_jokes_user_id_joke_id_key")
        )
        await session.commit()


@jokes_router.message(Command("submit_joke"))
async def submit_joke_start_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(NewJokeForm.joke)
    await message.answer("جوکت رو توی یک پیام برام بنویس")


@jokes_router.message(NewJokeForm.joke)
async def submit_joke_end_handler(message: Message, state: FSMContext) -> None:
    assert message.from_user

    data = await state.update_data(joke=message.text)
    await state.clear()

    async with async_session() as session:
        joke = Joke(
            text=data["joke"],
            creator_id=message.from_user.id,
        )
        session.add(joke)
        await session.commit()
        await session.refresh(joke)

    notify_admin_submit_joke.delay(joke.id, joke.text, message.from_user.full_name)

    await message.answer("😂😂😂")


@jokes_router.callback_query(ReviewJokeCallback.filter())
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
        else:
            await query.answer(text="دوباره تلاش کنید.")
        await session.commit()

    await query.answer(text="انجام شد.")
