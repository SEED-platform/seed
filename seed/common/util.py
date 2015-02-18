"""
Utility functions for processing external files, etc.
"""
__author__ = 'Dan Gunter <dkgunter@lbl.gov>'
__date__ = '2/13/15'

import csv
import json
from . import mapper

# use this to recognize when to remove from mapping
REMOVE_KEY = "REMOVE"

def create_map(path_in, path_out):
    """Create a JSON mapping file, suitable for `map.Mapping()`,
    from a CSV input file in our own custom style.

    Input columns: CurrentSEED,NewSEED,PM1,PM2,Type (ignore rest)

    :param path_in:
    :param path_out:
    :return: None
    """
    bedes_flag = mapper.Mapping.META_BEDES
    infile = csv.reader(open(path_in, "rU"))
    header = infile.next()
    assert len(header) >= 5
    map = {}
    for row in infile:
        meta = {bedes_flag: True}
        if len(row[1]) > 0:
            if row[1] == REMOVE_KEY:
                continue # don't map this
            value = row[1]
        elif len(row[0]) > 0:
            value = row[0]
            meta[bedes_flag] = False
        else:
            value = None # will use PM value
            meta[bedes_flag] = False
        meta[mapper.Mapping.META_TYPE] = row[4]
        for key in row[2], row[3]:
            if len(key) > 0:
                if value is None:
                    field = key
                else:
                    field = value
                map[key] = [value, meta]
    outfile = open(path_out, "w")
    json.dump(map, outfile)

def apply_map(path_map, path_data, file_out):
    """Apply a JSON mapping to data, and write the output.

    :param path_map:
    :param path_data:
    :param file_out:
    :return:
    """
    map_file = open(path_map, "r")
    mapping = mapper.Mapping(map_file, encoding='latin_1')
    data_file = open(path_data, "rU")
    data_csv = csv.reader(data_file)
    # map each field
    d = {}
    input_fields = data_csv.next()
    matched, nomatch = mapping.apply(input_fields)
    for field, m in matched.iteritems():
        d[field] = m.as_json()
        print("Mapped {} => {}".format(field, m.field))
    for field in nomatch:
        print("* No mapping found for input field: {}".format(field))
        d[field] = mapper.MapItem(field, None).as_json()
    # write mapping as a JSON
    try:
        json.dump(d, file_out, ensure_ascii=True)
    except:
        #print("** Error: While writing:\n{}".format(d))
        pass
    # write stats
    print("Mapped {} fields: {} OK and {} did not match".format(
        len(input_fields),  len(matched), len(nomatch)))

