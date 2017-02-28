from __future__ import unicode_literals

"""Migration code for the Seed project from the original tables to the
new tables.
"""

import pdb
from IPython import embed
from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
import subprocess
import random
import collections
import datetime
import logging
import itertools
import seed.models
import numpy as np
from scipy.sparse import dok_matrix
from scipy.sparse.csgraph import connected_components
from _localtools import projection_onto_index
from _localtools import get_static_building_snapshot_tree_file
from _localtools import read_building_snapshot_tree_structure
from _localtools import get_core_organizations
from _localtools import get_node_sinks
from _localtools import find_or_create_bluesky_taxlot_associated_with_building_snapshot
from _localtools import find_or_create_bluesky_property_associated_with_building_snapshot
from _localtools import load_organization_property_field_mapping
from _localtools import load_organization_taxlot_field_mapping
from _localtools import _load_raw_mapping_data
from _localtools import get_value_for_key
from _localtools import set_state_value
from _localtools import logging_info
from _localtools import logging_debug

from _localtools import get_taxlot_columns
from _localtools import get_property_columns

from _localtools import USE_FIRST_VALUE

logging.basicConfig(level=logging.DEBUG)

# FIXME: This should get factored out into the soon-to-be class structure of this module.
# Global values for controlling whether or not extra data columns get
# added to the metadata.
ADD_METADATA = True
CURRENT_CANONICAL_BUILDING = False


# These encode rules for how final values
tax_collapse_rules = collections.defaultdict(lambda: {})
tax_collapse_rules[10] = {
    'jurisdiction_tax_lot_id': (
        USE_FIRST_VALUE,
        ['jurisdiction_tax_lot_id', "extra_data/custom_id_1", "extra_data/CS_TaxID2"]
    )
}

property_collapse_rules = collections.defaultdict(lambda: {})


def get_code_version():
    return subprocess.check_output(["git", "describe"]).strip()


def copy_extra_data_excluding(extra_data, bad_fields):
    bad_fields = set(bad_fields)
    return {x: y for (x, y) in extra_data.items() if x not in bad_fields}


def node_has_associated_import_name(node):
    try:
        if node.import_file is not None and node.import_file.file.name:
            return True
        else:
            return False
    except:
        return False


def get_organization_cycle_date(org, node):
    mappings = collections.defaultdict(lambda: collections.defaultdict(lambda : False))
    mappings[69][u'data_imports/BEUDO%20Masterlist%202016_5.16.16.xlsx.1469546768'] = datetime.datetime(2016, 5, 1)
    mappings[69][u'data_imports/PM%20Reports%202015_5.16.16.xlsx.1463604454'] = datetime.datetime(2015, 5, 1)
    mappings[69][u'data_imports/PM%20Reports%202016_8.11.16.xlsx.1471284203'] = datetime.datetime(2016, 5, 1)
    mappings[69][u'data_imports/BEUDO%20Masterlist%202015_5.16.16.xlsx.1463605948'] = datetime.datetime(2015, 5, 1)
    mappings[69][u'data_imports/BEUDO%20Masterlist%202015_5.16.16.xlsx.1463603666'] = datetime.datetime(2015, 5, 1)
    mappings[69][u'data_imports/MIT%20PM%20Reports%202016_9.6.16.xlsx.1473186628']  = datetime.datetime(2016, 5, 1)

    return mappings[org.pk][get_possible_import_filename(node)]


def get_possible_import_filename(node):
    try:
        return str(node.import_file.file.name)
    except:
        return ''


def get_possible_import_notes(node):
    try:
        return str(node.import_file.import_record.notes)
    except:
        return ''
    return


def get_possible_import_user_email(node):
    try:
        return str(node.import_file.import_record.owner.email)
    except:
        return ''


def get_possible_import_time(node):
    try:
        return str(node.import_file.import_record.start_time.strftime("%m-%d-%Y"))
    except:
        return ''


