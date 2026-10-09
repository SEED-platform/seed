"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from itertools import pairwise

from django.core.management import call_command
from django.test import TestCase

from seed.lib.superperms.orgs.models import Organization
from seed.models import Cycle, PropertyAuditLog, PropertyView, TaxLotAuditLog, TaxLotView
from seed.models.auditlog import AUDIT_IMPORT, AUDIT_USER_EDIT


class TestCreateAndLoadSampleData(TestCase):
    def _run(self, years, audit_depth=1):
        call_command(
            "create_and_load_sample_data",
            "--A=2",
            "--B=1",
            "--C=1",
            "--D=1",
            f"--Y={years}",
            f"--audit-depth={audit_depth}",
            verbosity=0,
        )
        return Organization.objects.get(name="SampleDataDemo_caseALL")

    def test_single_year(self):
        org = self._run("2022")

        self.assertTrue(Cycle.objects.filter(organization=org, name="2022 Annual").exists())
        self.assertGreater(PropertyView.objects.filter(cycle__organization=org).count(), 0)
        self.assertGreater(TaxLotView.objects.filter(cycle__organization=org).count(), 0)

    def test_multiple_years_with_audit_history(self):
        org = self._run("2022,2023", audit_depth=2)

        self.assertEqual(Cycle.objects.filter(organization=org, name__in=["2022 Annual", "2023 Annual"]).count(), 2)
        property_views = PropertyView.objects.filter(cycle__organization=org)
        taxlot_views = TaxLotView.objects.filter(cycle__organization=org)
        self.assertGreater(property_views.count(), 0)
        self.assertGreater(taxlot_views.count(), 0)

        for views, log_model in ((property_views, PropertyAuditLog), (taxlot_views, TaxLotAuditLog)):
            for view in views:
                self.assertEqual(view.state.organization_id, org.id)
                logs = list(log_model.objects.filter(view=view).order_by("pk"))
                # creation log followed by one edit per audit-depth update; cases B/C/D may touch a view in more than one pass
                self.assertGreaterEqual(len(logs), 2, view)
                self.assertEqual(logs[0].record_type, AUDIT_IMPORT)
                self.assertIsNone(logs[0].parent1)
                for parent, log in pairwise(logs):
                    self.assertEqual(log.record_type, AUDIT_USER_EDIT)
                    self.assertEqual(log.parent1_id, parent.pk)
                    self.assertEqual(log.parent_state1_id, parent.state_id)
                self.assertEqual(logs[-1].state_id, view.state_id)

    def test_earlier_cycle_keeps_its_own_state(self):
        org = self._run("2022,2023")

        early = TaxLotView.objects.filter(cycle__organization=org, cycle__name="2022 Annual")
        late = TaxLotView.objects.filter(cycle__organization=org, cycle__name="2023 Annual")
        self.assertGreater(early.count(), 0)
        self.assertFalse({v.state_id for v in early} & {v.state_id for v in late})
        for view in late:
            self.assertEqual(view.state.extra_data["Tax Year"], "2023")
        for view in early:
            self.assertNotEqual(view.state.extra_data["Tax Year"], "2023")
        # the same taxlot is carried from one cycle to the next
        self.assertTrue({v.taxlot_id for v in early} & {v.taxlot_id for v in late})
