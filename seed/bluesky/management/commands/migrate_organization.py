from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from django.apps import apps
import pdb
import copy
import collections
import os
import datetime
import logging
import itertools
import csv
import StringIO
from IPython import embed
import seed.bluesky.models
import numpy as np
from scipy.sparse import dok_matrix
from scipy.sparse.csgraph import connected_components
from _localtools import projection_onto_index
from _localtools import get_static_building_snapshot_tree_file
from _localtools import get_static_extradata_mapping_file
from _localtools import read_building_snapshot_tree_structure
from _localtools import get_core_organizations
from _localtools import get_node_sinks

logging.basicConfig(level=logging.DEBUG)


def find_or_create_bluesky_taxlot_associated_with_building_snapshot(bs, org):
    desired_field_mapping = load_organization_taxlot_field_mapping(org)
    reverse_mapping = {y:x for x,y in desired_field_mapping.items()}

    bs_taxlot_val = bs.tax_lot_id
    if ('jurisdiction_taxlot_identifier' in reverse_mapping and reverse_mapping['jurisdiction_taxlot_identifier'] in bs.extra_data):
        bs_taxlot_val = bs.extra_data[reverse_mapping['jurisdiction_taxlot_identifier']]

    if bs_taxlot_val is None:
        tax_lot = seed.bluesky.models.TaxLot(organization=org)
        tax_lot.save()
        return tax_lot, True


    qry = seed.bluesky.models.TaxLotView.objects.filter(state__jurisdiction_taxlot_identifier=bs_taxlot_val)

    # See if we have any tax lot views that have tax lot states
    # with that id, if yes, find/return associated property.

    if qry.count():
        print "HAHA: Found a match!"
        return qry.first().taxlot, False

    else:
        tax_lot = seed.bluesky.models.TaxLot(organization=org)
        tax_lot.save()
        return tax_lot, True


def find_or_create_bluesky_property_associated_with_building_snapshot(bs, org):
    mapping_field = 'building_portfolio_manager_identifier'


    desired_field_mapping = load_organization_property_field_mapping(org)
    reverse_mapping = {y:x for x,y in desired_field_mapping.items()}
    bs_property_id = bs.pm_property_id
    if (mapping_field in reverse_mapping and reverse_mapping[mapping_field] in bs.extra_data):
        bs_property_id = bs.extra_data[reverse_mapping[mapping_field]]

    if bs_property_id is None:
        property = seed.bluesky.models.Property(organization=org)
        property.save()
        return property, True

    qry = seed.bluesky.models.PropertyView.objects.filter(state__building_portfolio_manager_identifier=bs_property_id)

    if qry.count():
        print "HOHO: Found a property match"
        return qry.first().property, False
    else:
        property = seed.bluesky.models.Property(organization=org)
        property.save()
        return property, True

def copy_extra_data_excluding(extra_data, bad_fields):
    bad_fields = set(bad_fields)
    return {x:y for (x,y) in extra_data.items() if x not in bad_fields}


