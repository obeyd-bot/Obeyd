from aiogram.filters.callback_data import CallbackData


class LikeCallback(CallbackData, prefix="like"):
    joke_id: int
    score: int
