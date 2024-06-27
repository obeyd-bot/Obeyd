import asyncio
from obeyd.db import db


async def main():
    await db["users"].delete_many({})
    await db["jokes"].delete_many({})
    await db["joke_views"].delete_many({})
    await db["joke_views_chat"].delete_many({})
    await db["recurrings"].delete_many({})
    await db["activities"].delete_many({})


if __name__ == "__main__":
    asyncio.run(main())
