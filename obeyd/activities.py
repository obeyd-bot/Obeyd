from datetime import datetime, timezone
from typing import Any, Optional

from telegram import Update

from obeyd.db import db


async def log_activity_custom(
    update: Update, kind: str, data: Optional[dict[str, Any]] = None
):
    await db["activities"].insert_one(
        {
            "kind": kind,
            "user_id": (
                update.effective_user.id if update.effective_user is not None else None
            ),
            "user_name": (
                update.effective_user.full_name
                if update.effective_user is not None
                else None
            ),
            "chat_type": (
                update.effective_chat.type
                if update.effective_chat is not None
                else None
            ),
            "chat_id": (
                update.effective_chat.id if update.effective_chat is not None else None
            ),
            "chat_name": (
                update.effective_chat.full_name
                if update.effective_chat is not None
                else None
            ),
            "data": data,
            "created_at": datetime.now(tz=timezone.utc),
        }
    )
