import asyncio

import sentry_sdk
from celery import Celery

from obeyd.jokes.tasks import notify_admin_submit_joke_async
from obeyd.likes.tasks import notify_creator_like_joke_async

app = Celery("tasks", broker="redis://localhost:6379/0")
app.conf.broker_connection_retry_on_startup = True


sentry_sdk.init(
    dsn="https://3f61d721091e147adc6ee6028f06aa25@o673833.ingest.us.sentry.io/4507386459127808",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)


@app.task
def notify_creator_like_joke(joke_id, score):
    asyncio.run(notify_creator_like_joke_async(joke_id, score))


@app.task
def notify_admin_submit_joke(joke_id, joke_text, from_user):
    asyncio.run(notify_admin_submit_joke_async(joke_id, joke_text, from_user))
