from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from obeyd.models import User


async def find_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.scalar(select(User).where(User.user_id == user_id))