def create_property_state_for_node(node, org, cb):
    property_columns = get_property_columns(org)
    taxlot_columns = get_taxlot_columns(org)

    # Check every key is mapped at least once.
    for key in node.extra_data.keys():
        if key.strip() == '':
            if node.extra_data[key] is not None and node.extra_data[key].strip() != '':
                print "WARNING: key '{}' for organization={} has value={} (cb={})".format(key, org,
                                                                                          node.extra_data[
                                                                                              key],
                                                                                          cb.pk)
            continue

        try:
            assert (key in taxlot_columns or key in property_columns)
        except AssertionError:
            # raise KeyError("Every key must be mapped: '{}'=>'{}' for org={} missing!".format(key, node.extra_data[key], org))
            print "WARNINGXXX: {}".format(KeyError(
                "Every key must be mapped: '{}'=>'{}' for org={} missing!".format(key,
                                                                                  node.extra_data[
                                                                                      key], org)))
            node.extra_data.pop(key)
            continue

    property_state_extra_data = {x: y for (x, y) in node.extra_data.items() if
                                 y in property_columns}
    mapping = load_organization_property_field_mapping(org)

    if ADD_METADATA:
        property_state_extra_data["prop_cb_id"] = cb.pk
        property_state_extra_data["prop_bs_id"] = node.pk

        property_state_extra_data["record_created"] = node.created
        property_state_extra_data["record_modified"] = node.modified
        property_state_extra_data["record_year_ending"] = node.year_ending
        property_state_extra_data["random"] = str(random.random())

        property_state_extra_data["migration_version"] = get_code_version()

    if ADD_METADATA:
        property_state_extra_data["prop_cb_id"] = cb.pk
        property_state_extra_data["prop_bs_id"] = node.pk

        import_filename = get_possible_import_filename(node)
        import_username = get_possible_import_user_email(node)
        import_notes = get_possible_import_notes(node)
        import_time = get_possible_import_time(node)

        property_state_extra_data["import_file"] = import_filename
        property_state_extra_data["import_user"] = import_username
        property_state_extra_data["import_notes"] = import_notes
        property_state_extra_data["import_date"] = import_time

    property_state = seed.models.PropertyState(organization=org,
                                               confidence=node.confidence,
                                               data_state=seed.models.DATA_STATE_MATCHING,
                                               jurisdiction_property_id=None,
                                               lot_number=node.lot_number,
                                               property_name=node.property_name,
                                               address_line_1=node.address_line_1,
                                               address_line_2=node.address_line_2,
                                               city=node.city,
                                               state=node.state_province,
                                               postal_code=node.postal_code,
                                               #building_count=node.building_count,
                                               property_notes=node.property_notes,
                                               use_description=node.use_description,
                                               gross_floor_area=node.gross_floor_area,
                                               year_built=node.year_built,
                                               recent_sale_date=node.recent_sale_date,
                                               conditioned_floor_area=node.conditioned_floor_area,
                                               occupied_floor_area=node.occupied_floor_area,
                                               owner=node.owner,
                                               owner_email=node.owner_email,
                                               owner_telephone=node.owner_telephone,
                                               owner_address=node.owner_address,
                                               owner_city_state=node.owner_city_state,
                                               owner_postal_code=node.owner_postal_code,
                                               pm_property_id=node.pm_property_id,
                                               home_energy_score_id=None,
                                               energy_score=node.energy_score,
                                               site_eui=node.site_eui,
                                               generation_date=node.generation_date,
                                               release_date=node.release_date,
                                               site_eui_weather_normalized=node.site_eui_weather_normalized,
                                               year_ending=node.year_ending,
                                               source_eui=node.source_eui,
                                               energy_alerts=node.energy_alerts,
                                               space_alerts=node.space_alerts,
                                               building_certification=node.building_certification,
                                               extra_data=property_state_extra_data)

    for (field_origin, field_dest) in mapping.items():
        value = get_value_for_key(node, field_origin)
        if value is not None and value != "":
            set_state_value(property_state, field_dest, value)

    property_state.save()
    return property_state


