Matching
========

What is it?
-----------
Within SEED, matching refers to a possible relationship between at least 2 properties or at least 2 tax lots.
Two properties **match** if they have the same values for some specified field(s).
These specified fields are referred to as **matching criteria**, and each SEED organization has its
own set of matching criteria which is customizable by users.

Why does it exist?
------------------
At a high level, matching is used to identify if two or more property records are actually different
representations of the same property (or tax lots representing one tax lot).  For example, within the same cycle,
two matching records, so one persists while the other is used and subsequently discarded to update the persisting record
(say if the building owner's phone number changed). Or across different cycles, it's possible that the
two records capture the same property at different times/cycles - this relationship is referred to as a **link**.

How and when is it used?
------------------------

In-Cycle Merging
""""""""""""""""
(This is different from manual merging.)

For records within the same cycle, there really shouldn't be more than one
representation of the same property (or tax lot). As much as possible, the program
is set up to prevent this from happening by automatically **merging** matched
records together whenever they might occur in the same cycle.

Specifically, a merge of matches might need to occur after any of the following events:

1. The record has been manually edited.
2. The record was just created as a result of a manual merge (via the 'Actions' on the Properties or Tax Lots page).
3. The record has just been imported.

The actual execution of merges includes a few additional, unrelated steps but,
in the scope of merging, the following occurs.

The record in the scenarios listed above is the "target" record. Any and all
matches found, excluding the "target", are merged together first. If there are
overlapping values, priority is given to more recently updated records.

Once these matches (excluding the target) are merged together, the final step is
to merge the "target" record. In all but one case, choosing between overlapping
values gives priority to the "target". That one case is when a record has just been
imported. Here, overlapping values follow merge protection rules set by
the user for an organization in this final step.

Linking (Across Cycles)
"""""""""""""""""""""""
For records in different cycles, matches between these are considered links.
Links are used to connect snapshots of the same record year-over-year (at different time periods).
This allows for the analysis of how the record has changed over time.

In the case of properties, these links are used to associate meters to properties.
This means that adding meters to a property in one cycle will make those meters
accessible to that same property's instance in all other cycles.

This association can be viewed in aggregate; all of the records within some selected cycles are
grouped and displayed with their links. Alternatively, this association can be viewed for particular linked
group; the linked records of this group are displayed by themselves.

Putting them Together, Match-Merge-Linking
""""""""""""""""""""""""""""""""""""""""""
As mentioned earlier, there is a rule or assumption that at most one representation of
the same record can exist in any given cycle.

This avoids unresolvable situations that would prevent year-over-year analysis.
In the most simple case, a record in `Cycle A` matches two records in `Cycle B`.
SEED wouldn't know which of the two records in `Cycle B` should be
the "snapshot" for this time period.

For this reason, in-cycle match merging always occurs before cross-cycle match linking.
So when searches for links do happen, ambiguous cases have already been resolved.

For an individual record, these are the following cases in which a
match-merge-link is automatically run:
1. Explicit triggering (from the Propery/TaxLot Detail page)
2. After editing (in the Propery/TaxLot Detail page)
3. After manual merging (in the Properties/Tax Lots list page). Explicitly
specified merges happen as chosen by the user. Then, if the resulting record has
matches, merges and/or linking happens.
4. When importing a record. If the incoming record has matches,
merges and/or linking happens.

For a whole organization, a match-merge-link round for all records in that
organization is run in the following cases:
1. During the original deployment of this feature - This happens in order to
initially normalize the existing data and establish all initial links.
2. Whenever a user changes matching criteria - This happens in order to
re-normalize existing data and reestablish links.  As of this writing, before
committing matching criteria changes, a user can view a preview of how their
records will be affected as these are difficult to reverse.

Note on In-Cycle Not-merged Matches
"""""""""""""""""""""""""""""""""""
Even though the application tries it's best to have only one representative record per property
(or tax lot) per Cycle, it's possible for there to exist matches that were not merged.
This can happen if a user manually unmerges a record after a (manual or automatic) merge occurs.
If this happens, and there exists two records that match each other but are not merged,
both records are **completely unlinked**. Without user intervention such as editing
one of the matching criteria values, these will be merged and linked as described
above next time the system finds them during a match search.

Match Searching in Depth
------------------------
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

1. Amongst only the incoming records, duplicates (of other incoming or existing) are flagged and ignored.
2. Amongst only the incoming records, matching records are merged together.
3. Amongst all records in the same Cycle, incoming records that match an existing record gets merged with priority to that existing record.
    If the incoming record has multiple existing matches, the existing matches are merged together in
    latest updated order first while also combining any other associations (labels, notes, etc.) just as in the manual merge or edit cases.
    Since the incoming record is new, it doesn't have any of the other associations.
