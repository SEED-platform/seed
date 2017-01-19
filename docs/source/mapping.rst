Mapping
=======

This document describes the set of calls that occur from the web client or API
down to the back-end for the process of mapping.

An overview of the process is:

1. Import - A file is uploaded and saved in the database
2. Mapping - Mapping occurs on that file
3. Matching / Merging
4. Pairing

Import
------

From the web UI, the import process invokes `seed.views.main.save_raw_data` to save the data. When the data is
done uploading, we need to know whether it is a Portfolio Manager file, so we can add metadata to the record in the
database. The end of the upload happens in `seed.data_importer.views.DataImportBackend.upload_complete` or
`seed.data_importer.views.handle_s3_upload_complete`, depending on whether it is using a local file system or
Amazon S3-based backend. At this point, the request object has additional attributes for Portfolio Manager files.
These are saved in the model `seed.data_importer.models.ImportFile`.

Mapping
-------

After the data is saved, the UI invokes `DataFileViewSet.mapping_suggestions` to get the columns to
display on the mapping screen. This loads back the model that was mentioned above as an `ImportFile` instance, and
then the `from_portfolio_manager` property can be used to choose the branch of the code:

If it is a Portfolio Manager file the `seed.common.mapper.get_pm_mapping` method provides a high-level interface to
the Portfolio Manager mapping (see comments in the containing file, `mapper.py`), and the result is used to populate
the return value for this method, which goes back to the UI to display the mapping screen.

Otherwise the code does some auto-magical logic to try and infer the "correct" mapping.

Matching
--------

.. todo:: document

Pairing
-------

.. todo:: document