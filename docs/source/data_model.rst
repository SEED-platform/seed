Data Model
==========

Our primary data model is based on a tree structure with BuildingSnapshot
instances as nodes of the tree and the tip of the tree referenced by a
CanonicalBuilding.

Take the following example: a user has loaded a CSV file containing information
about one building and created the first BuildingSnapshot (BS0). At this point
in time, BS0 is linked to the first CanonicalBuilding (CB0), and CB0 is also
linked to BS0.

.. code-block:: shell

    BS0 <-- CB0
    BS0 --> CB0

These relations are represented in the database as foreign keys from the
BuildingSnapshot table to the CanonicalBuilding table, and from the
CanonicalBuilding table to the BuildingSnapshot table.

The tree structure comes to fruition when a building, BS0 in our case, is
matched with a new building, say BS1, enters the system and is auto-matched.

Here BS1 entered the system and was matched with BS0. When a match occurs,
a new BuildingSnapshot is created, BS2, with the fields from the primary
BuildingSnapshot, BS0, and the secondary BuildingSnapshot, BS1, merged
together. If both the primary and secondary BuildingSnapshot have data for a
given field, the primary's fields are preferred and merged into the child, B3.

All BuildingSnapshot instances point to a CanonicalBuilding.

.. code-block:: shell

    BS0  BS1
      \ /
      BS2 <-- CB0

    BS0 --> CB0
    BS1 --> CB0
    BS2 --> CB0


parents and children
^^^^^^^^^^^^^^^^^^^^

BuildingSnapshots also have linkage to other BuildingSnapshots in order to
keep track of their *parents* and *children*. This is represented in the
database as a many-to-many relation from BuildingSnapshot to BuildingSnapshot.
In our case here, BS0 and BS1 would both have *children* BS2, and BS2 would
have *parents* BS0 and BS1.

.. note::
    throughout most of the application, the ``search_buildings`` endpoint
    is used to search or list active building. This is to say, buildings that
    are pointed to by an active CanonicalBuilding.
    The ``search_building_snapshots`` endpoint allows the search of buildings
    regardless of whether the BuildingSnapshot is pointed to by an active
    CanonicalBuilding or not and this search is needed during the mapping
    preview and matching sections of the application.



For illustration purposes let's suppose BS2 and a new building BS3 match to form a child BS4.

+--------+-------+
| parent | child |
+========+=======+
| BS0    | BS2   |
+--------+-------+
| BS1    | BS2   |
+--------+-------+
| BS2    | BS4   |
+--------+-------+
| BS3    | BS4   |
+--------+-------+


And the corresponding tree would look like:

.. code-block:: shell

    BS0  BS1
      \ /
      BS2  BS3
        \  /
         BS4 <-- CB0

    BS0 --> CB0
    BS1 --> CB0
    BS2 --> CB0
    BS3 --> CB0
    BS4 --> CB0

matching
--------

During the auto-matching process, if a *raw* BuildingSnapshot matches an
existing BuildingSnapshot instance, then it will point to the existing
BuildingSnapshot instance's CanonicalBuilding. In the case where there is no
existing BuildingSnapshot to match, a new CanonicalBuilding will be created, as
happened to B0 and C0 above.

+-------+--------+--------+-------------+
| field | BS0    | BS1    | BS2 (child) |
+=======+========+========+=============+
| id1   | **11** | 11     | 11          |
+-------+--------+--------+-------------+
| id2   |        | **12** | 12          |
+-------+--------+--------+-------------+
| id3   | **14** |        | 14          |
+-------+--------+--------+-------------+
| id4   | **13** | 14     | 13          |
+-------+--------+--------+-------------+


manual-matching vs auto-matching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since BuildingSnapshots can be manually matched, there is the possibility for
two BuildingSnapshots each with an active CanonicalBuilding to match and the
system has to choose to move only one CanonicalBuilding to the tip of the tree
for the primary BuildingSnapshot and *deactivate* the secondary
BuildingSnapshot's CanonicalBuilding.

Take for example:

.. code-block:: shell

    BS0  BS1
      \ /
      BS2  BS3
        \  /
         BS4 <-- CB0 (active: True)         BS5 <-- CB1 (active: True)

If a user decides to manually match BS4 and BS5, the system will take the
primary BuildingSnapshot's CanonicalBuilding and have it point to their
child and deactivate CB1. The deactivation is handled by setting a field
on the CanonicalBuilding instance, *active*, from ``True`` to ``False``.

Here is what the tree would look like after the manual match of **BS4** and
**BS5**:

.. code-block:: shell

    BS0  BS1
      \ /
      BS2  BS3
        \  /
         BS4  BS5 <-- CB1 (active: False)
           \  /
            BS6 <-- CB0 (active: True)

Even though BS5 is pointed to by a CanonicalBuilding, CB1, BS5 will not be
returned by the normal ``search_buildings`` endpoint because the
CanonicalBuilding pointing to it has its field ``active`` set to ``False``.

.. note::
    anytime a match is **unmatched** the system will create a new
    CanonicalBuilding or set an existing CanonicalBuilding's active field to
    ``True`` for any leaf BuildingSnapshot trees.

