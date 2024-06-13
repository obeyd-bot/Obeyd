from functools import wraps
import logging
import os
import random
from typing import Optional, Tuple

import sentry_sdk
from sqlalchemy import Select, func, select
from sqlalchemy import update as _update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
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
        assert update.effective_user

        async with async_session() as session:
            user = await session.scalar(
                select(User).where(User.user_id == update.effective_user.id)
            )

        if user is not None:
            if update.message:
                await update.message.reply_text(
                    f"من شما رو میشناسم. تو {user.nickname} هستی."
                )
            return

        return await f(update, context)

    return g


def authenticated(f):
    @wraps(f)
    async def g(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_user

        async with async_session() as session:
            user = await session.scalar(
                select(User).where(User.user_id == update.effective_user.id)
            )

        if user is None:
            if update.message:
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
                            callback_data=f"scorejoke:{joke.id}:{score}",
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

    await update.message.reply_text("جوکت رو توی یک پیام برام بنویس")

    return NEWJOKE_STATES_TEXT


async def newjoke_callback_notify_admin(context: ContextTypes.DEFAULT_TYPE):
    assert context.job
    assert isinstance(context.job.data, dict)

    joke_id = context.job.data["joke_id"]
    joke_text = context.job.data["joke_text"]
    joke_creator_nickname = context.job.data["joke_creator_nickname"]

    await context.bot.send_message(
        chat_id=REVIEW_JOKES_CHAT_ID,
        text=f"جوک جدیدی ارسال شده است:\n\n{joke_text}\n\n*{joke_creator_nickname}*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="رد",
                        callback_data=f"reviewjoke:{joke_id}:reject",
                    ),
                    InlineKeyboardButton(
                        text="تایید",
                        callback_data=f"reviewjoke:{joke_id}:accept",
                    ),
                ]
            ]
        ),
    )


@authenticated
async def newjoke_handler_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
):
    assert update.message
    assert update.effective_user
    assert context.job_queue

    async with async_session() as session:
        joke = Joke(
            text=update.message.text,
            creator_id=user.user_id,
            creator_nickname=user.nickname,
        )
        session.add(joke)
        await session.commit()
        await session.refresh(joke)

    context.job_queue.run_once(
        callback=newjoke_callback_notify_admin,
        when=0,
        data={
            "joke_id": joke.id,
            "joke_text": joke.text,
            "joke_creator_nickname": joke.creator_nickname,
        },
    )

    await update.message.reply_text("دریافت شد!")

    return ConversationHandler.END


async def reviewjoke_callback_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.callback_query
    assert isinstance(update.callback_query.data, str)

    _, joke_id, action = tuple(update.callback_query.data.split(":"))
    accepted = None
    if action == "accept":
        accepted = True
    elif action == "reject":
        accepted = False
    else:
        raise Exception("expected accept or reject")

    async with async_session() as session:
        await session.execute(
            _update(Joke).where(Joke.id == int(joke_id)).values(accepted=accepted)
        )
        await session.commit()

    if accepted:
        await update.callback_query.answer("تایید شد")
    else:
        await update.callback_query.answer("رد شد")


@authenticated
async def scorejoke_callback_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
):
    assert update.effective_user
    assert update.callback_query
    assert isinstance(update.callback_query.data, str)

    _, joke_id, score = tuple(update.callback_query.data.split(":"))

    inserted = False
    async with async_session() as session:
        try:
            like = Like(
                user_id=update.effective_user.id, joke_id=int(joke_id), score=int(score)
            )
            session.add(like)
            await session.commit()
            inserted = True
        except IntegrityError:
            pass

    if not inserted:
        await update.callback_query.answer("شما قبلا یک بار رای داده اید")
    else:
        await update.callback_query.answer(SCORES[score]["notif"])
        assert context.job_queue
        context.job_queue.run_once(
            callback=scorejoke_callback_notify_creator,
            when=0,
            data={
                "scored_by_user_id": update.effective_user.id,
                "joke_id": int(joke_id),
                "score": int(score),
            },
        )


async def scorejoke_callback_notify_creator(context: ContextTypes.DEFAULT_TYPE):
    assert context.job
    assert isinstance(context.job.data, dict)

    scored_by_user_id = context.job.data["scored_by_user_id"]
    joke_id = context.job.data["joke_id"]
    score = context.job.data["score"]

    async with async_session() as session:
        scored_by_user = await session.scalar(
            select(User).where(User.user_id == scored_by_user_id)
        )
        assert scored_by_user is not None
        joke = await session.scalar(select(Joke).where(Joke.id == joke_id))
        assert joke is not None

    await context.bot.send_message(
        chat_id=REVIEW_JOKES_CHAT_ID,
        text=f"{scored_by_user.nickname} به جوک شما امتیاز {score} رو داد.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="رد",
                        callback_data=f"reviewjoke:{joke_id}:reject",
                    ),
                    InlineKeyboardButton(
                        text="تایید",
                        callback_data=f"reviewjoke:{joke_id}:accept",
                    ),
                ]
            ]
        ),
    )


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
    app.add_handler(
        CallbackQueryHandler(scorejoke_callback_query_handler, pattern="^scorejoke")
    )

    # admin
    app.add_handler(
        CallbackQueryHandler(reviewjoke_callback_query_handler, pattern="^reviewjoke")
    )

    app.run_polling()
