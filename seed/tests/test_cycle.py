"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import date, datetime

from django.test import TestCase
from django.utils import timezone

from seed.lib.superperms.orgs.models import Organization
from seed.models import Cycle


class TestCycle(TestCase):
    def test_default_cycle(self):
        year = date.today().year - 1
        cycle_name = str(year) + " Calendar Year"

        self.org = Organization.objects.create()
        self.assertEqual(self.org.cycles.count(), 1)

        cycle = Cycle.objects.filter(name=cycle_name, organization=self.org)
        self.assertEqual(self.org.cycles.count(), 1)
        cycle.delete()
        cycle = Cycle.objects.filter(name=cycle_name, organization=self.org)
        self.assertEqual(self.org.cycles.count(), 0)

        cycle = Cycle.get_or_create_default(self.org)
        self.assertEqual(self.org.cycles.count(), 1)

    def test_default_cycle_not_recreated_when_other_cycles_exist(self):
        """If a user deletes the default Calendar Year cycle and creates their
        own, get_or_create_default should not recreate it."""
        year = date.today().year - 1
        default_name = f"{year} Calendar Year"

        self.org = Organization.objects.create()
        self.assertEqual(self.org.cycles.count(), 1)

        # delete the auto-created default cycle
        Cycle.objects.filter(name=default_name, organization=self.org).delete()
        self.assertEqual(self.org.cycles.count(), 0)

        # create a custom cycle covering the same year
        Cycle.objects.create(
            name=f"Reporting Period {year}",
            organization=self.org,
            start=datetime(year, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime(year, 12, 31, tzinfo=timezone.get_current_timezone()),
        )
        self.assertEqual(self.org.cycles.count(), 1)

        # get_or_create_default should return the existing cycle, not create a new one
        result = Cycle.get_or_create_default(self.org)
        self.assertEqual(self.org.cycles.count(), 1)
        self.assertEqual(result.name, f"Reporting Period {year}")
        self.assertFalse(Cycle.objects.filter(name=default_name, organization=self.org).exists())
