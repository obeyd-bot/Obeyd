import os

REVIEW_JOKES_CHAT_ID = os.environ["OBEYD_REVIEW_JOKES_CHAT_ID"]


SCORES = {
    1: {
        "emoji": "💩",
        "notif": "💩💩💩",
        "score_notif": "<b>{s}</b> با جوکت اصلا حال نکرد 💩💩💩",
    },
    2: {
        "emoji": "😐",
        "notif": "😐😐😐",
        "score_notif": "<b>{s}</b> با جوکت حال نکرد 😐😐😐",
    },
    3: {
        "emoji": "🙂",
        "notif": "🙂🙂🙂",
        "score_notif": "<b>{s}</b> فکر میکنه جوکت بد هم نبوده 🙂🙂🙂",
    },
    4: {
        "emoji": "😁",
        "notif": "😁😁😁",
        "score_notif": "<b>{s}</b> با جوکت حال کرد 😁😁😁",
    },
    5: {
        "emoji": "😂",
        "notif": "😂😂😂",
        "score_notif": "<b>{s}</b> با جوکت خیلی حال کرد 😂😂😂",
    },
}

RECURRING_INTERVALS = {
    "هر روز": {
        "code": "daily",
        "text": "هر روز ساعت ۸ شب",
    },
    "هر هفته": {
        "code": "weekly",
        "text": "هر هفته پنج شنبه ساعت ۸ شب",
    },
    "هر دقیقه": {
        "code": "minutely",
        "text": "هر دقیقه",
    },
}


FILES_BASE_DIR = os.environ.get("OBEYD_FILES_BASE_DIR", "files")
