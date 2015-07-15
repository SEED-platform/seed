"""
:copyright: (c) 2014 Building Energy Inc
"""
import jellyfish


def best_match(s, categories, top_n=5):
    """Return the top N best matches from your categories."""
    scores = []
    for cat in categories:
        scores.append((cat, jellyfish.jaro_winkler(s.upper(), cat.upper())))

    scores = sorted(scores, key=lambda x: x[1])
    scores = scores[-top_n:]
    scores = [(scores[0][0], int(scores[0][1] * 100))]

    return scores


def fuzzy_in_set(column_name, ontology, percent_confidence=95):
    """Return True if column_name is in the ontology."""
    match, percent = best_match(
        column_name, ontology, top_n=1
    )[0]

    return percent > percent_confidence
