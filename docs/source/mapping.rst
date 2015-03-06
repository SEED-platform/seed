Mapping
=======

This document describes the set of calls that occur from the web client or API
down to the back-end for the process of mapping.

An overview of the process is:

1. Import - A file is uploaded and saved in the database
2. Mapping - Mapping occurs on that file

Import
------

From the web UI, the import process invokes

`seed.views.main.save_raw_data`
`seed.views.main.get_column_mapping_suggestions`