def create_tax_lot_state_for_node(node, org, cb):
    property_columns = get_property_columns(org)
    taxlot_columns = get_taxlot_columns(org)

    # Check every key is mapped at least once.
    for key in node.extra_data:
        if key.strip() == '':
            if node.extra_data[key]:
                print "WARNING: key '{}' for organization={} has value={} (cb={})".format(
                    key, org, node.extra_data[key], cb.pk)
            continue

        try:
            assert (key in taxlot_columns or key in property_columns)
        except AssertionError:
            print "WARNING: Every key must be mapped: '{}'=>'{}' for org={} missing!".format(
                key, node.extra_data[key], org)
            # raise KeyError("Every key must be mapped: '{}'=>'{}' for org={} missing!".format(key, node.extra_data[key], org))

    taxlot_extra_data = {x: y for (x, y) in node.extra_data.items() if y in taxlot_columns}
    mapping = load_organization_taxlot_field_mapping(org)

    if ADD_METADATA:
        taxlot_extra_data["taxlot_cb_id"] = cb.pk
        taxlot_extra_data["taxlot_bs_id"] = node.pk

        taxlot_extra_data["record_created"] = node.created
        taxlot_extra_data["record_modified"] = node.modified
        taxlot_extra_data["record_year_ending"] = node.year_ending
        taxlot_extra_data["random"] = str(random.random())

    if ADD_METADATA:
        import_filename = get_possible_import_filename(node)
        import_username = get_possible_import_user_email(node)
        import_notes = get_possible_import_notes(node)
        import_time = get_possible_import_time(node)

        taxlot_extra_data["import_file"] = import_filename
        taxlot_extra_data["import_user"] = import_username
        taxlot_extra_data["import_notes"] = import_notes
        taxlot_extra_data["import_date"] = import_time

        taxlot_extra_data["taxlot_cb_id"] = cb.pk
        taxlot_extra_data["taxlot_bs_id"] = node.pk

    try:
        filename = node.import_file.file.name
    except:
        filename = "NO FILENAME"

    print filename

    taxlotstate = seed.models.TaxLotState.objects.create(organization=org,
                                                         confidence=node.confidence,
                                                         jurisdiction_tax_lot_id=node.tax_lot_id,
                                                         block_number=node.block_number,
                                                         district=node.district,
                                                         address_line_1=node.address_line_1,
                                                         city=node.city,
                                                         state=node.state_province,
                                                         postal_code=node.postal_code,
                                                         number_properties=node.building_count,
                                                         extra_data=taxlot_extra_data)
    if org.pk == 69:
        taxlotstate.extra_data["Assessors City"] = taxlotstate.city
        taxlotstate.extra_data["Assessors State"] = taxlotstate.state
        taxlotstate.extra_data["Assessors Zip"] = taxlotstate.postal_code


    for (field_origin, field_dest) in mapping.items():
        value = get_value_for_key(node, field_origin)
        if value is not None and value != "":
            set_state_value(taxlotstate, field_dest, value)

    taxlotstate.save()
    return taxlotstate


def is_import(node, org):
    return node.import_file_id is not None


def is_merge(node, org):
    return not is_import(node, org)


MERGE = 0
TAX_IMPORT = 1
PROPERTY_IMPORT = 2
COMBO_IMPORT = 3


def classify_node(node, org):
    if is_merge(node, org):
        return MERGE
    else:
        return classify_import_node(node, org)


def node_has_tax_lot_info(node, org):
    tax_fields = set(
        [x[0] for x in organization_extra_data_mapping[org.id].items() if x[1][0] == "Tax"])
    has_tax_extra_data = len({x: y for x, y in node.extra_data.items() if x in tax_fields and y})
    return bool(node.tax_lot_id is not None or has_tax_extra_data)


def node_has_property_info(node, org):
    # pdb.set_trace()
    # embed()
    property_fields = set(
        [x[0] for x in organization_extra_data_mapping[org.id].items() if x[1][0] == "Property"])

    has_property_extra_data = len(
        {x: y for x, y in node.extra_data.items() if x in property_fields and (y.strip() if isinstance(y, str) else y)})
    return bool(node.pm_property_id is not None or has_property_extra_data)


