# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from collections import namedtuple

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models, transaction

from seed.models import (
    Analysis,
    Cycle,
    Property,
    PropertyState,
    PropertyView
)


BatchCreateError = namedtuple('BatchCreateError', ['property_view_id', 'message'])


class AnalysisPropertyView(models.Model):
    """
    The AnalysisPropertyView provides a "snapshot" of a property at the time an
    analysis was run.
    """
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    # It's assumed that the linked PropertyState is never modified, thus it's
    # important to "clone" PropertyState models rather than directly using those
    # referenced by normal PropertyViews.
    property_state = models.OneToOneField(PropertyState, on_delete=models.CASCADE)
    # parsed_results can contain any results gathered from the resulting file(s)
    # that are applicable to this specific property.
    # For results not specific to the property, use the Analysis's parsed_results
    parsed_results = JSONField(default=dict, blank=True)

    @classmethod
    def batch_create(cls, analysis_id, property_view_ids):
        """Creates AnalysisPropertyViews from provided PropertyView IDs.
        The method returns a tuple, the first value being a dictionary of the created
        AnalysisPropertyView IDs with the key as the original property_view_id,
        the second value being a list of BatchCreateErrors.

        Intended to be used when initializing an analysis.

        :param analysis_id: int
        :param property_view_ids: list[int]
        :returns: tuple(list[int], list[BatchCreateError])
        """
        analysis = Analysis.objects.get(id=analysis_id)
        with transaction.atomic():
            property_view_ids = set(property_view_ids)
            property_views = PropertyView.objects.filter(
                id__in=property_view_ids,
                property__organization_id=analysis.organization_id,
            )

            missing_property_views = property_view_ids - set(property_views.values_list('id', flat=True))
            failures = [
                BatchCreateError(view_id, 'No such PropertyView')
                for view_id in missing_property_views
            ]

            analysis_property_view_ids = {}
            for property_view in property_views:
                try:
                    # clone the property state
                    property_state = property_view.state
                    property_state.pk = None
                    property_state.save()

                    analysis_property_view = AnalysisPropertyView(
                        analysis_id=analysis_id,
                        property=property_view.property,
                        cycle=property_view.cycle,
                        property_state=property_state
                    )
                    analysis_property_view.full_clean()
                    analysis_property_view.save()
                    analysis_property_view_ids[property_view.id] = analysis_property_view.id
                except ValidationError as e:
                    failures.append(BatchCreateError(
                        property_view.id,
                        f'Validation of new AnalysisPropertyView failed:\n{e}'
                    ))

        return analysis_property_view_ids, failures

    @classmethod
    def get_property_views(cls, analysis_property_views):
        """Get PropertyViews related to the AnalysisPropertyViews. If no PropertyView
        is found for an AnalysisPropertyView, the value will be None for that key.

        :param analysis_property_views: list[AnalysisPropertyView]
        :return: dict{int: PropertyView}, PropertyViews keyed by the related AnalysisPropertyView id
        """
        # build a query to find PropertyViews linked to the canonical property and cycles we're interested in
        property_view_query = models.Q()
        for analysis_property_view in analysis_property_views:
            property_view_query |= (
                models.Q(property=analysis_property_view.property)
                & models.Q(cycle=analysis_property_view.cycle)
            )
        property_views = PropertyView.objects.filter(property_view_query).prefetch_related('state')

        # get original property views keyed by canonical property id and cycle
        property_views_by_property_cycle_id = {
            (pv.property.id, pv.cycle.id): pv
            for pv in property_views
        }

        return {
            # we use .get() here because the PropertyView might not exist anymore!
            apv.id: property_views_by_property_cycle_id.get((apv.property.id, apv.cycle.id), None)
            for apv in analysis_property_views
        }