def create_property_state_for_node(node, org):

    dont_include_fields = load_organization_property_extra_data_mapping_exclusions(org)

    extra_data_copy = copy_extra_data_excluding(node.extra_data, dont_include_fields)

    extra_data_copy["record_created"] = node.created
    extra_data_copy["record_modified"] = node.modified
    extra_data_copy["record_year_ending"] = node.year_ending


    desired_field_mapping = load_organization_property_field_mapping(org)
    premapped_data = {}

    for key in desired_field_mapping:
        if key in extra_data_copy:
            premapped_data[key] = extra_data_copy[key]
            extra_data_copy.pop(key)

    property_state = seed.bluesky.models.PropertyState(confidence = node.confidence,
                                                       jurisdiction_property_identifier = None,
                                                       lot_number = node.lot_number,
                                                       property_name = node.property_name,
                                                       address_line_1 = node.address_line_1,
                                                       address_line_2 = node.address_line_2,
                                                       city = node.city,
                                                       state = node.state_province,
                                                       postal_code = node.postal_code,
                                                       building_count = node.building_count,
                                                       property_notes = node.property_notes,
                                                       use_description = node.use_description,
                                                       gross_floor_area = node.gross_floor_area,
                                                       year_built = node.year_built,
                                                       recent_sale_date = node.recent_sale_date,
                                                       conditioned_floor_area = node.conditioned_floor_area,
                                                       occupied_floor_area = node.occupied_floor_area,
                                                       owner = node.owner,
                                                       owner_email = node.owner_email,
                                                       owner_telephone = node.owner_telephone,
                                                       owner_address = node.owner_address,
                                                       owner_city_state = node.owner_city_state,
                                                       owner_postal_code = node.owner_postal_code,
                                                       building_portfolio_manager_identifier = node.pm_property_id,
                                                       building_home_energy_score_identifier = None,
                                                       energy_score = node.energy_score,
                                                       site_eui = node.site_eui,
                                                       generation_date = node.generation_date,
                                                       release_date = node.release_date,
                                                       site_eui_weather_normalized = node.site_eui_weather_normalized,
                                                       source_eui = node.source_eui,
                                                       energy_alerts = node.energy_alerts,
                                                       space_alerts = node.space_alerts,
                                                       building_certification = node.building_certification,
                                                       extra_data = extra_data_copy)


    for (field_to_move, value) in premapped_data.items():
        setattr(property_state, desired_field_mapping[field_to_move], value)

    property_state.save()

    return property_state


def create_tax_lot_state_for_node(node, org):
    dont_include_fields = [x[0] for x in organization_extra_data_mapping[org.id].items() if x[1][0] != "Tax"]
    extra_data_copy = copy_extra_data_excluding(node.extra_data, dont_include_fields)

    extra_data_copy["record_created"] = node.created
    extra_data_copy["record_modified"] = node.modified
    extra_data_copy["record_year_ending"] = node.year_ending


    desired_field_mapping = load_organization_taxlot_field_mapping(org)
    premapped_data = {}

    for key in desired_field_mapping:
        if key in extra_data_copy:
            premapped_data[key] = extra_data_copy[key]
            extra_data_copy.pop(key)

    taxlotstate = seed.bluesky.models.TaxLotState.objects.create(confidence = node.confidence,
                                                                 jurisdiction_taxlot_identifier = node.tax_lot_id,
                                                                 block_number = node.block_number,
                                                                 district = node.district,
                                                                 address = node.address_line_1,
                                                                 city = node.city,
                                                                 state = node.state_province,
                                                                 postal_code = node.postal_code,
                                                                 number_properties = node.building_count,
                                                                 extra_data = extra_data_copy)

    for (field_to_move, value) in premapped_data.items():
        setattr(taxlotstate, desired_field_mapping[field_to_move], value)

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
    tax_fields = set([x[0] for x in organization_extra_data_mapping[org.id].items() if x[1][0] == "Tax"])
    has_tax_extra_data = len({x:y for x,y in node.extra_data.items() if x in tax_fields and y})
    return bool(node.tax_lot_id is not None or has_tax_extra_data)

def node_has_property_info(node, org):
    property_fields = set([x[0] for x in organization_extra_data_mapping[org.id].items() if x[1][0] == "Property"])
    has_property_extra_data = len({x:y for x,y in node.extra_data.items() if x in property_fields and y})
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

