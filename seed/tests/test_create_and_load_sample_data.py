"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.management import call_command
from django.test import TestCase

from seed.lib.superperms.orgs.models import Organization
from seed.models import Cycle, PropertyAuditLog, PropertyView, TaxLotAuditLog, TaxLotView


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
        self.assertGreaterEqual(PropertyAuditLog.objects.filter(organization=org).count(), property_views.count())
        self.assertGreaterEqual(TaxLotAuditLog.objects.filter(organization=org).count(), taxlot_views.count())
        for view in [*property_views, *taxlot_views]:
            self.assertEqual(view.state.organization_id, org.id)
