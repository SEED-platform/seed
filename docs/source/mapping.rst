=========
Mapping
=========

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

Once files are uploaded, file header columns need to be mapped to SEED columns. Mappings can be specified/decided manually for any particular file import,
or mapping profiles can be created and subsequently applied to any file imports.

When a column mapping profile is applied to an import file, file header columns defined in the profile must match exactly (spaces, lowercase, uppercase, etc.)
in order for the corresponding SEED column information to be used/mapped.

Matching
--------

.. todo:: document

Pairing
-------

.. todo:: document