def classify_import_node(node, org):
    has_tax_lot = node_has_tax_lot_info(node, org)
    has_property = node_has_property_info(node, org)

    assert node.import_file_id is not None, "Thought this was an import node"

    if has_tax_lot and not has_property:
        return TAX_IMPORT
    elif not has_tax_lot and has_property:
        return PROPERTY_IMPORT
    elif has_tax_lot and has_property:
        return COMBO_IMPORT
    else:
        return PROPERTY_IMPORT
        raise Exception("Could not classify import node.")


def load_cycle(org, node, year_ending=True, fallback=True):
    if year_ending:
        time = node.year_ending

        if not fallback:
            assert time is not None, "Got no time!"
        elif time is None:

            time = get_organization_cycle_date(org, node)
            if not time:
                # logging_debug("Node does not have 'year ending' field.")
                time = node.modified
    else:
        if not time:
            time = node.modified

    # FIXME: Refactor.

    # Only Berkeley is allowed
    orgs_allowing_2016 = set([117])
    # if org.pk not in orgs_allowing_2016 and time.year == 2016:
    #     time = datetime.date(2015, 12, 31)

    time = datetime.datetime(year=time.year, month=time.month, day=time.day)

    # TODO: Is this correct?  I like the idea but it appears to have
    # never been used

    # Rules definitions for how to handle ambiguous data.
    remap_year = {}
    remap_year[20] = 2015
    remap_year[7] = 2015
    remap_year[49] = 2015
    remap_year[69] = 2015
    remap_year[10] = 2015
    remap_year[184] = 2015
    remap_year[156] = 2015
    remap_year[117] = 2015
    remap_year[124] = 2015
    remap_year[105] = 2015
    remap_year[126] = 2015
    remap_year[6] = 2015
    remap_year[117] = 2016

    if time.year == 2016 and org.pk in remap_year:
        time = time.replace(year=remap_year[org.pk])

    # This seems like a very inelegant way to handle city specific application rules.

    # For Berkeley if this field is available, we always use it.
    if org.pk == 117 and 'Label Date' in node.extra_data:
        berkeley_datestr = node.extra_data['Label Date']
        try:
            if berkeley_datestr is not None:
                time = datetime.datetime.strptime(berkeley_datestr, "%Y-%m-%d")
        except ValueError:
            pass # Bad value in extra_data; skip it and use the default.


    cycle_start = time.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    cycle_end = cycle_start.replace(year=cycle_start.year + 1) - datetime.timedelta(seconds=1)

    if org.pk in [69, 20]:
        cycle_name = "{} Compliance Year".format(cycle_start.year+1)
    else:
        cycle_name = "{} Calendar Year".format(cycle_start.year)

    cycle, created = seed.models.Cycle.objects.get_or_create(organization=org,
                                                             name=cycle_name,
                                                             start=cycle_start,
                                                             end=cycle_end)
    return cycle


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        parser.add_argument('--limit', dest='limit', default=0, type=int)
        parser.add_argument('--starting_on_canonical', dest='starting_on_canonical', default=0,
                            type=int)
        parser.add_argument('--starting_following_canonical', dest='starting_following_canonical',
                            default=0, type=int)
        parser.add_argument('--no_metadata', dest='add_metadata', default=True,
                            action='store_false')
        parser.add_argument('--cb', dest='cb_whitelist_string', default=False, )
        return

    def handle(self, *args, **options):
        """Migrate the CanonicalBuildings for one or more Organizations into
        the new 'BlueSky' data structures."""

        logging_info("RUN migrate_organization with args={},kwds={}".format(args, options))

        # Process Arguments
        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = get_core_organizations()

        limit = options['limit'] if "limit" in options else 0
        starting_from_canonical = False if not options['starting_on_canonical'] else options[
            'starting_on_canonical']
        starting_on_canonical_following = False if not options['starting_following_canonical'] else \
            options['starting_following_canonical']

        ADD_METADATA = options['add_metadata']

        assert not (
            starting_on_canonical_following and starting_from_canonical), "Can only specify one of --starting_on_canonical and --starting_following_canonical"

        canonical_buildings_whitelist = map(int, options['cb_whitelist_string'].split(",")) if \
            options['cb_whitelist_string'] else False
        # End Processing

        tree_file = get_static_building_snapshot_tree_file()
        m2m = read_building_snapshot_tree_structure(tree_file)

        all_nodes = set(map(projection_onto_index(0), m2m)).union(
            set(map(projection_onto_index(1), m2m)))

        child_dictionary = collections.defaultdict(lambda: set())
        parent_dictionary = collections.defaultdict(lambda: set())

        adj_dim = max(all_nodes) + 1
        adj_matrix = dok_matrix((adj_dim, adj_dim), dtype=np.bool)

        for (from_node, to_node) in m2m:
            adj_matrix[from_node, to_node] = 1
            child_dictionary[from_node].add(to_node)
            parent_dictionary[to_node].add(from_node)

        # Core data struct, possible refactor point.
        all_nodes, child_dictionary, parent_dictionary, adj_matrix

        # We don't care about the total number because
        _, labelarray = connected_components(adj_matrix)

        counts = collections.Counter()
        for label in labelarray: counts[label] += 1

        logging_info("Migration organization: {}".format(",".join(map(str, core_organization))))

        for org_id in core_organization:
            # Writing loop over organizations

            org = Organization.objects.get(pk=org_id)

            logging_info("Processing organization {}".format(org))

            assert org, "Organization {} not found".format(org_id)

            org_canonical_buildings = seed.models.CanonicalBuilding.objects.filter(
                canonical_snapshot__super_organization=org_id, active=True).all()
            org_canonical_snapshots = [cb.canonical_snapshot for cb in org_canonical_buildings]

            # FIXME: Turns out the ids are on Building
            # Snapshot. Leaving it this way because the other code
            # should be displaying canonical building indexes.
            if starting_from_canonical or starting_on_canonical_following:
                # org_canonical_ids = map(lambda x: x.pk, org_canonical_buildings)
                org_canonical_ids = map(lambda x: x.pk, org_canonical_snapshots)
                try:
                    canonical_index = max(starting_from_canonical, starting_on_canonical_following)
                    canonical_index = org_canonical_ids.index(canonical_index)
                    if starting_on_canonical_following: canonical_index += 1

                    org_canonical_buildings = list(org_canonical_buildings)[canonical_index:]
                    org_canonical_snapshots = list(org_canonical_snapshots)[canonical_index:]

                    ref_str = "starting" if starting_from_canonical else "following"

                    logging_info(
                        "Restricting to canonical starting ndx={} (id={}), was {} now {}.".format(
                            canonical_index, len(org_canonical_ids), len(org_canonical_ids),
                            len(org_canonical_buildings)))



                except ValueError:
                    raise RuntimeError(
                        "Requested to start referencing canonical building id={} which was not found.".format(
                            starting_from_canonical))

            if canonical_buildings_whitelist:
                good_canonical_building_indexes = [ndx for (ndx, cb) in
                                                   enumerate(org_canonical_buildings) if
                                                   cb.pk in canonical_buildings_whitelist]
                org_canonical_buildings = [org_canonical_buildings[ndx] for ndx in
                                           good_canonical_building_indexes]
                org_canonical_snapshots = [org_canonical_snapshots[ndx] for ndx in
                                           good_canonical_building_indexes]

                logging_info(
                    "Restricted to {} elements in whitelist.".format(len(org_canonical_buildings)))
                logging_info("IDS: {}".format(
                    ", ".join(map(lambda cs: str(cs.pk), org_canonical_buildings))))

            if canonical_buildings_whitelist:
                good_canonical_building_indexes = [ndx for (ndx, cb) in
                                                   enumerate(org_canonical_buildings) if
                                                   cb.pk in canonical_buildings_whitelist]
                org_canonical_buildings = [org_canonical_buildings[ndx] for ndx in
                                           good_canonical_building_indexes]
                org_canonical_snapshots = [org_canonical_snapshots[ndx] for ndx in
                                           good_canonical_building_indexes]

                logging_info(
                    "Restricted to {} elements in whitelist.".format(len(org_canonical_buildings)))
                logging_info("IDS: {}".format(
                    ", ".join(map(lambda cs: str(cs.pk), org_canonical_buildings))))

            if len(org_canonical_buildings) == 0:
                logging_info("Organization {} has no buildings".format(org_id))
                continue

            last_date = max([cs.modified for cs in org_canonical_snapshots])
            # create_bluesky_cycles_for_org(org, last_date)

            tree_sizes = [counts[labelarray[bs.id]] for bs in org_canonical_snapshots]

            ## For each of those trees find the tip
            ## For each of those trees find the import records
            ## For each of those trees find the cycles associated with it
            for ndx, (cb, bs) in enumerate(zip(org_canonical_buildings, org_canonical_snapshots)):
                if limit and (ndx + 1) > limit:
                    logging_info("Migrated limit={} buildings.".format(limit))
                    logging_info("Skipping remainder of buildings for organization.")
                    break

                logging_info(
                    "Processing Building {}/{}".format(ndx + 1, len(org_canonical_snapshots)))
                bs_label = labelarray[bs.id]
                import_nodes, leaf_nodes, other_nodes = get_node_sinks(bs_label, labelarray,
                                                                       parent_dictionary,
                                                                       child_dictionary)

                # Load all those building snapshots
                tree_nodes = itertools.chain(import_nodes, leaf_nodes, other_nodes)
                building_dict = {bs.id: bs for bs in seed.models.BuildingSnapshot.objects.filter(
                    pk__in=tree_nodes).all()}
                missing_buildings = [node for node in
                                     itertools.chain(import_nodes, leaf_nodes, other_nodes) if
                                     node not in building_dict]

                import_buildingsnapshots = [building_dict[bs_id] for bs_id in import_nodes]
                leaf_buildingsnapshots = [building_dict[bs_id] for bs_id in leaf_nodes]
                assert len(leaf_buildingsnapshots), (
                    "Expected only one leaf of the canonical building family of "
                    "buildings.  Found {}").format(len(leaf_buildingsnapshots))
                leaf = leaf_buildingsnapshots[0]

                other_buildingsnapshots = [building_dict[bs_id] for bs_id in other_nodes]

                logging_info("Creating Blue Sky Data for for CanonicalBuilding={}".format(cb.pk))

                # embed()
                create_associated_bluesky_taxlots_properties(org, import_buildingsnapshots, leaf,
                                                             other_buildingsnapshots,
                                                             child_dictionary, parent_dictionary,
                                                             adj_matrix, cb)
        logging_info("END migrate_organization")
        return


