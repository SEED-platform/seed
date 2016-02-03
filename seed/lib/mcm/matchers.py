# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import jellyfish


def best_match(s, categories, top_n=5):
    """Return the top N best matches from your categories with the best match
    in the 0th position of the return list.
    Usage:
            >>> best_match('ilinois', ['Michigan', 'Ohio', 'Illinois'], 2)
            [('Illinois', 96), ('Michigan', 22)]

    :param s: str value to find best match
    :param categories: list values to compare against
    :param top_n: number of matches to return
    :returns: list of tuples (guess, percentage)
    """
    scores = []
    for cat in categories:
        scores.append((cat, jellyfish.jaro_winkler(
            s.encode('ascii', 'replace').upper(),
            cat.encode('ascii', 'replace').upper()
        )))

    scores = sorted(scores, key=lambda x: x[1])
    scores = scores[-top_n:]
    scores = [(score[0], int(score[1] * 100)) for score in scores]
    scores.reverse()

    return scores


def fuzzy_in_set(column_name, ontology, percent_confidence=95):
    """Return True if column_name is in the ontology."""
    match, percent = best_match(
        column_name, ontology, top_n=1
    )[0]

    return percent > percent_confidence
