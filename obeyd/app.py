from functools import wraps
import logging
import os
import random
from typing import Optional, Tuple

import sentry_sdk
from sqlalchemy import Select, func, select
from sqlalchemy import update as _update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from obeyd.models import Joke, Like, SeenJoke, User, async_session

SCORES = {
    "1": {"emoji": "💩", "notif": "💩💩💩"},
    "2": {"emoji": "😐", "notif": "😐😐😐"},
    "3": {"emoji": "🙂", "notif": "🙂🙂🙂"},
    "4": {"emoji": "😁", "notif": "😁😁😁"},
    "5": {"emoji": "😂", "notif": "😂😂😂"},
}

SHOW_RANDOM_JOKE_PROB = 0.25

START_STATES_NAME = 1
SETNAME_STATES_NAME = 1
NEWJOKE_STATES_TEXT = 1

REVIEW_JOKES_CHAT_ID = "-4226479784"


def accepted_jokes() -> Select[Tuple[Joke]]:
    return select(Joke).filter(Joke.accepted.is_(True))


def filter_seen_jokes(
    filter: Select[Tuple[Joke]], by_user_id: int
) -> Select[Tuple[Joke]]:
    seen_jokes = (
        select(SeenJoke.joke_id).where(SeenJoke.user_id == by_user_id).subquery()
    )
    return filter.join(seen_jokes, Joke.id == seen_jokes.c.joke_id, isouter=True).where(
        seen_jokes.c.joke_id.is_(None)
    )


async def random_joke(
    session: AsyncSession, filter: Select[Tuple[Joke]]
) -> Optional[Joke]:
    return await session.scalar(filter.order_by(func.random()).limit(1))


async def most_rated_joke(
    session: AsyncSession, filter: Select[Tuple[Joke]]
) -> Optional[Joke]:
    jokes_scores = (
        select(Like.joke_id, func.avg(Like.score).label("avg_score"))
        .group_by(Like.joke_id)
        .subquery()
    )
    return await session.scalar(
        filter.join(
            jokes_scores,
            Joke.id == jokes_scores.c.joke_id,
            isouter=True,
        )
        .order_by(jokes_scores.c.avg_score)
        .limit(1)
    )


def not_authenticated(f):
    @wraps(f)
    async def g(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message
        assert update.effective_user

        async with async_session() as session:
            user = await session.scalar(
                select(User).where(User.user_id == update.effective_user.id)
            )

        if user is not None:
            await update.message.reply_text(
                f"من شما رو میشناسم. تو {user.nickname} هستی."
            )
            return

        return await f(update, context)

    return g


def authenticated(f):
    @wraps(f)
    async def g(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message
        assert update.effective_user

        async with async_session() as session:
            user = await session.scalar(
                select(User).where(User.user_id == update.effective_user.id)
            )

        if user is None:
            await update.message.reply_text("من شما رو میشناسم؟")
            return

        return await f(update, context, user=user)

    return g


@not_authenticated
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    await update.message.reply_text("سلام. اسمت رو بهم بگو!")

    return START_STATES_NAME


@not_authenticated
async def start_handler_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert update.effective_user

    async with async_session() as session:
        await session.execute(
            insert(User).values(
                user_id=update.effective_user.id, nickname=update.message.text
            )
        )
        await session.commit()

    await update.message.reply_text(f"سلام {update.message.text}!")

    return ConversationHandler.END


@authenticated
async def setname_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
):
    assert update.message

    await update.message.reply_text("اسمت رو بهم بگو.")

    return SETNAME_STATES_NAME


@authenticated
async def setname_handler_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
):
    assert update.message
    assert update.effective_user

    async with async_session() as session:
        await session.execute(
            _update(User)
            .where(User.user_id == update.effective_user.id)
            .values(nickname=update.message.text)
        )
        await session.commit()

    await update.message.reply_text(f"سلام {update.message.text}!")

    return ConversationHandler.END


@authenticated
async def getname_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
):
    assert update.message
    assert update.effective_user

    await update.message.reply_text(f"تو {user.nickname} هستی!")


@authenticated
async def getjoke_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
):
    assert update.message
    assert update.effective_user

    async with async_session() as session:
        filter = filter_seen_jokes(
            filter=accepted_jokes(), by_user_id=update.effective_user.id
        )

        if random.random() < SHOW_RANDOM_JOKE_PROB:
            joke = await random_joke(session, filter)
        else:
            joke = await most_rated_joke(session, filter)

        if not joke:
            await update.message.reply_text("جوکی ندارم که برات بگم :(")
            return

        await update.message.reply_text(
            f"""
{joke.text}

*{joke.creator_nickname}*
""",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=score_data["emoji"],
                            callback_data={
                                "joke_id": joke.id,
                                "score": int(score),
                            },
                        )
                        for score, score_data in SCORES.items()
                    ]
                ]
            ),
        )

        await session.execute(
            insert(SeenJoke)
            .values(user_id=update.effective_user.id, joke_id=joke.id)
            .on_conflict_do_nothing(constraint="seen_jokes_user_id_joke_id_key")
        )
        await session.commit()


@authenticated
async def newjoke_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
):
    assert update.message

    await update.message.reply_text("جوکت رو توی یک پیام برام بنویس :)")

    return NEWJOKE_STATES_TEXT


async def new_joke_callback_notify_admin(context: ContextTypes.DEFAULT_TYPE, **kwargs):
    joke_text = kwargs["joke_text"]
    joke_creator_nickname = kwargs["joke_creator_nickname"]

    await context.bot.send_message(
        chat_id=REVIEW_JOKES_CHAT_ID,
        text=f"جوک جدیدی ارسال شده است:\n{joke_text}\n*{joke_creator_nickname}*",
    )


@authenticated
async def newjoke_handler_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
):
    assert update.message
    assert update.effective_user
    assert context.job_queue

    async with async_session() as session:
        await session.execute(
            insert(Joke).values(
                text=update.message.text,
                creator_id=user.user_id,
                creator_nickname=user.nickname,
            )
        )
        await session.commit()

    context.job_queue.run_once(
        callback=new_joke_callback_notify_admin,
        when=0,
        job_kwargs={
            "joke_text": update.message.text,
            "joke_creator_nickname": user.nickname,
        },
    )

    await update.message.reply_text("دریافت شد!")

    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message

    if context.user_data is not None:
        context.user_data.clear()
    await update.message.reply_text("لغو شد.")

    return ConversationHandler.END


if __name__ == "__main__":
    sentry_sdk.init(
        dsn="https://843cb5c0e82dfa5f061f643a1422a9cf@sentry.hamravesh.com/6750",
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    app = ApplicationBuilder().token(os.environ["API_TOKEN"]).build()

    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("start", start_handler)],
            states={
                START_STATES_NAME: [MessageHandler(filters.TEXT, start_handler_name)]
            },
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("setname", setname_handler)],
            states={
                SETNAME_STATES_NAME: [
                    MessageHandler(filters.TEXT, setname_handler_name)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )
    app.add_handler(CommandHandler("getname", getname_handler))
    app.add_handler(CommandHandler("getjoke", getjoke_handler))
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("newjoke", newjoke_handler)],
            states={
                NEWJOKE_STATES_TEXT: [
                    MessageHandler(filters.TEXT, newjoke_handler_text)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
    )

    app.run_polling()
