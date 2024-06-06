from aiogram.fsm.state import State, StatesGroup


class NewJokeForm(StatesGroup):
    joke = State()
