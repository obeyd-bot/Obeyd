from aiogram.filters.callback_data import CallbackData


class LikeCallback(CallbackData, prefix="like"):
    joke_id: int
    score: int


class ReviewJokeCallback(CallbackData, prefix="review-joke"):
    joke_id: int
    command: str
