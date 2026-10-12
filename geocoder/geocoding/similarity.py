"""String similarity methods.

This module defines the class used for computing the score of similarity
between two strings. Even with the ideas for computing this score are well know
(ngrams), the exactly method is not and that`s why an own implementation was
needed.
"""


from functools import lru_cache


@lru_cache(maxsize=1 << 18)
def grams(s):
    """The sets of unigrams and bigrams of a string, and the score of their union.

    The score of a set of strings is the sum of their lengths, hence the number of unigrams plus twice the number of
    bigrams. Candidates are the same few thousand street names for most queries: caching saves most of the work.

    :rtype: tuple
    """
    unigrams = frozenset(s)
    bigrams = frozenset(s[i:i + 2] for i in range(len(s) - 1))
    return unigrams, bigrams, len(unigrams) + 2 * len(bigrams)


class Similarity:
    """Class defining the string similarity methods using uni and bigrams.

    One object of this class will have a set of uni and bigrams of a string s
    as an attribute. The string s is an argument of __init__ and this set is
    used in the score method to compute the score of similarity between s and
    one second string t, for example.

    Attributes:
        slice_set (:obj:`set` of :obj:`str`): The set of uni and bigrams.
        slice_set_score (int): The score of the attribute slice_set, that is,
            the sum of the length of the strings in that set.

    """

    def __init__(self, s):
        """
        Args:
            s (str): The string to compute the 1 and 2 grams set.

        """
        self.unigrams, self.bigrams, self.slice_set_score = grams(s)
        self.slice_set = self.unigrams | self.bigrams

    def score(self, t):
        """String similarity score.

        The score of similarity between two strings s and t is defined as the
        score of the intersection over the score of the union of two sets: the
        set of unigrams and bigrams of s and t.

        Args:
            t (str): The string to compare.

        Returns:
            (float): The score of similarity between t and the string s passed
                as argument in the initialization of the class.

        """
        unigrams, bigrams, score = grams(t)

        # The score of the intersection of the sets of t and s
        intersection_score = len(unigrams & self.unigrams) + 2 * len(bigrams & self.bigrams)

        union_score = score + self.slice_set_score - intersection_score

        # The union_score is zero only if both s and t are empty
        if union_score == 0:  # pragma: no cover
            return 0

        return intersection_score / union_score
