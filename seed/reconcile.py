# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from operator import ior, iand

from fuzzywuzzy import fuzz
from django.db.models import Q
from seed.mappings import reconcile_mappings

logger = logging.getLogger(__name__)


"""
Module seeks to provide a general way to tie together information about
a single entity from two datasources using sparse data.


Sample usage:

    A task or a view that wants to find a correlated building from another
    data set would execute the following set of calls:

    model_a is an instance of a model that I have (probably just recently
        loaded).
    model_b_qs is the dataset type we're trying to find matches in.

    ```
    possible_matches = search(model_a, model_b_qs)
    best_match = get_best_match(model_a, possible_matches)
    best_match
    >>> (0.89, AssessedBuildingInst)
    ```

"""


def build_q(model_a, a_attr, model_b_class, b_attr, a_value=None):
    """build Q objects for model_a in model_b_class among `attrs`.

    :param model_a: model instance.
    :param a_attr: str, attribute name on model_a whose value we search for.
    :param model_b_class: class, the object class we filter through.
    :param b_attr: str, the attribute name we're searching.

    """
    a_value = a_value or getattr(model_a, a_attr, None)
    if a_value:
        return Q(**{'{0}__icontains'.format(b_attr): a_value})

    return None


def build_q_filter(q_set, model_a, a_attr, model_b_class, b_attr, op, trans):
    """Build a set of Q objects to filter table results.

    :param q_set: the Q object set that's being built cumulatively.
    :param model_a: model instance.
    :param a_attr: str, the name of an attribute we're querying from.
    :param model_b_class: class, model class we're querying to.
    :param b_attr: str, model attribute we're querying to (on model_b_class).
    :param op: callable, takes two parameters. This callable should be an
        ``operator`` module function, e.g. operator.ior, or operator.iand.
    :param trans: callable or None. If callable, we apply this callable to
    our `a_attr` for circumstances in which we need to break up its value
    into sub values for more accurate querying (e.g. address data.).

    """
    if trans:
        # Think of breaking up the components of an address as these values.
        a_sub_values = trans(getattr(model_a, a_attr), b_attr)
        if isinstance(a_sub_values, Q):
            return op(q_set, a_sub_values)

        for sub_value in filter(lambda x: x, a_sub_values):
            # Let's not filter for Nulls.
            if not sub_value:
                continue
            q_set = iand(q_set, build_q(
                model_a, a_attr, model_b_class, b_attr, a_value=sub_value
            ))

    sub_q = build_q(model_a, a_attr, model_b_class, b_attr)
    if not sub_q:
        return q_set

    return op(q_set, sub_q)


def _get_mapping(mapping, sample_model):
    """Helper method to fetch the correct mapping for a given model."""
    return getattr(
        reconcile_mappings,
        '{0}_{1}'.format(mapping, sample_model.__class__.__name__.upper()),
        []
    )


def _unpack_a_attr(a_attr):
    """Sometimes a_ttr is packed with a callable for deconstructing it."""
    trans = None
    if isinstance(a_attr, tuple) and len(a_attr) == 2:
        trans, a_attr = a_attr

    return trans, a_attr


def search(model_a, model_b_qs, mapping='FIRST_PASS', op=ior):
    """Create and execute filters according to mapping rules.

    :param model_a: model instance we're querying from.
    :param model_b_qs: QuerySet, the pre-filtered set of models to match.
    :param mapping: str, prefix for a mapping between model_a and model_b.
    :param op: callable, how we combine this set of Q objects.
    :rtype Queryset: the Q objects are strung together and passed ``filter``.
        The results, if any, are the set of possible matches.

    """
    recon_attrs = _get_mapping(mapping, model_a)
    q_filter_set = Q()
    for a_attr, b_attr in recon_attrs:
        trans, a_attr = _unpack_a_attr(a_attr)
        # Build up a chain or `OR`ed  or `AND`ed filters.
        q_filter_set = build_q_filter(
            q_filter_set, model_a, a_attr, model_b_qs, b_attr, op, trans=trans
        )

    if q_filter_set.children:
        return model_b_qs.filter(q_filter_set)

    return model_b_qs


def calculate_confidence(model_a, model_b, mapping='FIRST_PASS'):
    """Determine the similarity between model_a and model_b.

    Goes through the mappings and compares those attrs
    between each of the modules produced in the ``search`` function.

    :rtype float: 0.0 to 1.0, the degree that the two models are similar.

    """
    attr_map = _get_mapping(mapping, model_a)
    if not attr_map:
        return 0.0

    total_match = 0.0
    # This becomes our denominator for arithemetic mean.
    num_attrs = 0.0
    for a_attr, b_attr in attr_map:
        _trans, a_attr = _unpack_a_attr(a_attr)
        a_value = getattr(model_a, a_attr)
        b_value = getattr(model_b, b_attr)
        if not a_value or not b_value:
            continue

        num_attrs += 1.0

        # Because we want a ratio, not a precentage
        ratio = fuzz.token_set_ratio(
            unicode(a_value), unicode(b_value)
        ) / 100.0
        total_match += ratio

    return total_match / max(num_attrs, 1)


def get_best_match(model_a, search_results):
    """Return highest confidence model_b match and its confidence number.

    :param model_a: model instance, the known model.
    :param search_results: a queryset of `model_b` insts returned from `search`
    :rtype tuple: (float, model_b_inst|None)

    """
    largest_conf = 0.0
    largest_model_b = None
    for model_b in search_results:
        conf = calculate_confidence(model_a, model_b)
        if conf > largest_conf:
            largest_conf = conf
            largest_model_b = model_b

    return largest_conf, largest_model_b
