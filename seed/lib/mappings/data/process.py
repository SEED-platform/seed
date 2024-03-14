"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
import re
from os.path import dirname, join, realpath

f = open(join(dirname(realpath(__file__)), "pm-mapping-orig.json"))
data = json.load(f)


def downcase(str):
    return str.replace(' ', '_').lower()


def strip_units(str):
    m = re.search(r".*\((.*)\).*", str)
    if m:
        return [re.sub(r"\((.*)\)", "", str).strip(), m.groups()[0]]
    else:
        return [str, ""]


new_data = []
for key, d in data.items():
    updated_key, units = strip_units(key)
    a = {}
    a['from_field'] = key
    a['to_table_name'] = "PropertyState"
    a['to_field'] = downcase(d[0])
    a['display_name'] = d[0]
    a['schema'] = 'bedes' if d[1]['bedes'] else ''
    a['type'] = d[1]['type']
    a['units'] = units

    new_data.append(a)


# sort the data
new_data = sorted(new_data, key=lambda k: k['to_field'])

with open('outputfile.json', 'w') as out:
    json.dump(new_data, out)
