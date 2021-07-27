# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from builtins import str
from functools import cmp_to_key

import jellyfish


def sort_scores(a, b):
    """
    Custom sort method in order to create a bias around the use of PropertyState over TaxLotState. This just works
    because the extra string comparison concats the table name with the field name. Since P is < T, it returns
    the correct order.
    """
    if a[2] > b[2]:
        return -1
    elif a[2] == b[2]:  # Sort by the strings if they match up
        com_a = '.'.join(
            a[0:2])  # so, 0:2 returns the first 2 elements, okay python, you win this time.
        com_b = '.'.join(b[0:2])
        if com_a > com_b:
            return 1
        else:
            return -1
    else:
        return 1


def best_match(s, categories, top_n=5):
    """
    Return the top N best matches from your categories with the best match
    in the 0th position of the return list. The comparison does not check
    the first element of the category name, only the second element.

    Usage:
            >>> best_match('illinois', [ ('_', 'Michigan'),
                                         ('_', 'Ohio',
                                         ('_', 'Illinois') ],
                                        2)
            [('Illinois', 96), ('Michigan', 22)]

    Args:
        s: str value to find best match
        categories: list of tuples to compare against. needs to be
        [('table1', 'value1'), ('table2', 'value2')]
        top_n: number of matches to return

    Returns:
        list of tuples (table, guess, percentage)

    """

    # print('starting match on {}'.format(s))
    scores = []
    for cat in categories:
        # verify that the category has two elements, if not, then just
        # return _ for the first category. Need this because fuzzy_in_set uses the
        # same method
        table_name = '_'
        category = None
        if isinstance(cat, tuple):
            table_name = cat[0]
            category = cat[1]
        else:
            category = cat

        scores.append(
            (
                table_name,
                category,
                jellyfish.jaro_winkler(
                    str(s.encode('ascii', 'replace').lower()),
                    str(category.encode('ascii', 'replace').lower())
                )
            )
        )

        # sort first by the ones

    # print('all scores for {} are {}'.format(s, scores))
    scores.sort()
    scores = sorted(scores, key=cmp_to_key(sort_scores))
    # take the top n number of matches
    scores = scores[:top_n]
    # convert to hundreds
    scores = [(score[0], score[1], int(score[2] * 100)) for score in scores]
    # print('ending all categories match of {} with scores {}'.format(s, scores))

    return scores


def fuzzy_in_set(column_name, ontology, percent_confidence=95):
    """Return True if column_name is in the ontology."""
    table, match, percent = best_match(column_name, ontology, top_n=1)[0]

    return percent > percent_confidence
