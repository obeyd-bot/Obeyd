from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from obeyd.models import User, async_session
from obeyd.users.services import find_user_by_id
from obeyd.users.states import NewUserForm, SetNicknameForm

users_router = Router()


@users_router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    assert message.from_user

    async with async_session() as session:
        user = await find_user_by_id(session, message.from_user.id)
        if user is not None:
            await message.answer(
                "ما قبلا با همدیگه آشنا شدیم. برای اینکه اسمت رو عوض کنی از دستور /setname استفاده کن."
            )
            return

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


@users_router.message(Command("setname"))
async def command_set_nickname_start_handler(
    message: Message, state: FSMContext
) -> None:
    assert message.from_user

    await state.set_state(SetNicknameForm.nickname)

    await message.answer(f"چطوری صدات کنم؟")


@users_router.message(Command("setname"))
async def command_set_nickname_end_handler(message: Message, state: FSMContext) -> None:
    assert message.from_user

    data = await state.update_data(nickname=message.text)
    await state.clear()

    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.user_id == message.from_user.id)
            .values(nickname=data["nickname"])
        )
        await session.commit()

    await message.answer(
        f"خوشوقتم {data['nickname']} :) حالا /new_joke رو برام بنویس تا برات جوک بگم."
    )


@users_router.message(Command("whoami"))
async def command_whoami_handler(message: Message) -> None:
    assert message.from_user

    async with async_session() as session:
        user = await find_user_by_id(session, message.from_user.id)
        assert user is not None

    await message.answer(f"هنوز زوده آلزایمر بگیری {user.nickname}!")
