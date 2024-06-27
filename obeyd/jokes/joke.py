from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from obeyd.jokes.functions import (
    scorejoke_inline_keyboard_markup,
    select_joke_for,
    send_joke,
)
from obeyd.middlewares import log_activity


@log_activity("joke")
async def joke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    assert update.effective_user
    assert update.effective_chat

    joke = await select_joke_for(
        user_id=update.effective_user.id,
        chat_id=update.effective_chat.id,
        chat_type=update.effective_chat.type,
    )

    if joke is None:
        await update.message.reply_text(
            "دیگه جوکی ندارم که بهت بگم 😁 میتونی به جاش تو یک جوک بهم بگی",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/newjoke")]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return

    await send_joke(
        joke=joke,
        user_id=update.effective_user.id,
        chat_id=update.effective_chat.id,
        context=context,
        kwargs={"reply_markup": scorejoke_inline_keyboard_markup(joke)},
    )

    return ConversationHandler.END
