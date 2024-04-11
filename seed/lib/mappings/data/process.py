"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import locale
import re
from os.path import dirname, join, realpath

file_path = join(dirname(realpath(__file__)), "pm-mapping-orig.json")
with open(file_path, encoding=locale.getpreferredencoding(False)) as f:
    data = json.load(f)


def downcase(s: str):
    return s.replace(" ", "_").lower()


def strip_units(s: str):
    m = re.search(r".*\((.*)\).*", s)
    if m:
        return [re.sub(r"\((.*)\)", "", s).strip(), m.groups()[0]]
    else:
        return [s, ""]


new_data = []
for key, d in data.items():
    updated_key, units = strip_units(key)
    a = {
        "from_field": key,
        "to_table_name": "PropertyState",
        "to_field": downcase(d[0]),
        "display_name": d[0],
        "schema": "bedes" if d[1]["bedes"] else "",
        "type": d[1]["type"],
        "units": units,
    }

    new_data.append(a)


# sort the data
new_data = sorted(new_data, key=lambda k: k["to_field"])

with open("outputfile.json", "w", encoding=locale.getpreferredencoding(False)) as out:
    json.dump(new_data, out)
