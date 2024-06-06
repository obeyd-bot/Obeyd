from aiogram.filters.callback_data import CallbackData


class ReviewJokeCallback(CallbackData, prefix="review-joke"):
    joke_id: int
    command: str
