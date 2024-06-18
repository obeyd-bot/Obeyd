import numpy as np


class ThompsonSampling:
    def __init__(self, n_arms):
        self.n_arms = n_arms
        # Initialize mean and variance for each arm
        self.means = np.zeros(n_arms)
        self.vars = np.ones(n_arms)

    def select_arm(self):
        sampled_values = np.random.normal(self.means, np.sqrt(self.vars))
        print(sampled_values)
        return np.argmax(sampled_values)

    def update(self, chosen_arm, reward):
        # Update the mean and variance for the chosen arm
        mean = self.means[chosen_arm]
        var = self.vars[chosen_arm]

        # Update the parameters
        new_mean = (mean * var + reward) / (var + 1)
        new_var = var / (var + 1)

        self.means[chosen_arm] = new_mean
        self.vars[chosen_arm] = new_var
