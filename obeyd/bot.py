import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


bot = Bot(
    token=os.environ["API_TOKEN"],
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
