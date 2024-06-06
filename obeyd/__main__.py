import asyncio
import logging

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardRemove

from obeyd.bot import new_bot
from obeyd.jokes.routes import jokes_router
from obeyd.likes.routes import likes_router
from obeyd.users.routes import users_router


async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer(
        "وقت ما رو نگیر بی خودی دیگه...", reply_markup=ReplyKeyboardRemove()
    )


async def main() -> None:
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(jokes_router)
    dp.include_router(likes_router)
    dp.include_router(users_router)
    dp.message(Command("cancel"))(cancel_handler)

    bot = new_bot()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
