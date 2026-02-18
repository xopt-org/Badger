from typing import Any

import numpy as np
from numpy.typing import NDArray


def none(data: NDArray[np.floating[Any]]) -> NDArray[np.floating[Any]]:
    return data


def median(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    return np.median(data)


def std_deviation(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    return np.std(data)


def median_deviation(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    med = np.median(data)

    return np.median(np.abs(data - med))


def max(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    return np.max(data)


def min(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    return np.min(data)


def percent_80(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    return np.percentile(data, 80)


def percent_20(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    return np.percentile(data, 20)


def avg_mean(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    percentile = np.percentile(data, 50)

    return np.mean(data[data > percentile])


def mean(data: NDArray[np.floating[Any]]) -> np.floating[Any]:
    return np.mean(data)
