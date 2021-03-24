# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import absolute_import

import collections

from celery.utils.log import get_task_logger

from seed.models import (
    PropertyState,
    TaxLotState)

_log = get_task_logger(__name__)


class EquivalencePartitioner(object):
    """Class for calculating equivalence classes on model States

    The EquivalencePartitioner is configured with a list of rules
    saying "two objects are equivalent if these two pieces of data are
    identical" or "two objects are not equivalent if these two pieces
    of data are different."  The partitioner then takes a group of
    objects (typically PropertyState and TaxLotState objects) and
    returns a partition of the objects (a collection of lists, where
    each object is a member of exactly one of the lists), where each
    list represents a "definitely distinct" element (i.e. two
    PropertyState objects with no values for pm_property_id,
    custom_id, etc may very well represent the same building, but we
    can't say that for certain).

    Some special cases that it handles based on SEED needs:

    - special treatment for matching based on multiple fields

    - Allowing one Field to hold "canonical" information (e.g. a
      building_id) and others (e.g. a custom_id) to hold potential
      information: when an alternate field (e.g. custom_id_1) is used,
      the logic does not necessarily assume the custom_id_1 means the
      portfolio manager id, unless p1.pm_property_id==p2.custom_id_1,
      etc.

    - equivalence/non-equivalence in both directions.  E.g. if
      ps1.pm_property_id == ps2.pm_property_id then ps1 represents the
      same object as ps2.  But if ps1.normalized_address ==
      ps2.normalized_address, then ps1 is related to ps2, unless
      ps1.pm_property_id != ps2.pm_property_id, in which case ps1
      definitely is not the same as ps2.

    """

    def __init__(self, equivalence_class_description, identity_fields):
        """Constructor for class.

        Takes a list of mappings/conditions for object equivalence, as
        well as a list of identity fields (if these are not identical,
        the two objects are definitely different object)
        """

        self.equiv_comparison_key_func = self.make_resolved_key_calculation_function(
            equivalence_class_description)
        self.equiv_canonical_key_func = self.make_canonical_key_calculation_function(
            equivalence_class_description)
        self.identity_key_func = self.make_canonical_key_calculation_function(
            [(x,) for x in identity_fields])

        return

    @classmethod
    def make_default_state_equivalence(kls, equivalence_type):
        """
        Class for dynamically constructing an EquivalencePartitioner
        depending on the type of its parameter.
        """
        if equivalence_type == PropertyState:
            return kls.make_propertystate_equivalence()
        elif equivalence_type == TaxLotState:
            return kls.make_taxlotstate_equivalence()
        else:
            err_msg = ("Type '{}' does not have a default "
                       "EquivalencePartitioner set.".format(equivalence_type.__class__.__name__))
            raise ValueError(err_msg)

    @classmethod
    def make_propertystate_equivalence(kls):
        property_equivalence_fields = [
            ("ubid",),
            ("pm_property_id", "custom_id_1"),
            ("custom_id_1",),
            ("normalized_address",)
        ]
        property_noequivalence_fields = ["pm_property_id"]

        return kls(property_equivalence_fields, property_noequivalence_fields)

    @classmethod
    def make_taxlotstate_equivalence(kls):
        """Return default EquivalencePartitioner for TaxLotStates

        Two tax lot states are identical if:

        - Their jurisdiction_tax_lot_ids are the same, which can be
          found in jurisdiction_tax_lot_ids or custom_id_1
        - Their custom_id_1 fields match
        - Their normalized addresses match

        They definitely do not match if :

        - Their jurisdiction_tax_lot_ids do not match.
        """
        tax_lot_equivalence_fields = [
            ("jurisdiction_tax_lot_id", "custom_id_1"),
            ("ulid",),
            ("custom_id_1",),
            ("normalized_address",)
        ]
        tax_lot_noequivalence_fields = ["jurisdiction_tax_lot_id"]
        return kls(tax_lot_equivalence_fields, tax_lot_noequivalence_fields)

    @staticmethod
    def make_canonical_key_calculation_function(list_of_fieldlists):
        """Create a function that returns the "canonical" key for the object -
        where the official value for any position in the tuple can
        only come from the first object.
        """
        # The official key can only come from the first field in the
        # list.
        canonical_fields = [fieldlist[0] for fieldlist in list_of_fieldlists]
        return lambda obj: tuple([getattr(obj, field) for field in canonical_fields])

    @classmethod
    def make_resolved_key_calculation_function(kls, list_of_fieldlists):
        # This "resolves" the object to the best potential value in
        # each field.
        return (
            lambda obj: tuple(
                [kls._get_resolved_value_from_object(obj, list_of_fields) for list_of_fields in
                 list_of_fieldlists]
            )
        )

    @staticmethod
    def _get_resolved_value_from_object(obj, list_of_fields):
        for f in list_of_fields:
            val = getattr(obj, f)
            if val:
                return val
        else:
            return None

    @staticmethod
    def calculate_key_equivalence(key1, key2):
        for key1_value, key2_value in list(zip(key1, key2)):
            if key1_value == key2_value and key1_value is not None:
                return True
        else:
            return False

    def calculate_comparison_key(self, obj):
        return self.equiv_comparison_key_func(obj)

    def calculate_canonical_key(self, obj):
        return self.equiv_canonical_key_func(obj)

    def calculate_identity_key(self, obj):
        return self.identity_key_func(obj)

    @staticmethod
    def key_needs_merging(original_key, new_key):
        return True in [not a and b for (a, b) in list(zip(original_key, new_key))]

    @staticmethod
    def merge_keys(key1, key2):
        return [a if a else b for (a, b) in list(zip(key1, key2))]

    @staticmethod
    def identities_are_different(key1, key2):
        for (x, y) in list(zip(key1, key2)):
            if x is None or y is None:
                continue
            if x != y:
                return True
        else:
            return False

    def calculate_equivalence_classes(self, list_of_obj):
        """
        There is some subtlety with whether we use "comparison" keys
        or "canonical" keys.  This reflects the difference between
        searching vs. deciding information is official.

        For example, if we are trying to match on pm_property_id is,
        we may look in either pm_property_id or custom_id_1.  But if
        we are trying to ask what the pm_property_id of a State is
        that has a blank pm_property, we would not want to say the
        value in the custom_id must be the pm_property_id.

        :param list_of_obj:
        :return:
        """
        equivalence_classes = collections.defaultdict(list)
        identities_for_equivalence = {}

        for (ndx, obj) in enumerate(list_of_obj):
            cmp_key = self.calculate_comparison_key(obj)
            identity_key = self.calculate_identity_key(obj)

            for class_key in equivalence_classes:
                if self.calculate_key_equivalence(class_key, cmp_key) and not \
                    self.identities_are_different(identities_for_equivalence[class_key],
                                                  identity_key):

                    equivalence_classes[class_key].append(ndx)

                    if self.key_needs_merging(class_key, cmp_key):
                        merged_key = self.merge_keys(class_key, cmp_key)
                        equivalence_classes[merged_key] = equivalence_classes.pop(class_key)
                        identities_for_equivalence[merged_key] = identity_key
                    break
            else:
                can_key = self.calculate_canonical_key(obj)
                equivalence_classes[can_key].append(ndx)
                identities_for_equivalence[can_key] = identity_key
        return equivalence_classes
