from typing import Any, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from obeyd.models import async_session
from obeyd.users.services import find_user_by_id


class AuthenticateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: Dict[str, Any]):
        if event.from_user is None:
            return await handler(event, data)

        async with async_session() as session:
            data["user"] = await find_user_by_id(session, event.from_user.id)
            return await handler(event, data)


class AuthorizeMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: Dict[str, Any]):
        if "user" not in data or data["user"] is None:
            await event.answer(
                "قبل از اینکه بتونم جوابت رو بدم، باید اسمت رو بهم بگی. برای این کار از دستور /start استفاده کن."
            )
            return
        return await handler(event, data)
