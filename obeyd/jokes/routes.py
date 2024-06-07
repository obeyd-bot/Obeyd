import random

from aiogram import Router, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReactionTypeEmoji,
)
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from obeyd.jokes.callbacks import ReviewJokeCallback
from obeyd.jokes.services import (
    accepted_jokes,
    filter_seen_jokes,
    most_rated_joke,
    random_joke,
)
from obeyd.jokes.states import NewJokeForm
from obeyd.likes.callbacks import LikeCallback
from obeyd.likes.enums import SCORES
from obeyd.middlewares import AuthenticateMiddleware, AuthorizeMiddleware
from obeyd.models import Joke, SeenJoke, async_session
from obeyd.tasks import notify_admin_submit_joke
from obeyd.users.services import find_user_by_id

jokes_router = Router()
jokes_router.message.middleware(AuthenticateMiddleware())
jokes_router.message.middleware(AuthorizeMiddleware())
jokes_router.callback_query.middleware(AuthenticateMiddleware())
jokes_router.callback_query.middleware(AuthorizeMiddleware())


SHOW_RANDOM_JOKE_PROB = 0.5


@jokes_router.message(Command("new_joke"))
async def new_joke_handler(message: Message) -> None:
    assert message.from_user

    async with async_session() as session:
        filter = filter_seen_jokes(
            filter=accepted_jokes(), by_user_id=message.from_user.id
        )

        if random.random() < SHOW_RANDOM_JOKE_PROB:
            joke = await random_joke(session, filter)
        else:
            joke = await most_rated_joke(session, filter)

        if not joke:
            await message.answer("جوکی ندارم که برات بگم :(")
            return

        await message.answer(
            f"""
{joke.text}

{html.bold(joke.creator_nickname)}
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
        user = await find_user_by_id(session, message.from_user.id)
        assert user is not None

        joke = Joke(
            text=data["joke"],
            creator_id=message.from_user.id,
            creator_nickname=user.nickname,
        )
        session.add(joke)
        await session.commit()
        await session.refresh(joke)

    notify_admin_submit_joke.delay(
        joke.id, joke.text, joke.creator_nickname, message.from_user.full_name
    )

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
            await query.message.react([ReactionTypeEmoji(emoji="👍")])  # type: ignore
            await query.answer(text="تایید شد.")
        elif callback_data.command == "reject":
            await session.execute(
                update(Joke)
                .where(Joke.id == callback_data.joke_id)
                .values(accepted=False)
            )
            await query.message.react([ReactionTypeEmoji(emoji="👎")])  # type: ignore
            await query.answer(text="رد شد.")
        else:
            await query.answer(text="مشکلی پیش آمده است.")
        await session.commit()
