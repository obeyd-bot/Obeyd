from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from obeyd.likes.callbacks import LikeCallback
from obeyd.likes.enums import SCORES
from obeyd.middlewares import AuthenticateMiddleware, AuthorizeMiddleware
from obeyd.models import Like, async_session
from obeyd.tasks import notify_creator_like_joke

likes_router = Router()
likes_router.message.middleware(AuthenticateMiddleware())
likes_router.message.middleware(AuthorizeMiddleware())
likes_router.callback_query.middleware(AuthenticateMiddleware())
likes_router.callback_query.middleware(AuthorizeMiddleware())


@likes_router.callback_query(LikeCallback.filter())
async def like_callback_handler(
    query: CallbackQuery, callback_data: LikeCallback
) -> None:
    async with async_session() as session:
        try:
            await session.execute(
                insert(Like).values(
                    user_id=query.from_user.id,
                    joke_id=callback_data.joke_id,
                    score=callback_data.score,
                )
            )
            await session.commit()
        except IntegrityError:
            await query.answer(text="قبلا به این جوک رای دادی!")
            return

    notify_creator_like_joke.delay(callback_data.joke_id, callback_data.score)

    await query.answer(text=SCORES[str(callback_data.score)]["notif"])
