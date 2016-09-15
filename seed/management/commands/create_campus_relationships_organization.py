from __future__ import unicode_literals

import datetime
import logging

from django.core.management.base import BaseCommand

from _localtools import get_core_organizations
from seed.models import *

logging.basicConfig(level=logging.DEBUG)


def find_property_associated_with_portfolio_manager_id(pm_lot_id):
    if pm_lot_id is None: return False

    result = PropertyView.objects.filter(state__pm_property_id=pm_lot_id) \
        .first()
    if result is None: return False

    return result.property


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        return

    def handle(self, *args, **options):
        """Do something."""

        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = get_core_organizations()

        for org_id in core_organization:
            # Writing loop over organizations

            org = Organization.objects.filter(pk=org_id).first()
            logging.info("Processing organization {}".format(org))

            assert org, "Organization {} not found".format(org_id)

            property_views = PropertyView.objects.filter(cycle__organization=org) \
                .exclude(state__pm_parent_property_id=None) \
                .exclude(state__pm_parent_property_id="Not Applicable: Standalone Property") \
                .all()

            property_views = list(property_views)
            property_views.sort(key=lambda pv: pv.cycle.start)

            states = map(lambda pv: pv.state, list(property_views))

            # All property views where the state has a parent property that isn't "Not Applicable."
            for (pv, state) in zip(property_views, states):
                pm_parent_property_id = state.pm_parent_property_id

                # What is the difference between these two fields?
                if pm_parent_property_id == state.building_portfolio_manager_identifier or
                    pm_parent_property_id == state.pm_property_id:

                    print "Auto reference!"
                    prop = pv.property
                    prop.campus = True
                    prop.save()
                    continue

                parent_property = find_property_associated_with_portfolio_manager_id(
                    pm_parent_property_id)
                if not parent_property:
                    print "Could not find parent property."
                    parent_property = Property(organization_id=org_id)
                    parent_property.campus = True
                    parent_property.save()

                    # Create a view and a state for the active cycle.
                    parent_property_state = PropertyState(pm_property_id=pm_parent_property_id,
                                                          pm_parent_property_id=pm_parent_property_id,
                                                          property_notes="Created by campus relations migration on {}".format(
                                                              datetime.datetime.now().strftime(
                                                                  "%Y-%m-%d %H:%M")))
                    parent_property_state.save()

                    parent_property_view = PropertyView(property=parent_property, cycle=pv.cycle,
                                                        state=parent_property_state)
                    parent_property_view.save()

                    child_property = pv.property
                    child_property = child_property.parent_property = parent_property
                    child_property.save()


                else:
                    print "found campus relationship"
                    parent_property.campus = True
                    parent_property.save()

                    child_property = pv.property
                    child_property.parent_property = parent_property
                    child_property.save()

                    # Make sure the parent has a view for the same
                    # cycle as the pv in question.

                    if not PropertyView.objects.filter(property=parent_property,
                                                       cycle=pv.cycle).count():
                        parent_views = list(
                            PropertyView.objects.filter(property=parent_property).all())
                        parent_views.sort(key=lambda pv: pv.cycle.start)
                        # parent_views = [ppv for ppv in parent_views if ppv.cycle.start <= pv.cycle.start]
                        assert len(parent_views), "This should always be true."

                        ps = parent_views[-1].state
                        ps.pk = None

                        ps.save()

                        parent_view = PropertyView(property=parent_property, cycle=pv.cycle,
                                                   state=ps)
                        parent_view.save()

        return
