import asyncio
import logging
import os
import random
import sys

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

# Bot token can be obtained via https://t.me/BotFather
TOKEN = os.environ["API_TOKEN"]

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()

outputs = [
    "One",
    "Two",
    "Three",
]


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"سلام {html.bold(message.from_user.full_name)}!")


@dp.message(Command("joke"))
async def joke_handler(message: Message) -> None:
    await message.answer(random.choice(outputs))


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
