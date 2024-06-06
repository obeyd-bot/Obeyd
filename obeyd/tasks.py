import asyncio

from celery import Celery

from obeyd.jokes.tasks import notify_admin_submit_joke_async
from obeyd.likes.tasks import notify_creator_like_joke_async

app = Celery("tasks", broker="redis://localhost:6379/0")
app.conf.broker_connection_retry_on_startup = True


@app.task
def notify_creator_like_joke(joke_id, score):
    asyncio.run(notify_creator_like_joke_async(joke_id, score))


@app.task
def notify_admin_submit_joke(joke_id, joke_text, from_user, from_user_nickname):
    asyncio.run(
        notify_admin_submit_joke_async(
            joke_id, joke_text, from_user, from_user_nickname
        )
    )
