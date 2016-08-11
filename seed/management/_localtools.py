import os
import pdb
import itertools
import csv
import StringIO
import collections
import re
from IPython import embed
import seed.models
from seed.models import TaxLotView


class TaxLotIDValueError(ValueError):
    def __init__(self, original_string, field = None):
        super(TaxLotIDValueError, self).__init__("Invalid id string found: {}".format(original_string))
        self.invalid_field = field
        self.original_string = original_string
        return


def get_core_organizations():
    # IDs of the 12 organizations defined by robin 6/6/16.
    # Google Doc for file describing this:
    # https://docs.google.com/document/u/4/d/1z1FScU-lysmgkCNGa9-hH0PCQudpzV_IG2IKcxYzyfM/edit
    # [69,20,156,49,7,10,181,117,105,126, 124,6]
    GOOD_ORGS = [20, 7, 49, 69, 10, 181, 156, 117, 124, 105, 126, 6]
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

    resolution_list = []
    if "jurisdiction_taxlot_identifier" in reverse_mapping: resolution_list.append(reverse_mapping["jurisdiction_taxlot_identifier"])
    resolution_list.append("tax_lot_id")

    bs_taxlot_val = aggregate_value_from_state(bs, (USE_FIRST_VALUE, resolution_list))

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

    # FIX ME - This needs to be updated to simply search on the field and be given a rule.

    desired_field_mapping = load_organization_property_field_mapping(org)
    reverse_mapping = {y:x for x,y in desired_field_mapping.items()}


    resolution_list = []
    if mapping_field in reverse_mapping: resolution_list.append(reverse_mapping[mapping_field])
    resolution_list.append("pm_property_id")

    bs_property_id = aggregate_value_from_state(bs, (USE_FIRST_VALUE, resolution_list))

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

def load_organization_field_mapping_for_type(org_id, type):
    """This returns a list of keys -> (table, attr) to map the key into."""

    org_mapping_line = "1,{}".format(org_id)

    fl = open(get_static_extradata_mapping_file()).readlines()
    fl = filter(lambda x: x.startswith(org_mapping_line), fl)
    reader = csv.reader(StringIO.StringIO("".join(fl)))

    field_mapping = collections.defaultdict(lambda : collections.defaultdict(lambda : False))

    for r in reader:
        org_str, is_explicit_field, key_name, table, field = r[1:6]
        if table != type: continue

        from_field = key_name if is_explicit_field else "extra_data/{}".format(key_name)

        # Note this implies you can remap extra_data->extra data by calling it extra_data/remap"
        to_field = "extra_data/{}".format(key_name) if field == "extra_data" else field
        field_mapping[from_field] = to_field

    return field_mapping


def load_organization_property_extra_data_mapping_exclusions(org):
    return load_organization_field_mapping_for_type_exclusions(org.pk, "Property")

def load_organization_taxlot_extra_data_mapping_exclusions(org):
    return load_organization_field_mapping_for_type_exclusions(org.pk, "Tax")

def load_organization_property_field_mapping(org):
    return load_organization_field_mapping_for_type(org.pk, "Property")

def load_organization_taxlot_field_mapping(org):
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


def valid_id(s):
    #pattern = r"[\w\-\s]+$"
    if len(s) == 1:
        #trying to do the case where the string is only one character was too complicated
        #so just do it separate for now
        pattern = r"\w"
    else:
        #Rules for individual field:
        #Must start and end with alphanumeric (\w)
        #May have any combination of whitespace, hyphens ("-") and alphanumerics in the middle
        pattern = r"\w[\w\-\s]*\w$"
    return re.match(pattern, s)

def sanitize_delimiters(s, delimiter_to_use, other_delimiters):
    """Replace all delimiters with preferred delimiter"""
    for d in other_delimiters:
        s = s.replace(d, delimiter_to_use)
    return s

def check_delimiter_sanity(check_str, delimiters):
    """Ensure that only one kind of delimiter is used."""
    return map(lambda delim: delim in check_str, delimiters).count(True) <= 1

def get_id_fields(parse_string):
    """Parse a string into a list of taxlots.

    Raises an exception if string does not match
    """

    if parse_string is None: raise TaxLotIDValueError(parse_string)

    #The id field can use any of several delimiters so reduce it to just one
    #delimiter first to make things easier
    delimiter_to_use = ","
    other_delimiters = [";", ":"]

    if not check_delimiter_sanity(parse_string, [delimiter_to_use] + other_delimiters):
        raise TaxLotIDValueError(parse_string)


    cleaned_str = sanitize_delimiters(parse_string, delimiter_to_use, other_delimiters)

    #If there is nothing in the string return an empty list
    if not len(cleaned_str.strip()):
        return []

    fields = cleaned_str.split(delimiter_to_use)
    #leading and trailing whitespace is part of the delimiter and not the ids
    #so remove it here before additional processing
    fields = [f.strip() for f in fields]

    for field in fields:
        if not valid_id(field):
            raise TaxLotIDValueError(parse_string, field)

    return fields


def set_state_value(state, field_string, value):
    ed = "extra_data/"
    if field_string.startswith(ed):
        ed_key = field_string[len(ed):]
        state.extra_data[ed_key] = value
        return
    else:
        assert hasattr(state, field_string), "{} should have an explicit field named {} but does not.".format(field_string)
        setattr(state, field_string, value)
    return


def get_value_for_key(state, field_string):
    ed = "extra_data/"
    if field_string.startswith(ed):
        key = field_string[len(ed):] if ed in field_string else ""

        if key not in state.extra_data:
            return None
        else:
            value = state.extra_data[key]
            if value is None: return None

            # FIXME: Gross.
            if isinstance(value, unicode):
                value = str(value.encode('ascii', 'ignore')).strip()
                if not value: return None
            elif isinstance(value, str):
                value = value.strip()
                if not value: return None

            return value
    else:
        return getattr(state, field_string)


USE_FIRST_VALUE = 1
JOIN_STRINGS = 2
UNIQUE_LIST = 3

def aggregate_value_from_state(state, collapse_rules):
    aggregation_type, collapse_fields = collapse_rules

    if aggregation_type == USE_FIRST_VALUE:
        return aggregate_value_from_state_usefirstvalue(state, collapse_fields)
    elif aggregation_type == JOIN_STRINGS:
        return aggregate_value_from_state_joinstrings(state, collapse_fields)
    elif aggregation_type == UNIQUE_LIST:
        return aggregate_value_from_state_uniquelist(state, collapse_fields)
    else:
        raise ValueError("Unknown aggregation type: {}".format(aggregation_type))

def aggregate_value_from_state_usefirstvalue(state, use_first_fields):
    for source_string in use_first_fields:
        val = get_value_for_key(state, source_string)
        if val is not None and val != "": return val
    else:
        return None


def aggregate_value_from_state_uniquelist(state, list_fields):
    list_of_values = []

    for source_string in list_fields:
        val = get_value_for_key(state, source_string)
        if val: list_of_values.extend(get_id_fields(val))
    else:
        return set(list_of_values)

def aggregate_value_from_state_joinstrings(state, string_fields):
    values = []

    for source_string in string_fields:
        val = get_value_for_key(state, source_string)
        if val: values.append(val)
    else:
        return ";".join(values)
