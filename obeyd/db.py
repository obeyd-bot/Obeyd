import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
db = client[os.environ["MONGODB_DB"]]


async def create_indexes():
    await db.create_collection("users")
    await db.create_collection("jokes")
    await db.create_collection("scores")
    await db.create_collection("activities")

    await db["users"].create_index("nickname", unique=True)
    await db["scores"].create_index(["user_id", "joke_id"], unique=True)


if __name__ == "__main__":
    asyncio.run(create_indexes())
