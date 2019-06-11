Data Quality
============

Data quality checks are run after the data are paired, during import of Properties/TaxLots, or on-demand by selecting rows in the inventory
page and clicking the action button. This checks whether any default or user-defined Rules are broken or satisfied by Property/TaxLot records.

Notably, in most cases when data quality checks are run, Labels can be applied for any broken Rules that have a Label.
To elaborate, Rules can have an attached Label. When a data quality check is run, records that break one of these "Labeled Rules"
are then given that Label. The case where this Label attachment does not happen is during import due to performance reasons.
