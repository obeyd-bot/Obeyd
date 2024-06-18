import numpy as np


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
