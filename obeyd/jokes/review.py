from bson import ObjectId
from telegram import Update
from telegram.ext import ContextTypes

from obeyd.db import db
from obeyd.jokes.functions import format_text_joke
from obeyd.middlewares import admin_only, log_activity


async def update_joke_sent_to_admin(joke: dict, update: Update, accepted: bool):
    assert update.callback_query
    assert update.effective_user

    info_msg = f"{'تایید' if accepted else 'رد'} شده توسط <b>{update.effective_user.full_name}</b>"

    if joke["kind"] == "text":
        await update.callback_query.edit_message_text(
            text=f"{format_text_joke(joke)}\n\n{info_msg}",
        )
    elif joke["kind"] in ["voice", "photo"]:
        await update.callback_query.edit_message_caption(
            caption=f"{format_text_joke(joke)}\n\n{info_msg}",
        )
    elif joke["kind"] == "video_note":
        # video notes do not have caption, we can't edit the message
        pass
    else:
        raise Exception(
            "expected 'kind' to be one of 'text' or 'voice' or 'video_note' or 'photo'"
        )


async def reviewjoke_callback_notify_creator(context: ContextTypes.DEFAULT_TYPE):
    assert context.job

    joke = context.job.data
    assert isinstance(joke, dict)

    msg = "جوکت تایید شد 😁" if joke["accepted"] else "جوکت رد شد 😿"

    await context.bot.send_message(
        chat_id=joke["creator_id"], text=f"{msg}\n\n{format_text_joke(joke)}"
    )


@admin_only
@log_activity("reviewjoke")
async def reviewjoke_callback_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.callback_query
    assert update.effective_user
    assert isinstance(update.callback_query.data, str)
    assert context.job_queue

    _, joke_id, action = tuple(update.callback_query.data.split(":"))
    joke_id = ObjectId(joke_id)

    accepted = None
    if action == "accept":
        accepted = True
    elif action == "reject":
        accepted = False
    else:
        raise Exception("expected accept or reject")

    await db["jokes"].update_one(
        {"_id": joke_id}, {"$set": {"accepted": accepted, "visible": accepted}}
    )

    joke = await db["jokes"].find_one({"_id": joke_id})
    assert joke is not None

    if accepted:
        await update.callback_query.answer("تایید شد")
    else:
        await update.callback_query.answer("رد شد")

    context.job_queue.run_once(reviewjoke_callback_notify_creator, when=0, data=joke)

    await update_joke_sent_to_admin(joke, update, accepted=accepted)
