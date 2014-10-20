from django.test import TestCase

from seed.models import BuildingSnapshot


class TestJsonManager(TestCase):

    def setUp(self):
        self.model = BuildingSnapshot.objects.create()
        self.model.extra_data = {'superdata': 'always here', 'ratio': 0.43}
        self.model.save()

    def test_contains(self):
        """If nothing else, check containment for partial key value."""
        # Testing partial matches.
        qs = BuildingSnapshot.objects.all().json_query('super')
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs.first(), self.model)

        # Testing no matches.
        no_match_count = BuildingSnapshot.objects.all().json_query(
            'noooope'
        ).count()
        self.assertEqual(no_match_count, 0)

    def test_no_key(self):
        """We safely return an empty QS if nothing is queried."""
        self.assertListEqual(
            list(BuildingSnapshot.objects.all().json_query('')),
            list(BuildingSnapshot.objects.none())
        )

    def test_condition(self):
        """We apply conditions properly."""
        for x in range(5):
            b = BuildingSnapshot.objects.create()
            b.extra_data = {'ratio': 0.345}
            b.save()

        # Basic string comparison condition.
        qs = BuildingSnapshot.objects.all().json_query(
            'ratio', cond="!=", value="0.43"
        )

        # We should have found only the newly created 5.
        self.assertEqual(qs.count(), 5)
        self.assertFalse(self.model.pk in [m.pk for m in qs])

        # This should exclude the five we just created.
        qs = BuildingSnapshot.objects.all().json_query(
            'ratio', key_cast='float', cond='>', value='.35'
        )

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.model)

    def test_condition_unspecified_w_value(self):
        """We assume you want equality if you provide value and no cond."""
        self.assertEqual(
            BuildingSnapshot.objects.all().json_query(
                'superdata', value='always here', cond='='
            ).count(),
            BuildingSnapshot.objects.all().json_query(
                'superdata', value='always here'
            ).count()
        )

    def test_exclusion(self):
        """Exclude data that aren't relevant."""
        for x in range(5):
            b = BuildingSnapshot.objects.all().create()
            b.extra_data = {'ratio': 'N/A'}  # Garbage data.
            b.save()

        # Check initial condition before exclusions.
        qs = BuildingSnapshot.objects.all().json_query('ratio')
        self.assertEqual(qs.count(), 6)

        # Now exclude the garbage data.
        qs = BuildingSnapshot.objects.all().json_query(
            'ratio', excludes=['N/A']
        )

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.model)

    def test_exception_and_conditional(self):
        """Exclude and also filter."""
        b = BuildingSnapshot.objects.create()
        b.extra_data = {'ratio': 'N/A'}
        b.save()

        b = BuildingSnapshot.objects.create()
        b.extra_data = {'ratio': 0.80}
        b.save()

        b = BuildingSnapshot.objects.create()
        b.extra_data = {'ratio': 0.12}
        b.save()

        qs = BuildingSnapshot.objects.all().json_query(
            'ratio',
            cond='>',
            value='.2',
            key_cast='float',
            excludes=['Not Available', 'N/A']
        )

        # We excluded the N/As, which would have ruined our comparison
        # and we excluded things from the inequality. Only two remain.
        self.assertEqual(qs.count(), 2)

    def test_order_by(self):
        """Test that we're able to order by values of a json field."""
        b = BuildingSnapshot.objects.create(source_type=3)
        # This one should be skipped.
        b.extra_data = {'ratio': None}
        b.save()

        b = BuildingSnapshot.objects.create(source_type=3)
        b.extra_data = {'ratio': 0.12, 'counter': '10'}
        b.save()

        b = BuildingSnapshot.objects.create(source_type=3)
        b.extra_data = {'ratio': 0.80, 'counter': '1001'}
        b.save()

        buildings = list(BuildingSnapshot.objects.all().json_query(
            'ratio', key_cast='float', order_by='ratio'
        ))

        self.assertEqual(buildings[0].extra_data['ratio'], None)
        self.assertEqual(buildings[1].extra_data['ratio'], 0.12)
        self.assertEqual(buildings[2].extra_data['ratio'], 0.43)
        self.assertEqual(buildings[3].extra_data['ratio'], 0.80)

        # Now test what happens when we sort in reverse order.
        buildings2 = list(BuildingSnapshot.objects.all().json_query(
            'ratio', key_cast='float', order_by='ratio', order_by_rev=True
        ))

        self.assertEqual(buildings2[0].extra_data['ratio'], 0.80)
        self.assertEqual(buildings2[1].extra_data['ratio'], 0.43)
        self.assertEqual(buildings2[2].extra_data['ratio'], 0.12)
        self.assertEqual(buildings2[3].extra_data['ratio'], None)

        # Now test alpha numeric sorting
        buildings3 = list(BuildingSnapshot.objects.all().json_query(
            'counter', order_by='counter'
        ))

        self.assertEqual(buildings3[0].extra_data['counter'], '10')
        self.assertEqual(buildings3[1].extra_data['counter'], '1001')

        # Now test reverse sort on alpha numeric sorting
        buildings4 = list(BuildingSnapshot.objects.all().json_query(
            'counter', order_by='counter', order_by_rev=True
        ))

        self.assertEqual(buildings4[0].extra_data['counter'], '1001')
        self.assertEqual(buildings4[1].extra_data['counter'], '10')

    def test_case_insensitive(self):
        """Make sure that we do case insensitive comparisons."""

        b = BuildingSnapshot.objects.create(source_type=3)
        b.extra_data = {'thing': 'vAluE'}
        b.save()

        no_matches_count = BuildingSnapshot.objects.all().json_query(
            'thing', value='value'
        ).count()

        self.assertEqual(no_matches_count, 0)

        matches_count = BuildingSnapshot.objects.all().json_query(
            'thing', value='value', case_insensitive=True
        ).count()

        self.assertEqual(matches_count, 1)

    def test_wildcards(self):
        """Passing wildcards into our query allows greedy matching."""
        no_matches_count = BuildingSnapshot.objects.all().json_query(
            'superdata', cond='LIKE', value='always'
        ).count()

        self.assertEqual(no_matches_count, 0)

        matches_count = BuildingSnapshot.objects.all().json_query(
            'superdata', cond='LIKE', value='always%'
        ).count()

        self.assertEqual(matches_count, 1)
