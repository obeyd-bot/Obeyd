from celery import Celery

app = Celery("tasks", broker="redis://localhost:6379/0")


@app.task
def notify_admin_submit_joke(joke, from_user):
    print(f"new joke {joke} from {from_user}")
