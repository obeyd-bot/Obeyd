from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.dialects.postgresql import insert

from obeyd.models import User, async_session
from obeyd.users.states import NewUserForm

users_router = Router()


@users_router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    assert message.from_user
    await state.set_state(NewUserForm.nickname)
    await message.answer(
        f"سلام! من عبید زاکانی هستم. میتونم برات جوک بگم. چطوری صدات کنم؟"
    )


@users_router.message(NewUserForm.nickname)
async def command_start_nickname_handler(message: Message, state: FSMContext) -> None:
    assert message.from_user

    data = await state.update_data(nickname=message.text)
    await state.clear()

    async with async_session() as session:
        await session.execute(
            insert(User).values(user_id=message.from_user.id, nickname=data["nickname"])
        )
        await session.commit()

    await message.answer(
        f"خوشوقتم {data['nickname']} :) حالا /new_joke رو برام بنویس تا برات جوک بگم."
    )