def load_cycle(org, node, year_ending = True, fallback = True):
    if year_ending:
        time = node.year_ending

        if not fallback:
            assert time is not None, "Got no time!"
        elif time is None:
            logging.warning("Node does not have 'year ending' field.")
            time = node.modified
    else:
        time = node.modified


    time = datetime.datetime(year = time.year, month=time.month, day = time.day)
    try:
        cycle_start = time.replace(month = 1, day = 1, hour = 0, minute = 0, second = 0, microsecond = 0)
        cycle_end = cycle_start.replace(year=cycle_start.year+1)-datetime.timedelta(seconds = 1)
    except:
        pdb.set_trace()

    cycle, created = seed.bluesky.models.Cycle.objects.get_or_create(organization=org,
                                                                     name = "{} Calendar Year".format(cycle_start.year),
                                                                     start = cycle_start,
                                                                     end = cycle_end)
    return cycle

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        parser.add_argument('--limit', dest='limit', default=0, type=int)
        return

    def handle(self, *args, **options):
        """Do something."""

        tree_file = get_static_building_snapshot_tree_file()
        m2m = read_building_snapshot_tree_structure(tree_file)

        all_nodes = set(map(projection_onto_index(0), m2m)).union(set(map(projection_onto_index(1), m2m)))
        child_dictionary = collections.defaultdict(lambda : set())
        parent_dictionary = collections.defaultdict(lambda : set())

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

        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = get_core_organizations()

        limit = options['limit'] if "limit" in options else 0

        print "Migration organization: {}".format(",".join(map(str, core_organization)))

        for org_id in core_organization:
            # Writing loop over organizations

            org = Organization.objects.filter(pk=org_id).first()
            logging.info("Processing organization {}".format(org))

            assert org, "Organization {} not found".format(org_id)

            org_canonical_buildings = seed.models.CanonicalBuilding.objects.filter(canonical_snapshot__super_organization=org_id, active=True).all()
            org_canonical_snapshots = [cb.canonical_snapshot for cb in org_canonical_buildings]

            if len(org_canonical_buildings) == 0:
                print "Organization {} has no buildings".format(org_id)
                continue


            last_date = max([cs.modified for cs in org_canonical_snapshots])
            # create_bluesky_cycles_for_org(org, last_date)

            tree_sizes = [counts[labelarray[bs.id]] for bs in org_canonical_snapshots]

            ## For each of those trees find the tip
            ## For each of those trees find the import records
            ## For each of those trees find the cycles associated with it
            print len(map(lambda x: x.id, org_canonical_snapshots))
            print len(set(map(lambda x: x.id, org_canonical_snapshots)))

            for ndx, bs in enumerate(org_canonical_snapshots):

                if limit and (ndx+1) > limit:
                    print "That's enough!"
                    break

                print "Processing Building {}/{}".format(ndx+1, len(org_canonical_snapshots))
                bs_label = labelarray[bs.id]
                # print "Label is {}".format(bs_label)
                import_nodes, leaf_nodes, other_nodes  = get_node_sinks(bs_label, labelarray, parent_dictionary, child_dictionary)

                # Load all those building snapshots
                tree_nodes = itertools.chain(import_nodes, leaf_nodes, other_nodes)
                building_dict = {bs.id: bs for bs in seed.models.BuildingSnapshot.objects.filter(pk__in=tree_nodes).all()}
                missing_buildings = [node for node in itertools.chain(import_nodes, leaf_nodes, other_nodes) if node not in building_dict]

                import_buildingsnapshots = [building_dict[bs_id] for bs_id in import_nodes]
                leaf_buildingsnapshots = [building_dict[bs_id] for bs_id in leaf_nodes]
                other_buildingsnapshots = [building_dict[bs_id] for bs_id in other_nodes]

                print "Creating snapshot for {}".format(leaf_buildingsnapshots[0])

                create_associated_bluesky_taxlots_properties(org, import_buildingsnapshots, leaf_buildingsnapshots, other_buildingsnapshots, child_dictionary, parent_dictionary, adj_matrix)
        return


