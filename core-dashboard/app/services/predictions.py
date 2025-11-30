import numpy as np
from sklearn.linear_model import LinearRegression

def predict_steps(steps_data: list) -> int:
    if len(steps_data) < 2:
        return 0
    X = np.arange(len(steps_data)).reshape(-1, 1)
    y = np.array([d['steps'] for d in steps_data])
    model = LinearRegression()
    model.fit(X, y)
    return int(model.predict([[len(X)]])[0])