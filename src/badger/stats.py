from typing import Any

import numpy as np
from numpy.typing import NDArray


def none(data: NDArray[Any]) -> NDArray[Any]:
    return data


def median(data: NDArray[Any]) -> Any:
    return np.median(data)


def std_deviation(data: NDArray[Any]) -> Any:
    return np.std(data)


def median_deviation(data: NDArray[Any]) -> Any:
    median = np.median(data)

    return np.median(np.abs(data - median))


def max(data: NDArray[Any]) -> Any:
    return np.max(data)


def min(data: NDArray[Any]) -> Any:
    return np.min(data)


def percent_80(data: NDArray[Any]) -> Any:
    return np.percentile(data, 80)


def percent_20(data: NDArray[Any]) -> Any:
    return np.percentile(data, 20)


def avg_mean(data: NDArray[Any]) -> Any:
    percentile = np.percentile(data, 50)

    return np.mean(data[data > percentile])


def mean(data: NDArray[Any]) -> Any:
    return np.mean(data)
