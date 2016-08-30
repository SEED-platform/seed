# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import jellyfish


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

    scores = []
    for cat in categories:
        # test_cat = cat[0] + '.' + cat[1]
        scores.append(
            (
                cat[0],
                cat[1],
                jellyfish.jaro_winkler(
                    s.encode('ascii', 'replace').upper(),
                    cat[1].encode('ascii', 'replace').upper()
                )
            )
        )

    scores = sorted(scores, key=lambda x: x[2])
    scores = scores[-top_n:]
    scores = [(score[0], score[1], int(score[2] * 100)) for score in scores]
    scores.reverse()

    return scores


def fuzzy_in_set(column_name, ontology, percent_confidence=95):
    """Return True if column_name is in the ontology."""
    table, match, percent = best_match(column_name, ontology, top_n=1)[0]

    return percent > percent_confidence
