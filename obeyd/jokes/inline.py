from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import ContextTypes

from obeyd.jokes.functions import (
    format_text_joke,
    scorejoke_inline_keyboard_markup,
)
from obeyd.jokes.thompson import thompson_sampled_joke
from obeyd.middlewares import log_activity


@log_activity("inlinequery")
async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.inline_query

    joke = await thompson_sampled_joke()
    assert joke is not None

    await update.inline_query.answer(
        results=[
            InlineQueryResultArticle(
                id="joke",
                title="جوک بگو",
                input_message_content=InputTextMessageContent(
                    message_text=format_text_joke(joke)
                ),
                reply_markup=scorejoke_inline_keyboard_markup(joke),
            )
        ],
        is_personal=True,
        cache_time=5,
    )