def create_associated_bluesky_taxlots_properties(org, import_buildingsnapshots, leaf_buildingsnapshots, other_buildingsnapshots, child_dictionary, parent_dictionary, adj_matrix):
    """Take tree structure describing a single Property/TaxLot over time and create the entities."""
    logging.info("Creating a new entity thing-a-majig!")

    tax_lot_created = 0
    property_created = 0
    tax_lot_view_created = 0
    property_view_created = 0
    tax_lot_state_created = 0
    property_state_created = 0
    m2m_created =  0

    logging.info("Creating Property/TaxLot from {} nodes".format( sum(map(len, (leaf_buildingsnapshots, other_buildingsnapshots, import_buildingsnapshots)))))

    all_nodes = list(itertools.chain(import_buildingsnapshots, leaf_buildingsnapshots, other_buildingsnapshots))
    all_nodes.sort(key = lambda rec: rec.created)

    tax_lot = None
    property_obj = None

    if node_has_tax_lot_info(leaf_buildingsnapshots[0], org):
        tax_lot, created = find_or_create_bluesky_taxlot_associated_with_building_snapshot(leaf_buildingsnapshots[0], org)
        # tax_lot = seed.bluesky.models.TaxLot(organization=org)
        tax_lot.save()
        tax_lot_created += int(created)

    if node_has_property_info(leaf_buildingsnapshots[0], org):
        property_obj, created = find_or_create_bluesky_property_associated_with_building_snapshot(leaf_buildingsnapshots[0], org)
        # property_obj = seed.bluesky.models.Property(organization=org)
        property_obj.save()
        property_created += int(created)

    if not property_obj and not tax_lot:
        property_obj = seed.bluesky.models.Property(organization=org)
        property_obj.save()
        property_created += 1

    last_taxlot_view = False
    last_property_view = False

    for node in all_nodes:
        node_type = classify_node(node, org)

        if node_type == TAX_IMPORT or node_type == COMBO_IMPORT:
            # Get the cycle associated with the node

            # pdb.set_trace()
            import_cycle = load_cycle(org, node)
            tax_lot_state = create_tax_lot_state_for_node(node, org)
            tax_lot_state_created += 1

            query = seed.bluesky.models.TaxLotView.objects.filter(taxlot=tax_lot, cycle=import_cycle)
            if query.count():
                taxlotview = query.first()
                taxlotview.state = tax_lot_state
                taxlotview.save()
            else:
                taxlotview, created = seed.bluesky.models.TaxLotView.objects.get_or_create(taxlot=tax_lot, cycle=import_cycle, state=tax_lot_state)
                tax_lot_view_created += int(created)
                assert created, "Should have created a tax lot."
                taxlotview.save()
            last_taxlot_view = taxlotview
        elif node_type == PROPERTY_IMPORT or node_type == COMBO_IMPORT:
            import_cycle = load_cycle(org, node)
            property_state = create_property_state_for_node(node, org)
            property_state_created += 1


            query = seed.bluesky.models.PropertyView.objects.filter(property=property_obj, cycle=import_cycle)
            if query.count():
                property_view = query.first()
                property_view.state = property_state
                property_view.save()
            else:
                try:
                    propertyview, created = seed.bluesky.models.PropertyView.objects.get_or_create(property=property_obj, cycle=import_cycle, state=property_state)
                except Exception, xcpt:
                    pdb.set_trace()
                assert created, "Should have created something"
                property_view_created += int(created)
                propertyview.save()
            last_property_view = propertyview

        if node_type == MERGE or node_type == COMBO_IMPORT:
            if last_property_view and last_taxlot_view:
                m2m_cycle = load_cycle(org, node)

                if node_type == MERGE:
                    # Check to make sure the last stuff created is
                    # associated with the same cycle as the merge.
                    assert last_property_view, "Didn't expect NO proeprty view"
                    assert last_taxlot_view, "Didn't expect NO tax lot view"

                    if m2m_cycle != last_property_view:
                        # Ultimately Copy the state over to a new state
                        last_property_view, _ = seed.bluesky.models.PropertyView.objects.get_or_create(property=property_obj, cycle=m2m_cycle, state=last_property_view.state)
                    if m2m_cycle != last_taxlot_view:
                        last_taxlot_view, _ = seed.bluesky.models.TaxLotView.objects.get_or_create(taxlot=tax_lot, cycle=m2m_cycle, state=last_taxlot_view.state)

                    assert m2m_cycle == last_taxlot_view.cycle == last_property_view.cycle, "Why aren't all these equal?!"


                    tlp, created  = seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = last_property_view,
                                                                                             taxlot_view = last_taxlot_view,
                                                                                             cycle = m2m_cycle)
                    m2m_created += int(created)

            else:
                # Treat it like an import.
                if node_has_tax_lot_info(node, org):
                    import_cycle = load_cycle(org, node)
                    tax_lot_state = create_tax_lot_state_for_node(node, org)
                    tax_lot_state_created += 1

                    taxlotview, created = seed.bluesky.models.TaxLotView.objects.update_or_create(taxlot=tax_lot, cycle=import_cycle, defaults={"state": tax_lot_state})
                    tax_lot_view_created += int(created)

                    taxlotview.save()
                    last_taxlot_view = taxlotview
                if node_has_property_info(node, org):
                    import_cycle = load_cycle(org, node)
                    property_state = create_property_state_for_node(node, org)
                    property_state_created += 1

                    propertyview, created = seed.bluesky.models.PropertyView.objects.update_or_create(property=property_obj, cycle=import_cycle, defaults={"state": property_state})
                    property_view_created += int(created)

                    propertyview.save()
                    last_property_view = propertyview


    logging.info("{} Tax Lot, {} Property, {} TaxLotView, {} PropertyView, {} TaxLotState, {} PropertyState, {} m2m created.".format(tax_lot_created,
                                                                                                                                     property_created,
                                                                                                                                     tax_lot_view_created,
                                                                                                                                     property_view_created,
                                                                                                                                     tax_lot_state_created,
                                                                                                                                     property_state_created,
                                                                                                                                     m2m_created))
    return


