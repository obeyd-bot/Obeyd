import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

db_uri = os.environ["MONGODB_URI"]
client = AsyncIOMotorClient(db_uri.rsplit("/", 1)[0])
db = client[db_uri.rsplit("/", 1)[1]]


async def create_indexes():
    await db["users"].create_index("user_id", name="user_id_unique", unique=True)
    await db["users"].create_index("nickname", name="nickname_unique", unique=True)
    await db["joke_views"].create_index(
        ["user_id", "joke_id"], name="user_id_joke_id_unique", unique=True
    )
    await db["scores"].create_index(
        ["user_id", "joke_id"], name="user_id_joke_id_unique", unique=True
    )
    await db["recurrings"].create_index("chat_id", name="chat_id_unique", unique=True)


if __name__ == "__main__":
    asyncio.run(create_indexes())
