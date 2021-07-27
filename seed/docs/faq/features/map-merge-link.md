---
question: Mapping, Merging, Matching, Pairing, and Linking - What do each of those mean and how are they related or different from each other?
tags: [features, inventory management]
---
Different inventory management and analysis features in SEED are based on the relationships between records of different inventory types (properties and tax lots). Those terms help describe these relationships.

![mapping diagram](/static/docs/images/mapping_diagram.png)

* **Mapping** refers to the process of mapping newly imported data fields to the known database column names in order to create a record.

* **Merging** refers to the act of combining multiple properties (or multiple tax lots) into one record. This can be done manually by users or automatically by SEED and helps avoid duplicate records.

* **Matching** refers to whether two or more properties match (or two or more tax lots). A match can only happen if specific fields between records match. Records can be compared within the same cycle (triggering a merge) or across cycles (building a link). The specific fields can be modified for each organization.

* **Pairing** refers to the association between properties and tax lots within the same cycle.

* **Linking** refers to the association between properties across cycles (or tax lots across cycles) and is useful for analysis.

For more details, refer to [this documentation that covers matching, merging, and linking](https://github.com/SEED-platform/seed/blob/develop/docs/source/matching.rst).
