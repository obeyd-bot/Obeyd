from typing import Optional

from bson import ObjectId

from obeyd.db import db


async def random_joke():
    try:
        return (
            await db["jokes"]
            .aggregate([{"$match": {"accepted": True}}, {"$sample": {"size": 1}}])
            .next()
        )
    except StopAsyncIteration:
        return None


async def most_rated_joke(not_viewed_by_user_id: Optional[int]):
    views = (
        await db["joke_views"].find({"user_id": not_viewed_by_user_id}).to_list(None)
    )

    try:
        joke_id = (
            await db["jokes"]
            .aggregate(
                [
                    {
                        "$match": {
                            "accepted": True,
                            "_id": {
                                "$nin": [ObjectId(view["joke_id"]) for view in views]
                            },
                        }
                    },
                    {
                        "$lookup": {
                            "from": "joke_views",
                            "localField": "_id",
                            "foreignField": "joke_id",
                            "as": "views",
                        },
                    },
                    {"$unwind": {"path": "$views", "preserveNullAndEmptyArrays": True}},
                    {"$set": {"views.score": {"$ifNull": ["$views.score", 3]}}},
                    {"$group": {"_id": "$_id", "avg_score": {"$avg": "$views.score"}}},
                    {"$sort": {"avg_score": -1}},
                ]
            )
            .next()
        )["_id"]
        return await db["jokes"].find_one({"_id": joke_id})
    except StopAsyncIteration:
        return None
