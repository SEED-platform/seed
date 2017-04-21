# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Dan Gunter <dkgunter@lbl.gov>
"""

import csv
import json
import sys

from seed.lib.mappings import mapper

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
        if len(row) < 5:
            break
        meta = {bedes_flag: True}
        if len(row[1]) > 0:
            if row[1] == REMOVE_KEY:
                continue  # don't map this
            value = row[1]
        elif len(row[0]) > 0:
            value = row[0]
            meta[bedes_flag] = False
        else:
            value = None  # will use PM value
            meta[bedes_flag] = False
        meta[mapper.Mapping.META_TYPE] = row[4]
        for key in row[2], row[3]:
            if len(key) > 0:
                map[key] = [value, meta]
    if path_out == '-':
        outfile = sys.stdout
    else:
        outfile = open(path_out, "w")
    json.dump(map, outfile, encoding='latin_1')


def apply_map(map_path, data_path, out_file):
    """Apply a JSON mapping to data, and write the output.

    Args:
      map_path (str): Path to mapping file
      data_path (str): Path to data file
      out_file (file): output stream
    Return:
      None
    """
    map_file = open(map_path, "r")
    mapping = mapper.Mapping(map_file, encoding='latin_1')
    data_file = open(data_path, "rU")
    data_csv = csv.reader(data_file)
    # map each field
    d = {}
    input_fields = data_csv.next()
    matched, nomatch = mapping.apply(input_fields)
    for field, m in matched.iteritems():
        d[field] = m.as_json()
        print "Mapped {} => {}".format(field, m.field)
    for field in nomatch:
        print "* No mapping found for input field: {}".format(field)
        d[field] = mapper.MapItem(field, None).as_json()
    # write mapping as a JSON
    try:
        json.dump(d, out_file, ensure_ascii=True)
    except:
        # print("** Error: While writing:\n{}".format(d))
        pass
    # write stats
    print "Mapped {} fields: {} OK and {} did not match".format(
        len(input_fields), len(matched), len(nomatch))


def find_duplicates(map_path, data_path, out_file):
    """Find duplicates created by a given mapping on a given input file.

    Args:
      map_path (str): Path to mapping file
      data_path (str): Path to data file
      out_file (file): output stream
    Return:
      None
    """
    map_file = open(map_path, "r")
    mapping = mapper.Mapping(map_file, encoding='latin-1')
    data_file = open(data_path, "rU")
    data_csv = csv.reader(data_file)
    hdr = data_csv.next()
    seen_values, dup = {}, {}
    for src in hdr:
        value = mapping.get(src, None)
        if value is None:
            continue
        dst = value.field
        if dst in seen_values:  # this is a duplicate
            if src in dup:  # we already have >= 1 duplicates
                # add new duplicate to list
                dup[dst].append(src)
            else:  # first duplicate
                # add both keys to list
                seen_key = seen_values[dst]
                dup[dst] = [seen_key, src]
        else:
            seen_values[dst] = src
    # print results
    for value, keys in dup.items():
        keylist = ' | '.join(keys)
        out_file.write(
            "({n:d}) {v}: {kl}\n".format(
                n=len(keys),
                v=value,
                kl=keylist,
            ),
        )
