import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
db = client[os.environ["MONGODB_DB"]]


async def create_indexes():
    await db["users"].create_index("user_id", name="user_id_unique", unique=True)
    await db["users"].create_index("nickname", name="nickname_unique", unique=True)
    await db["scores"].create_index(
        ["user_id", "joke_id"], name="user_id_joke_id_unique", unique=True
    )


if __name__ == "__main__":
    asyncio.run(create_indexes())