def is_descendant_of(node_1_id, node_2_id, child_dictionary):
    # If node_1 is a descendent of node 2, then node 2 has a path
    # following it's children to node 1 because every node only has
    # one child.
    continue_search = True  # A non-false value definitely not equal to

    while node_2_id:
        node_2_id = child_dictionary[node_2_id]
        node_2_id = next(iter(node_2_id)) if node_2_id else node_2_id
        if node_2_id == node_1_id: return True

    return False


def calculate_generation(node_id, child_dictionary):
    generation = 0

    while node_id:
        generation += 1
        node_id = child_dictionary[node_id]
        if node_id: node_id = next(iter(node_id))

    return generation


def calculate_migration_order(node_list, child_dictionary):
    """Take a list of building snapshots and determine the order they
    should be processed.

    The created/modified flags are not reliable indicators of the tree
    order because nodes are created out of order.

    This calculated an order where n1 < n2 if node n1 is an ancestor of n2.

    Bubble sort on the is_descendant
    """

    for node in node_list:
        assert node.id in child_dictionary

    if len(node_list) <= 1:
        return node_list

    needs_sort = True
    # FIXME: It's probably perfectly safe to copy django objects with
    # their underlying objects but I'm going to be silly and safe.
    orig_id_list = [node.id for node in node_list]
    node_id_list = [node.id for node in node_list]

    node_id_list.sort(key=lambda node_id: calculate_generation(node_id, child_dictionary))

    migration_order = [seed.models.BuildingSnapshot.objects.get(pk=id) for id in node_id_list]

    return migration_order


