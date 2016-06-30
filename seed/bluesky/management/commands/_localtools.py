import os
import pdb
import itertools
import csv
import StringIO
import collections
import seed.bluesky.models
from seed.bluesky.models import TaxLotView


def get_core_organizations():
    # IDs of the 12 organizations defined by robin 6/6/16.
    # Google Doc for file describing this:
    # https://docs.google.com/document/u/4/d/1z1FScU-lysmgkCNGa9-hH0PCQudpzV_IG2IKcxYzyfM/edit
    # [69,20,156,49,7,10,181,117,105,126, 124,6]
    GOOD_ORGS = [20, 7, 49, 69, 10, 21, 156, 117, 124, 105, 126]
    assert len(GOOD_ORGS) == 12
    return GOOD_ORGS


def projection_onto_index(n):
    """Return function that returns the nth value for a vector."""
    def projection_func(vect): return vect[n]
    return projection_func

def get_static_extradata_mapping_file():
    management_file_directory = os.path.split(__file__)[0]
    extradata_file = os.path.join(management_file_directory, "extradata.csv")
    return extradata_file

def get_static_building_snapshot_tree_file():
    management_file_directory = os.path.split(__file__)[0]
    tree_file = os.path.join(management_file_directory, "tree_file.csv")
    return tree_file

def read_building_snapshot_tree_structure(input_file):
    with open(input_file) as tree_file:
        l = tree_file.readline() # Header
        assert l.startswith("id")

        z = lambda line: map(int, line.split(',')[1:])
        m2m = map(z, tree_file.readlines())
    return m2m



def find_matching_values_linear(array, val):
    results = []
    for (ndx, array_val) in enumerate(array):
        if array_val == val: results.append(ndx)
    return set(results)



def get_node_sinks(tree_label, labelarray, parent_adj_dict, child_adj_dict):
    label_nodes = find_matching_values_linear(labelarray, tree_label)

    import_nodes = filter(lambda node_ndx: len(parent_adj_dict[node_ndx]) == 0, label_nodes)
    leaf_nodes = filter(lambda node_ndx: len(child_adj_dict[node_ndx]) == 0, label_nodes)
    other_nodes = [x for x in label_nodes if x not in import_nodes and x not in leaf_nodes]

    # print "import_nodes({}): {}".format(len(import_nodes), import_nodes)
    # print "leaf_nodes({}): {}".format(len(leaf_nodes), leaf_nodes)
    # print "other_nodes({}): {}".format(len(other_nodes), other_nodes)
    return import_nodes, leaf_nodes, other_nodes


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
        return qry.first().property, False
    else:
        property = seed.bluesky.models.Property(organization=org)
        property.save()
        return property, True



def load_organization_field_mapping_for_type_exclusions(org, type):
    assert type in ["Tax", "Property"]

    data, _ = _load_raw_mapping_data()

    remove_from_extra_data_mapping = []

    # custom_not_explicitly_mapped = "custom_id_1" not in data[org]

    for key in data[org]:
        (table, column) = data[org][key]
        if (table != type):
            remove_from_extra_data_mapping.append(key)

    # if (custom_not_explicitly_mapped):
    #     remove_from_extra_data_mapping.append("custom_id_1")

    # FIXME: Tired.  Can't figure out this super-basic logic.  Taking
    # a fairly harmless conservative state for now.  We just make sure
    # it goes everywhere.
    remove_from_extra_data_mapping = filter(lambda x: x != "custom_id_1", remove_from_extra_data_mapping)
    return remove_from_extra_data_mapping


def load_organization_field_mapping_for_type(org, type):
    """This returns a list of keys -> (table, attr) to map the key into."""
    data, _ = _load_raw_mapping_data()

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


def get_organization_map_custom():
    _, org_map_custom = _load_raw_mapping_data()
    return org_map_custom

def _load_raw_mapping_data():
    # pdb.set_trace()
    fl = open(get_static_extradata_mapping_file()).readlines()

    fl = filter(lambda x: x.startswith("1,"), fl)

    d = collections.defaultdict(lambda : {})
    reader = csv.reader(StringIO.StringIO("".join(fl)))

    org_map_custom_id = collections.defaultdict(lambda : False)

    for r in reader:
        org_str, is_explicit_field, key_name, table, field = r[1:6]

        if is_explicit_field and int(is_explicit_field) == 1:
            org_map_custom_id[int(org_str)] = (table, field)

        if not is_explicit_field or not int(is_explicit_field):
            d[int(org_str)][key_name] = (table, field)

    return d, is_explicit_field
