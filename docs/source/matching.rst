Matching
========

What is it?
-----------
Within SEED, matching refers to a possible relationship between at least 2 properties or at least 2 tax lots.
Two properties **match** if they have the same values for some specified field(s).
These specified fields are called **matching criteria**, and each SEED organization has its
own set of matching criteria which is customizable by users.

Why does it exist?
------------------
At a high level, matching is used to identify if two or more property records are actually different
representations of the same property (or tax lots representing one tax lot).
For example, it's possible that the two records captured the same property at different times/cycles,
or within the same cycle, the most recent record is an updated snapshot of a
previously imported record (say if the building owner's phone number changed).

How and when is it used?
""""""""""""""""""""""""
In-Cycle Merging
****************
For records within the same Cycle, there really shouldn't be more than one
representation of the same property (or tax lot). As much as possible, the program
is set up to prevent this from happening by automatically **merging** matched
records together whenever it might occur.

Specifically, a search for matches occurs for a given record in the following cases:

1. The record has been manually edited.
2. The record was just created as a result of a manual merge (via the 'Actions' on the Properties or Tax Lots page).
3. The record has just been imported.

In any of these cases, any and all matches found are merged together.
Among the matches, if there are overlapping values, priority is given to more recently
uploaded records. Once, the matches are merged together, final/highest priority is given
to the "original" record - the record currently being edited, created from a merge, or imported.

In-Cycle Not-merged Matches
***************************
Even though the application tries it's best to have only one representative record per property
(or tax lot) per Cycle, it's possible for there to exist matches that were not merged.
This can happen if a user manually unmerges a record after a (manual or automatic) merge occurs.
If this happens, and there exists two records that match each other but are not merged,
nothing breaks, but without user intervention such as an edit, these will be rolled up
via merge as described in the above section the next time the system finds them during a match search.

Match Searching in Depth
************************
Though they accomplish the same goal, the process for merging is very different between the last case, importing,
and the first 2 cases, manual edit or manual merge.

In the case of manual merging or editing, this process accounts for the fact that these are records that already exist.
Specifically, they may have associations such as labels, notes, pairings, and for properties, meters.
So during a subsequent match search leading to a merge of two or more records, all of these "old" associations are
carried over to the final record once merges are complete.

In the case of importing, considerations must be taken for the fact that, in most cases, multiple records
are being imported together. Also, since this is the entry point for records, it's possible that a user might
accidentally try to import the same record snapshot twice - where all the record values are the same as another
existing record (as opposed to just having the same values for matching criteria fields). So on import, the
process is as follows:

1. Amongst only the incoming records, duplicates are flagged and ignored.
2. Amongst only the incoming records, matching records are merged together.
3. Amongst all records in the same Cycle, incoming records that match an existing record gets merged with priority to that existing record.
  - If the incoming record has multiple existing matches, the existing matches are merged together in ID order
    first while also combining any other associations (labels, notes, etc.) just as in the manual merge or edit cases.
  - Since the incoming record is new, it doesn't have any of the other associations.
