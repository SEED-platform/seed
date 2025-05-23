"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author Nicholas Long <nicholas.long@nrel.gov>
"""

import logging
from functools import cmp_to_key

from seed.lib.mcm import matchers

_log = logging.getLogger(__name__)


def sort_duplicates(a, b):
    """
    Custom sort for the duplicate hash to decide which raw column will get the mapping suggestion
    based on the confidence.
    """
    if a["confidence"] > b["confidence"]:
        return -1
    elif a["confidence"] == b["confidence"]:
        if a["raw_column"] > b["raw_column"]:  # Sort by the strings--yay determinism
            return 1
        else:
            return -1
    else:
        return 1


class MappingColumns:
    """
    This class handles the probabilistic mapping of unknown columns to defined fields. This
    is mainly used in the build_column_mapping API endpoint.
    """

    # TODO: convert dest_columns to mapping_data class instance
    def __init__(self, raw_columns, dest_columns, previous_mapping=None, map_args=None, default_mappings=None, threshold=0):
        """
        :param raw_columns: list of str. The column names we're trying to map.
        :param dest_columns: list of str. The columns we're mapping to.
        :param previous_mapping: Method that contains previous mapped columns

            .. code:

                The expectation is that our callable always gets passed a raw key. If
                it finds a match, it returns the raw_column and score.
                previous_mapping('example field', *map_args) ->
                    ('field_1', 0.93)

        :param map_args: Arguments to pass into the previous_mapping method (e.g., Organization ID)
        :param default_mappings: dict of mappings. Use these mappings if the column is not found in the previous mapping call
        :param threshold: int, Minimum value of the matching confidence to allow for matching.
        :return dict: {'raw_column': ('dest_column', score), 'raw_column_2': ('dest_column_2',...)}
        """
        self.data = {}
        for raw in raw_columns:
            attempt_best_match = False
            # We want previous mappings to be at the top of the list.
            if previous_mapping and callable(previous_mapping):
                args = map_args or []
                # Mapping will look something like this -- ['table', 'field', 100]
                mapping = previous_mapping(raw, *args)
                if mapping:
                    self.add_mappings(raw, [mapping], True)
                elif default_mappings and raw in default_mappings:
                    self.add_mappings(raw, [default_mappings[raw]], True)
                else:
                    attempt_best_match = True
            else:
                attempt_best_match = True

            # Only enter this flow if we haven't already selected a result. Ignore blank columns
            # with conf of 100 since a conf of 100 signifies the user has saved that mapping.
            if attempt_best_match:
                # convert raw fields spaces into underscores because that is what is in the database
                raw_test = raw.replace(" ", "_")

                # try some alternatives to the raw column in specific cases
                # (e.g., zip => postal code). Hack for now, but should make this some global
                # config or organization specific config
                if raw_test.lower() == "zip" or raw_test.lower() == "zip_code":
                    raw_test = "postal_code"
                if raw_test.lower() == "gba":
                    raw_test = "gross_floor_area"
                if raw_test.lower() == "building_address":
                    raw_test = "address_line_1"
                if raw_test.lower() == "ubi":
                    raw_test = "jurisdiction_tax_lot_id"

                matches = matchers.best_match(raw_test, dest_columns, top_n=5)

                # go get the top 5 matches. format will be [('PropertyState', 'building_count', 62), ...]
                self.add_mappings(raw, matches)

        # convert this to an exception and catch it some day.
        index = 0
        while self.duplicates and index < 10:
            index += 1
            _log.debug(f"Index: {index} with duplicates: {self.duplicates}")
            for k, v in self.duplicates.items():
                self.resolve_duplicate(k, v)

        if threshold > 0:
            self.apply_threshold(threshold)

    def add_mappings(self, raw_column, mappings, previous_mapping=False):
        """
        Add mappings to the data structure for later processing.

        :param raw_column: list of strings
        :param mappings: list of tuples of potential mappings and confidences
        :param previous_mapping: boolean, if true these mappings will take precedence
        :return: Bool, whether the mapping was added
        """

        # verify that the raw_column_name does not yet exist, if it does, then return false
        if raw_column in self.data:
            # _log.warn('raw column mapping already exists for {}'.format(raw_column))
            return False

        # if mappings are None or empty, then return false
        if mappings is None or not mappings:
            # _log.warn('there are no mappings for raw column {}'.format(raw_column))
            return False

        self.data[raw_column] = {
            "previous_mapping": previous_mapping,
            "mappings": mappings,
        }
        self.set_initial_mapping_cmp(raw_column)

        return True

    def first_suggested_mapping(self, raw_column):
        """
        Grab the first suggested mapping for a raw column

        :param raw_column: String
        :return: tuple of the mapping ('table', 'field', confidence), or ()
        """

        mappings = self.data[raw_column]["mappings"]
        if mappings and len(mappings) > 0:
            return self.data[raw_column]["mappings"][0]
        else:
            _log.debug(f"There are no suggested mappings for the column {raw_column}, setting to field name")
            return "PropertyState", raw_column, 100

    @property
    def duplicates(self):
        """
        Check for duplicate initial mapping results. Duplicates exist if the first suggested mapping
        for two different raw_columns are the same. The example below would be one of those cases.

        .. example:

            {
                'PropertyState.generation_date': [
                    {'raw_column': 'extra_data_1', 'confidence': 69},
                    {'raw_column': 'extra_data_2', 'confidence': 69}],
                'PropertyState.building_count': [
                    {'raw_column': 'extra_data_1', 'confidence': 69},
                    {'raw_column': 'UBI', 'confidence': 62}
                ]
            }

        :return: List of raw col
        """

        uniques = set()
        duplicates = set()
        result = {}

        for raw_column, v in self.data.items():
            if v["initial_mapping_cmp"] in uniques:
                duplicates.add(v["initial_mapping_cmp"])
            uniques.add(v["initial_mapping_cmp"])

        # now go through and populate the dict with the duplicate keys
        for item in duplicates:
            for raw_column, v in self.data.items():
                if v["initial_mapping_cmp"] == item:
                    if item not in result:
                        result[item] = []
                    result[item].append({"raw_column": raw_column, "confidence": self.first_suggested_mapping(raw_column)[2]})

        return result

    def resolve_duplicate(self, dup_map_field, raw_columns):
        """
        If there are duplicates, that is two raw_columns are trying to map to the same suggested
        column, then select the next available one on the duplicate column. The one with the highest
        confidence will 'win' the duplicate battle.

        :param dup_map_field: String, name of the field that is a duplicate
        :param raw_columns: list, raw columns that mapped to the same result
        :return: None

        """
        _log.debug(f"resolving duplicate field for {dup_map_field}")

        # decide which raw_column should "win"
        raw_columns = sorted(raw_columns, key=cmp_to_key(sort_duplicates))

        # go through all but the first result and remove the first mapping suggestion. There
        # should always be two because it was found as a duplicate.
        for raw in raw_columns[1:]:
            if len(self.data[raw["raw_column"]]["mappings"]) > 0:
                self.data[raw["raw_column"]]["mappings"].pop(0)
            self.set_initial_mapping_cmp(raw["raw_column"])

    def set_initial_mapping_cmp(self, raw_column):
        """
        Set the initial_mapping_cmp helper item in the self.data hash. This is used to detect
        if there are any duplicates. The initial mapping cmp will be the first match in the list
        (i.e., the one with the highest confidence).

        :param raw_column: String, name of the raw column to set the initial_mapping_cmp
        :return: None
        """

        # check if there are any other items left in the mapping suggestions
        if len(self.data[raw_column]["mappings"]) > 0:
            # update the compare string for detecting duplicates -- make method?
            new_map = self.data[raw_column]["mappings"][0]
            # If anyone can figure out why new_map[1] could be a list then I will buy you a burrito
            if new_map[0] is not None and new_map[1] is not None and not isinstance(new_map[1], list):
                self.data[raw_column]["initial_mapping_cmp"] = ".".join([new_map[0], new_map[1]])
            else:
                _log.info("The mappings have a None table or column name")
                self.data[raw_column]["initial_mapping_cmp"] = None
        else:
            # if there are no mappings left, then the mapping suggestion will look like extra data
            # print("Setting set_initial_mapping to None for {}".format(raw_column))
            self.data[raw_column]["initial_mapping_cmp"] = None

    def apply_threshold(self, threshold):
        """
        Remove mapping suggestions that do not meet the defined threshold

        This method is forced as part of the workflow for now, but could easily be made as a
        separate call.

        :param threshold: int, min value to be greater than or equal to.
        :return: None
        """
        for k in self.data:
            # anyone want to convert this to a list comprehension?
            new_mappings = []
            for m in self.data[k]["mappings"]:
                if m[2] >= threshold:
                    new_mappings.append(m)
            self.data[k]["mappings"] = new_mappings
            self.set_initial_mapping_cmp(k)

    @property
    def final_mappings(self):
        """

        Return the final mappings in a format that can be used downstream from this method
        {
            "raw_column_1": ('table', 'db_column_1', confidence),
            "raw_column_2": ('table', 'db_column_1', confidence),
        }

        """
        result = {}
        for k, v in self.data.items():
            result[k] = list(self.first_suggested_mapping(k))

        return result
