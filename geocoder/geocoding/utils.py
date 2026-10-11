"""Useful methods.

This module defines some useful methods for the application.

Attributes:
    SCALE (int): The scale conversion of float to int.

"""
import os

import numpy as np

SCALE = 7


def env_bool(name, default=False):
    """Read a boolean environment variable (1/true/t/yes/y/on, case insensitive)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 't', 'yes', 'y', 'on')


def degree_to_int(degree):
    """Convert the float degree to int.
    """
    fl = float(degree)
    return int(fl * (10 ** SCALE))


def int_to_degree(integer):
    """Convert the int integer to a float.
    """
    i = int(integer)
    return float(i / (10 ** SCALE))


def search(element, indices, values, sorted=True):
    """Search element in a list of values.

    Args:
        element (int or str): The element to search.
        indices (:obj:`list` of :obj:`int`): The list of indices to consider in
            the search.
        values (:obj:`list` of :obj:`int` or `str`): The list of values.
        sorted (bool, optional): True if values are sorted, false otherwise.

    Returns:
        tuple: the index of the selected index in the indices list and the index of the selected value in the
        values list, as two integers.

    """
    # If values is a sorted list, we only need the limits of that list
    if sorted:
        def get_index(i):
            return i
        start, end = (indices[0], indices[1])
    # If values is not sorted, we need the list of indices of values if it was
    # sorted
    else:
        def get_index(i):
            return indices[min(i, len(indices) - 1)]
        start, end = (0, len(indices))

    return binary_search(element, values, start, end, get_index)


def binary_search(element, values, start, end, get_index):
    """Binary search of element in values.
    """
    i = start
    j = end
    while i < j:
        mid = (i + j) // 2
        midvalue = values[get_index(mid)]
        if midvalue < element:
            i = mid + 1
        else:
            j = mid
    return i, get_index(i)


def most_similar(indices, values, similarity):
    """Find the value with greatest score of similarity.
    """
    # read all the candidates at once: element by element access of a memory-mapped column is slow
    if isinstance(indices, range) and indices.step == 1:
        candidates = values[indices.start:indices.stop]
    else:
        candidates = values[np.fromiter(indices, dtype=np.int64)]
    candidates = np.asarray(candidates).tolist()

    max_result = None, None, None
    for (rang, (index, value)) in enumerate(zip(indices, candidates)):
        score = similarity(value)
        max_score = max_result[0]
        if score == 1:
            return score, rang, index
        elif max_score is None or score > max_score:
            max_result = score, rang, index
    return max_result
