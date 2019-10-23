Mapping
=======

This document describes the set of calls that occur from the web client or API
down to the back-end for the process of mapping data into SEED.

An overview of the process is:

1. Import - A file is uploaded to the server
2. Save - The file is batched saved into the database as JSON data
3. Mapping - Mapping occurs on that file
4. Matching / Merging
5. Pairing

Import
------

From the web UI, the import process invokes `seed.views.main.save_raw_data` to save the data. When the data is
done uploading, we need to know whether it is a Portfolio Manager file, so we can add metadata to the record in the
database. The end of the upload happens in `seed.data_importer.views.DataImportBackend.upload_complete`. At this
point, the request object has additional attributes for Portfolio Manager files. These are saved in the model
`seed.data_importer.models.ImportFile`.

Mapping
-------

The information captured above is used to build suggestions for column mappings. This process is made up of the following steps:

1. Raw columns are read in from the import file as is (column titles).

2. For each raw column, several attempts are made at finding suggestions of database columns scored from 0 to 100 (100 == highest confidence). The columns are checked in the following order until at least one suggestion is found:

   a. previous mapping - score of 100 for the one found.
   b. default mapping (only provided for Portfolio Manager imports) - score of 100 for the one found.
   c. 5 best possible matches between raw and existing database columns using Jaro-Winkler distance - score between 0 and 100.

3. The "best" suggested column mapping by score is noted for each raw column.

4. Two or more raw columns are prevented from having the same "best" database column suggestion. 

5. Any "best" suggestions with less than a score of 80 score removed.

6. Return the "best" suggestion (or an empty string if no suggestion available) for each raw column. These are formatted to build the suggestions the user sees while importing a file.

7. Once the mappings are saved (and the data are imported), the raw columns and eventual database column association (after user adjustments) are captured to be used as "previous mappings" in subsequent imports.

Step 2 ends once a possible suggestion is found. For example, steps b) and c) won't run if previous mappings provide the previously used database column for a raw column.

In step 2a, SEED can only have previous mappings if there were prior file imports. So, this step would be skipped in
the very first file import for an organization. It's possible to completely delete previous mappings for organization. This is done in the Column Mappings settings page for an organization but is not recommended as the user will lose the previous mappings which help import future data.

In step 2b, SEED contains default mappings only for Portfolio Manager imports. These are hardcoded into the application but are only referenced when no previous mapping is available for a raw column (when step 2a is skipped).

In step 2c, an altered version of the raw column string is used for this step. Any spaces (" ") are replaced with underscores ("_").
And, if the resulting lowercased version is one of the following, and the string is replaced as follows:

====================  =========================
 Lowercased Version          Actual Used
====================  =========================
"zip" or "zip_code"   postal_code
gba                   gross_floor_area
building_address      address_line_1
ubi                   jurisdiction_tax_lot_id
====================  =========================

Once this version of the raw column string is established, step 2c uses it to find the Jaro-Winkler distance to each database column.
The distance between two strings is based on 1) the number of character transpositions needed to get the strings to match and
2) the length that the prefixes match without transpositions. More information can be found here: _`https://en.wikipedia.org/wiki/Jaro–Winkler_distance`
This distance/score is captured between a raw column and all possible database columns for this organization. These results are
ordered by score so that the top 5 can be returned as suggestions.

Step 4 prevents duplicates by giving precedence to the raw column & "best" suggestion pair with the highest score. If multiple pairs have the same score,
the raw columns are ordered alphabetically, and the "greatest"  of them takes precedence ("b" is greater than "a").
Each raw column with lower precedence for a database column will use its next "best" column match or none, if only one was provided.

Matching
--------

.. todo:: document

Pairing
-------

.. todo:: document