def load_organization_field_mapping_for_type_exclusions(org, type):
    assert type in ["Tax", "Property"]

    data = load_raw_mapping_data()

    remove_from_extra_data_mapping = []

    for key in data[org]:
        (table, column) = data[org][key]

        if (table != type):
            remove_from_extra_data_mapping.append(key)

    return remove_from_extra_data_mapping


def load_organization_field_mapping_for_type(org, type):
    """This returns a list of keys -> (table, attr) to map the key into."""
    data = load_raw_mapping_data()

    mapping = {}
    for column in data[org].keys():
        table, dest_column = data[org][column]
        if table == type and dest_column != "extra_data":
            mapping[column] = dest_column

    return mapping


def load_organization_property_extra_data_mapping_exclusions(org):
    return load_organization_field_mapping_for_type_exclusions(org.pk, "Property")

def load_organization_taxlot_extra_data_mapping_exclusions(org):
    return load_organization_field_mapping_for_type_exclusions(org.pk, "Tax")

def load_organization_property_field_mapping(org):
    """This returns a list of keys -> (table, attr) to map the key into."""
    return load_organization_field_mapping_for_type(org.pk, "Property")

def load_organization_taxlot_field_mapping(org):
    """This returns a list of keys -> (table, attr) to map the key into."""
    return load_organization_field_mapping_for_type(org.pk, "Tax")


def load_raw_mapping_data():
    # pdb.set_trace()
    fl = open(get_static_extradata_mapping_file()).readlines()

    fl = filter(lambda x: x.startswith("1,"), fl)

    d = collections.defaultdict(lambda : {})
    reader = csv.reader(StringIO.StringIO("".join(fl)))
    for r in reader:
        org_str, key_name, table, field = r[1:5]
        d[int(org_str)][key_name] = (table, field)

    return d



organization_extra_data_mapping = load_raw_mapping_data()
