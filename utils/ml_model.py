import numpy as np
from sklearn.linear_model import LinearRegression


class SimpleLinearRegression:
    def __init__(self):
        self.model = LinearRegression()

    def train(self, x, y):
        x = np.array(x).reshape(-1, 1)
        y = np.array(y)
        self.model.fit(x, y)

    def predict(self, x):
        x = np.array(x).reshape(-1, 1)
        return self.model.predict(x)[0]
