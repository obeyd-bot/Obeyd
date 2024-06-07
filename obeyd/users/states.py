from aiogram.fsm.state import State, StatesGroup


class NewUserForm(StatesGroup):
    nickname = State()


class SetNicknameForm(StatesGroup):
    nickname = State()
