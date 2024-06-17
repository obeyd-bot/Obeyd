from datetime import datetime, timezone

from bson import ObjectId
from telegram import Update
from telegram.ext import ContextTypes

from obeyd.activities import log_activity_custom
from obeyd.config import SCORES
from obeyd.db import db
from obeyd.middlewares import log_activity


@log_activity("scorejoke")
async def scorejoke_callback_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.effective_user
    assert update.callback_query
    assert isinstance(update.callback_query.data, str)

    _, joke_id, score = tuple(update.callback_query.data.split(":"))

    joke_score = {
        "user_id": update.effective_user.id,
        "joke_id": joke_id,
        "score": int(score),
        "created_at": datetime.now(tz=timezone.utc),
    }

    view = await db["joke_views"].find_one(
        {"user_id": update.effective_user.id, "joke_id": joke_id}
    )
    if view is not None and view["score"] is not None:
        await update.callback_query.answer("قبلا به این جوک رای دادی")
        return

    await db["joke_views"].update_one(
        {"user_id": update.effective_user.id, "joke_id": joke_id},
        {"$set": {"score": int(score), "scored_at": datetime.now(tz=timezone.utc)}},
    )

    await update.callback_query.answer(SCORES[score]["notif"])
    assert context.job_queue
    context.job_queue.run_once(
        callback=scorejoke_callback_notify_creator,
        when=0,
        data=joke_score,
    )


async def scorejoke_callback_notify_creator(context: ContextTypes.DEFAULT_TYPE):
    assert context.job
    assert isinstance(context.job.data, dict)

    joke_score = context.job.data

    joke = await db["jokes"].find_one({"_id": ObjectId(joke_score["joke_id"])})
    scored_by_user = await db["users"].find_one({"user_id": joke_score["user_id"]})
    assert joke
    assert scored_by_user

    await context.bot.send_message(
        chat_id=joke["creator_id"],
        text=SCORES[str(joke_score["score"])]["score_notif"].format(
            s=scored_by_user["nickname"]
        ),
    )
