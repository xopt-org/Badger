"""Statistical reducer functions for Badger objective evaluation. These
functions aggregate array-valued observations into scalar metrics (median,
mean, percentiles, etc.) used by the optimization loop to assess solution
quality."""

import numpy as np


def none(data):
    return data


def median(data):
    return np.median(data)


def std_deviation(data):
    return np.std(data)


def median_deviation(data):
    median = np.median(data)

    return np.median(np.abs(data - median))


def max(data):
    return np.max(data)


def min(data):
    return np.min(data)


def percent_80(data):
    return np.percentile(data, 80)


def percent_20(data):
    return np.percentile(data, 20)


def avg_mean(data):
    percentile = np.percentile(data, 50)

    return np.mean(data[data > percentile])


def mean(data):
    return np.mean(data)
