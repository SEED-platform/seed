# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from datetime import datetime

from django.core.urlresolvers import reverse
from django.utils.timezone import get_current_timezone

from seed.data_importer.tasks import match_buildings
from seed.landing.models import SEEDUser as User
from seed.models import (
    DATA_STATE_MAPPING,
    PropertyView,
    TaxLot,
    TaxLotProperty,
    TaxLotView,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeNoteFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeStatusLabelFactory,
    FakeTaxLotFactory,
    FakeTaxLotStateFactory,
)
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization


class TaxLotViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.client.login(**user_details)

    def test_merged_indicators_provided_on_filter_endpoint(self):
        _import_record, import_file_1 = self.create_import_file(self.user, self.org, self.cycle)

        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file_1 mapping done so that record is "created for users to view".
        import_file_1.mapping_done = True
        import_file_1.save()
        match_buildings(import_file_1.id)

        _import_record_2, import_file_2 = self.create_import_file(self.user, self.org, self.cycle)

        url = reverse('api:v2:taxlots-filter') + '?cycle_id={}&organization_id={}&page=1&per_page=999999999'.format(self.cycle.pk, self.org.pk)
        response = self.client.post(url)
        data = json.loads(response.content)

        self.assertFalse(data['results'][0]['merged_indicator'])

        # make sure merged_indicator is True when merge occurs
        base_details['city'] = 'Denver'
        base_details['import_file_id'] = import_file_2.id
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file_2 mapping done so that match merging can occur.
        import_file_2.mapping_done = True
        import_file_2.save()
        match_buildings(import_file_2.id)

        url = reverse('api:v2:taxlots-filter') + '?cycle_id={}&organization_id={}&page=1&per_page=999999999'.format(self.cycle.pk, self.org.pk)
        response = self.client.post(url)
        data = json.loads(response.content)

        self.assertTrue(data['results'][0]['merged_indicator'])

        # Create pairings and check if paired object has indicator as well
        property_factory = FakePropertyFactory(organization=self.org)
        property_state_factory = FakePropertyStateFactory(organization=self.org)

        property = property_factory.get_property()
        property_state = property_state_factory.get_property_state()
        property_view = PropertyView.objects.create(
            property=property, cycle=self.cycle, state=property_state
        )

        # attach pairing to one and only taxlot_view
        TaxLotProperty(
            primary=True,
            cycle_id=self.cycle.id,
            property_view_id=property_view.id,
            taxlot_view_id=TaxLotView.objects.get().id
        ).save()

        url = reverse('api:v2:taxlots-filter') + '?cycle_id={}&organization_id={}&page=1&per_page=999999999'.format(self.cycle.pk, self.org.pk)
        response = self.client.post(url)
        data = json.loads(response.content)

        related = data['results'][0]['related'][0]

        self.assertTrue('merged_indicator' in related)
        self.assertFalse(related['merged_indicator'])


class TaxLotMergeUnmergeViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.taxlot_factory = FakeTaxLotFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.client.login(**user_details)

        self.state_1 = self.taxlot_state_factory.get_taxlot_state()
        self.taxlot_1 = self.taxlot_factory.get_taxlot()
        self.view_1 = TaxLotView.objects.create(
            taxlot=self.taxlot_1, cycle=self.cycle, state=self.state_1
        )

        self.state_2 = self.taxlot_state_factory.get_taxlot_state()
        self.taxlot_2 = self.taxlot_factory.get_taxlot()
        self.view_2 = TaxLotView.objects.create(
            taxlot=self.taxlot_2, cycle=self.cycle, state=self.state_2
        )

    def test_taxlots_merge_without_losing_labels(self):
        # Create 3 Labels
        label_factory = FakeStatusLabelFactory(organization=self.org)

        label_1 = label_factory.get_statuslabel()
        label_2 = label_factory.get_statuslabel()
        label_3 = label_factory.get_statuslabel()

        self.view_1.labels.add(label_1, label_2)
        self.view_2.labels.add(label_2, label_3)

        # Merge the taxlots
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]
        })
        self.client.post(url, post_params, content_type='application/json')

        # The resulting -View should have 3 notes
        view = TaxLotView.objects.first()

        self.assertEqual(view.labels.count(), 3)
        label_names = list(view.labels.values_list('name', flat=True))
        self.assertCountEqual(label_names, [label_1.name, label_2.name, label_3.name])

    def test_taxlots_merge_without_losing_notes(self):
        note_factory = FakeNoteFactory(organization=self.org, user=self.user)

        # Create 3 Notes and distribute them to the two -Views.
        note1 = note_factory.get_note(name='non_default_name_1')
        note2 = note_factory.get_note(name='non_default_name_2')
        self.view_1.notes.add(note1)
        self.view_1.notes.add(note2)

        note3 = note_factory.get_note(name='non_default_name_3')
        self.view_2.notes.add(note2)
        self.view_2.notes.add(note3)

        # Merge the taxlots
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]
        })
        self.client.post(url, post_params, content_type='application/json')

        # The resulting -View should have 3 notes
        view = TaxLotView.objects.first()

        self.assertEqual(view.notes.count(), 3)
        note_names = list(view.notes.values_list('name', flat=True))
        self.assertCountEqual(note_names, [note1.name, note2.name, note3.name])

    def test_taxlots_merge_without_losing_pairings(self):
        # Create 2 pairings and distribute them to the two -Views.
        property_factory = FakePropertyFactory(organization=self.org)
        property_state_factory = FakePropertyStateFactory(organization=self.org)

        property_1 = property_factory.get_property()
        state_1 = property_state_factory.get_property_state()
        property_view_1 = PropertyView.objects.create(
            property=property_1, cycle=self.cycle, state=state_1
        )

        property_2 = property_factory.get_property()
        state_2 = property_state_factory.get_property_state()
        property_view_2 = PropertyView.objects.create(
            property=property_2, cycle=self.cycle, state=state_2
        )

        TaxLotProperty(
            primary=True,
            cycle_id=self.cycle.id,
            property_view_id=property_view_1.id,
            taxlot_view_id=self.view_1.id
        ).save()

        TaxLotProperty(
            primary=True,
            cycle_id=self.cycle.id,
            property_view_id=property_view_2.id,
            taxlot_view_id=self.view_2.id
        ).save()

        # Merge the taxlots
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        # There should still be 2 TaxLotProperties
        self.assertEqual(TaxLotProperty.objects.count(), 2)

        taxlot_view = TaxLotView.objects.first()
        paired_propertyview_ids = list(
            TaxLotProperty.objects.filter(taxlot_view_id=taxlot_view.id).values_list('property_view_id', flat=True)
        )
        self.assertCountEqual(paired_propertyview_ids, [property_view_1.id, property_view_2.id])

    def test_merge_assigns_new_canonical_records_to_each_resulting_record_and_old_canonical_records_are_deleted_when_if_associated_to_views(self):
        # Capture old taxlot_ids
        persisting_taxlot_id = self.taxlot_1.id
        deleted_taxlot_id = self.taxlot_2.id

        new_cycle = self.cycle_factory.get_cycle(
            start=datetime(2011, 10, 10, tzinfo=get_current_timezone())
        )
        new_taxlot_state = self.taxlot_state_factory.get_taxlot_state()
        TaxLotView.objects.create(
            taxlot=self.taxlot_1, cycle=new_cycle, state=new_taxlot_state
        )

        # Merge the taxlots
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        self.assertFalse(TaxLotView.objects.filter(taxlot_id=deleted_taxlot_id).exists())
        self.assertFalse(TaxLot.objects.filter(pk=deleted_taxlot_id).exists())

        self.assertEqual(TaxLotView.objects.filter(taxlot_id=persisting_taxlot_id).count(), 1)

    def test_taxlots_unmerge_without_losing_labels(self):
        # Merge the taxlots
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        # Create 3 Labels - add 2 to view
        label_factory = FakeStatusLabelFactory(organization=self.org)

        label_1 = label_factory.get_statuslabel()
        label_2 = label_factory.get_statuslabel()

        view = TaxLotView.objects.first()  # There's only one TaxLotView
        view.labels.add(label_1, label_2)

        # Unmerge the taxlots
        url = reverse('api:v2:taxlots-unmerge', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(url, content_type='application/json')

        for new_view in TaxLotView.objects.all():
            self.assertEqual(new_view.labels.count(), 2)
            label_names = list(new_view.labels.values_list('name', flat=True))
            self.assertCountEqual(label_names, [label_1.name, label_2.name])

    def test_unmerge_results_in_the_use_of_new_canonical_taxlots_and_deletion_of_old_canonical_state_if_unrelated_to_any_views(self):
        # Merge the taxlots
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        # Capture "old" taxlot_id - there's only one TaxLotView
        view = TaxLotView.objects.first()
        taxlot_id = view.taxlot_id

        # Unmerge the taxlots
        url = reverse('api:v2:taxlots-unmerge', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(url, content_type='application/json')

        self.assertFalse(TaxLot.objects.filter(pk=taxlot_id).exists())
        self.assertEqual(TaxLot.objects.count(), 2)

    def test_unmerge_results_in_the_persistence_of_old_canonical_state_if_related_to_any_views(self):
        # Merge the taxlots
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        # Associate only canonical taxlot with records across Cycle
        view = TaxLotView.objects.first()
        taxlot_id = view.taxlot_id

        new_cycle = self.cycle_factory.get_cycle(
            start=datetime(2011, 10, 10, tzinfo=get_current_timezone())
        )
        new_taxlot_state = self.taxlot_state_factory.get_taxlot_state()
        TaxLotView.objects.create(
            taxlot_id=taxlot_id, cycle=new_cycle, state=new_taxlot_state
        )

        # Unmerge the taxlots
        url = reverse('api:v2:taxlots-unmerge', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(url, content_type='application/json')

        self.assertTrue(TaxLot.objects.filter(pk=view.taxlot_id).exists())
        self.assertEqual(TaxLot.objects.count(), 3)
