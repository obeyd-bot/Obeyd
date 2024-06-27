from bson import ObjectId
import numpy as np

from obeyd.db import db


class ThompsonSampling:
    def __init__(self, n_arms, default_mean: float, default_var: float):
        self.n_arms = n_arms
        self.observations = {i: [] for i in range(self.n_arms)}
        self.default_mean = default_mean
        self.default_var = default_var

    def select_arm(self):
        means = np.array(
            [
                (
                    np.mean(self.observations[i])
                    if self.observations[i]
                    else self.default_mean
                )
                for i in range(self.n_arms)
            ]
        )
        vars = np.array(
            [
                (
                    np.var(self.observations[i])
                    if self.observations[i]
                    else self.default_var
                )
                for i in range(self.n_arms)
            ]
        )

        sampled_values = np.random.normal(means, np.sqrt(vars))
        return np.argmax(sampled_values)

    def insert_observation(self, chosen_arm, value):
        self.observations[chosen_arm].append(value)


async def thompson_sampled_joke(
    exclude_jokes: list[ObjectId] | None = None,
) -> dict | None:
    pipeline = [
        {
            "$match": {
                "visible": True,
                "_id": {"$nin": exclude_jokes or []},
            }
        },
        {
            "$lookup": {
                "from": "joke_views",
                "localField": "_id",
                "foreignField": "joke_id",
                "as": "views",
            }
        },
    ]

    results = await db.jokes.aggregate(pipeline).to_list(None)

    if len(results) == 0:
        return None

    thompson = ThompsonSampling(n_arms=len(results), default_mean=3.0, default_var=2.0)

    average_user_score = {}
    for joke in results:
        for view in joke["views"]:
            if "score" not in view or view["score"] is None:
                continue
            if view["user_id"] not in average_user_score:
                average_user_score[view["user_id"]] = {"count": 0, "sum": 0}
            average_user_score[view["user_id"]]["count"] += 1
            average_user_score[view["user_id"]]["sum"] += view["score"]

    for i, joke in enumerate(results):
        for view in joke["views"]:
            score = None
            if "score" not in view or view["score"] is None:
                if view["user_id"] in average_user_score:
                    score = (
                        average_user_score[view["user_id"]]["sum"]
                        / average_user_score[view["user_id"]]["count"]
                    )
            else:
                score = view["score"]
            if score:
                thompson.insert_observation(i, score)

    selected_joke = results[int(thompson.select_arm())]

    return selected_joke