def create_associated_bluesky_taxlots_properties(org, import_buildingsnapshots, leaf_building,
                                                 other_buildingsnapshots, child_dictionary,
                                                 parent_dictionary, adj_matrix, cb):
    """Take tree structure describing a single Property/TaxLot over time and create the entities."""
    logging_info("Populating new blue sky entities for canonical snapshot tree!")

    print "Processing {}/{}/{}".format(len(import_buildingsnapshots), 1, len(other_buildingsnapshots))

    tax_lot_created = 0
    property_created = 0
    tax_lot_view_created = 0
    property_view_created = 0
    tax_lot_state_created = 0
    property_state_created = 0
    m2m_created = 0

    logging_info("Creating Property/TaxLot from {} nodes".format(
        sum(map(len, ([leaf_building], other_buildingsnapshots, import_buildingsnapshots)))))


    tax_lot = None
    property_obj = None

    leaf_node_type = classify_node(leaf_building, org)

    #if node_has_tax_lot_info(leaf_building, org):
    if leaf_node_type in [TAX_IMPORT, COMBO_IMPORT, MERGE]:
        tax_lot, created = find_or_create_bluesky_taxlot_associated_with_building_snapshot(
            leaf_building, org)
        # tax_lot = seed.models.TaxLot(organization=org)

        tax_lot.save()
        tax_lot_created += int(created)

    # if node_has_property_info(leaf_building, org):
    if leaf_node_type in [PROPERTY_IMPORT, COMBO_IMPORT, MERGE]:
        property_obj, created = find_or_create_bluesky_property_associated_with_building_snapshot(
            leaf_building, org)
        # property_obj = seed.models.Property(organization=org)
        property_obj.save()
        property_created += int(created)

    if not property_obj and not tax_lot:
        property_obj = seed.models.Property(organization=org)
        property_obj.save()
        property_created += 1

    last_taxlot_view = collections.defaultdict(lambda: False)
    last_property_view = collections.defaultdict(lambda: False)

    all_nodes = list(
        itertools.chain(import_buildingsnapshots, other_buildingsnapshots, [leaf_building]))
    all_nodes.sort(key=lambda rec: rec.created)  # Sort from first to last

    x = None
    for ndx, node in enumerate(all_nodes):

        # if node.pk == leaf_building.pk:
        #     pdb.set_trace()

        node_type = classify_node(node, org)
        if node_type == TAX_IMPORT or node_type == COMBO_IMPORT or node_type == MERGE:
            # Get the cycle associated with the node
            import_cycle = load_cycle(org, node)
            if import_cycle.start.year == 2015: x = import_cycle

            # print "Node {} cycle is {} with address {}, {}".format(node, import_cycle, node.extra_data['Building Address'] if 'Building Address' in node.extra_data.keys() else "NONE", node.gross_floor_area)
            tax_lot_state = create_tax_lot_state_for_node(node, org, cb)
            tax_lot_state_created += 1

            query = seed.models.TaxLotView.objects.filter(taxlot=tax_lot, cycle=import_cycle)
            if query.count():
                taxlotview = query.first()
                taxlotview.update_state(tax_lot_state, name="Merge current state in migration")
                taxlotview.save()
            else:
                taxlotview, created = seed.models.TaxLotView.objects.get_or_create(taxlot=tax_lot,
                                                                                   cycle=import_cycle,
                                                                                   state=tax_lot_state)
                tax_lot_view_created += int(created)
                assert created, "Should have created a tax lot."
                taxlotview.save()

            last_taxlot_view[taxlotview.cycle] = taxlotview

        if node_type == PROPERTY_IMPORT or node_type == COMBO_IMPORT or node_type == MERGE:
            import_cycle = load_cycle(org, node)
            property_state = create_property_state_for_node(node, org, cb)

            # if import_cycle.start.year == 2015:
            #     print property_state.extra_data['Building Address']

            property_state_created += 1

            query = seed.models.PropertyView.objects.filter(property=property_obj,
                                                            cycle=import_cycle)
            if query.count():
                propertyview = query.first()
                propertyview.update_state(property_state, name="Merge current state in migration")
                propertyview.save()
            else:
                propertyview, created = seed.models.PropertyView.objects.get_or_create(
                    property=property_obj, cycle=import_cycle, state=property_state)
                assert created, "Should have created something"
                property_view_created += int(created)
                propertyview.save()
            last_property_view[propertyview.cycle] = propertyview

        if node_type == MERGE or node_type == COMBO_IMPORT:
            m2m_cycle = load_cycle(org, node)
            if last_property_view[m2m_cycle] and last_taxlot_view[m2m_cycle]:

                if node_type == MERGE:
                    # Check to make sure the last stuff created is
                    # associated with the same cycle as the merge.
                    assert last_property_view[m2m_cycle], "Didn't expect NO proeprty view"
                    assert last_taxlot_view[m2m_cycle], "Didn't expect NO tax lot view"

                    # # FIXME - bad logic
                    # if m2m_cycle != last_property_view[cycle].cycle:
                    #     # Ultimately Copy the state over to a new state
                    #     last_property_view, _ = seed.models.PropertyView.objects.get_or_create(property=property_obj, cycle=m2m_cycle, state=last_property_view.state)
                    # if m2m_cycle != last_taxlot_view.cycle:
                    #     last_taxlot_view, _ = seed.models.TaxLotView.objects.get_or_create(taxlot=tax_lot, cycle=m2m_cycle, state=last_taxlot_view.state)

                    # assert m2m_cycle == last_taxlot_view.cycle == last_property_view.cycle, "Why aren't all these equal?!"


                    tlp, created = seed.models.TaxLotProperty.objects.get_or_create(
                        property_view=last_property_view[m2m_cycle],
                        taxlot_view=last_taxlot_view[m2m_cycle],
                        cycle=m2m_cycle)
                    m2m_created += int(created)

            else:

                import_cycle = load_cycle(org, node)

                # Treat it like an import.
                if node_has_tax_lot_info(node, org):
                    tax_lot_state = create_tax_lot_state_for_node(node, org, cb)
                    tax_lot_state_created += 1

                    # Check if there is a TaxLotView Present
                    taxlotview, created = seed.models.TaxLotView.objects.update_or_create(
                        taxlot=tax_lot, cycle=import_cycle, defaults={"state": tax_lot_state})
                    tax_lot_view_created += int(created)

                    taxlotview.save()
                    last_taxlot_view[taxlotview.cycle] = taxlotview

                if node_has_property_info(node, org):
                    property_state = create_property_state_for_node(node, org, cb)
                    property_state_created += 1

                    propertyview, created = seed.models.PropertyView.objects.update_or_create(
                        property=property_obj, cycle=import_cycle,
                        defaults={"state": property_state})
                    property_view_created += int(created)

                    propertyview.save()
                    last_property_view[propertyview.cycle] = propertyview

                if node_has_tax_lot_info(node, org) and node_has_property_info(node, org):
                    _, created = seed.models.TaxLotProperty.objects.get_or_create(
                        property_view=last_property_view[import_cycle],
                        taxlot_view=last_taxlot_view[import_cycle],
                        cycle=import_cycle)
                    m2m_created += int(created)
                # print "{}: {}".format(ndx, last_taxlot_view[x].state.extra_data["Building Address"] if "Building Address" in last_taxlot_view[x].state.extra_data.keys() else last_taxlot_view[x].state.extra_data.keys())
            a = 10

    logging_info(
        "{} Tax Lot, {} Property, {} TaxLotView, {} PropertyView, {} TaxLotState, {} PropertyState, {} m2m created.".format(
            tax_lot_created,
            property_created,
            tax_lot_view_created,
            property_view_created,
            tax_lot_state_created,
            property_state_created,
            m2m_created))
    return

# FIXME: Remove this global variable
organization_extra_data_mapping, _ = _load_raw_mapping_data()
