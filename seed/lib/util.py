# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author Dan Gunter <dkgunter@lbl.gov>
"""

import csv
import json
import locale
import sys

from seed.lib.mappings import mapper

# use this to recognize when to remove from mapping
REMOVE_KEY = 'REMOVE'


def create_map(path_in, path_out):
    """Create a JSON mapping file, suitable for `map.Mapping()`,
    from a CSV input file in our own custom style.

    Input columns: CurrentSEED,NewSEED,PM1,PM2,Type (ignore rest)

    :param path_in:
    :param path_out:
    :return: None
    """
    bedes_flag = mapper.Mapping.META_BEDES
    infile = csv.reader(open(path_in, newline=None, encoding=locale.getpreferredencoding(False)))
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
        outfile = open(path_out, 'w', encoding=locale.getpreferredencoding(False))
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
    map_file = open(map_path, encoding=locale.getpreferredencoding(False))
    mapping = mapper.Mapping(map_file, encoding='latin_1')
    data_file = open(data_path, newline=None, encoding=locale.getpreferredencoding(False))
    data_csv = csv.reader(data_file)
    # map each field
    d = {}
    input_fields = data_csv.next()
    matched, nomatch = mapping.apply(input_fields)
    for field, m in matched.items():
        d[field] = m.as_json()
        print(f'Mapped {field} => {m.field}')
    for field in nomatch:
        print(f'* No mapping found for input field: {field}')
        d[field] = mapper.MapItem(field, None).as_json()
    # write mapping as a JSON
    try:
        json.dump(d, out_file, ensure_ascii=True)
    except BaseException:
        # print('** Error: While writing:\n{}'.format(d))
        pass
    # write stats
    print(f'Mapped {len(input_fields)} fields: {len(matched)} OK and {len(nomatch)} did not match')


def find_duplicates(map_path, data_path, out_file):
    """Find duplicates created by a given mapping on a given input file.

    Args:
      map_path (str): Path to mapping file
      data_path (str): Path to data file
      out_file (file): output stream
    Return:
      None
    """
    map_file = open(map_path, encoding=locale.getpreferredencoding(False))
    mapping = mapper.Mapping(map_file, encoding='latin-1')
    data_file = open(data_path, newline=None, encoding=locale.getpreferredencoding(False))
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

    for value, keys in dup.items():
        keylist = ' | '.join(keys)
        out_file.write(
            f'({len(keys):d}) {value}: {keylist}\n',
        )
