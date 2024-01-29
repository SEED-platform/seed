# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import datetime

from django.urls import reverse
from django.utils.timezone import get_current_timezone

from seed.data_importer.tasks import geocode_and_match_buildings_task
from seed.landing.models import SEEDUser as User
from seed.models import (
    DATA_STATE_MAPPING,
    VIEW_LIST_TAXLOT,
    Column,
    Label,
    Note,
    PropertyView,
    TaxLot,
    TaxLotProperty,
    TaxLotView
)
from seed.test_helpers.fake import (
    FakeColumnListProfileFactory,
    FakeCycleFactory,
    FakeNoteFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeStatusLabelFactory,
    FakeTaxLotFactory,
    FakeTaxLotStateFactory
)
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.match import match_merge_link
from seed.utils.merge import merge_taxlots
from seed.utils.organizations import create_organization
from seed.utils.properties import pair_unpair_property_taxlot


class TaxLotViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }

        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        self.taxlot_factory = FakeTaxLotFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)

        # create tree
        self.org.access_level_names = ["1st Gen", "2nd Gen", "3rd Gen"]
        mom_ali = self.org.add_new_access_level_instance(self.org.root.id, "mom")
        self.me_ali = self.org.add_new_access_level_instance(mom_ali.id, "me")
        self.sister_ali = self.org.add_new_access_level_instance(mom_ali.id, "sister")
        self.org.save()

    def test_get_links_for_a_single_property(self):
        # Create 2 linked property sets
        state = self.taxlot_state_factory.get_taxlot_state(extra_data={"field_1": "value_1"})
        taxlot = self.taxlot_factory.get_taxlot()
        view_1 = TaxLotView.objects.create(
            taxlot=taxlot, cycle=self.cycle, state=state
        )

        later_cycle = self.cycle_factory.get_cycle(
            start=datetime(2100, 10, 10, tzinfo=get_current_timezone()))
        state_2 = self.taxlot_state_factory.get_taxlot_state(extra_data={"field_1": "value_2"})
        view_2 = TaxLotView.objects.create(
            taxlot=taxlot, cycle=later_cycle, state=state_2
        )

        # save all the columns in the state to the database
        Column.save_column_names(state)

        url = reverse('api:v3:taxlots-links', args=[view_1.id])
        url += f'?organization_id={self.org.pk}'
        response = self.client.get(url)
        data = response.json()['data']

        self.assertEqual(len(data), 2)

        # results should be ordered by descending cycle start date
        result_1 = data[1]
        self.assertEqual(result_1['address_line_1'], state.address_line_1)
        self.assertEqual(result_1['extra_data']['field_1'], 'value_1')
        self.assertEqual(result_1['cycle_id'], self.cycle.id)
        self.assertEqual(result_1['view_id'], view_1.id)

        result_2 = data[0]
        self.assertEqual(result_2['address_line_1'], state_2.address_line_1)
        self.assertEqual(result_2['extra_data']['field_1'], 'value_2')
        self.assertEqual(result_2['cycle_id'], later_cycle.id)
        self.assertEqual(result_2['view_id'], view_2.id)

    def test_edit_properties_creates_notes_after_initial_edit(self):
        state = self.taxlot_state_factory.get_taxlot_state()
        taxlot = self.taxlot_factory.get_taxlot()
        view = TaxLotView.objects.create(
            taxlot=taxlot, cycle=self.cycle, state=state
        )

        # create the Some Extra Data column so serializers enables edit changes to be tracked by log Notes.
        Column.objects.create(
            column_name="Some Extra Data",
            organization=self.org,
            is_extra_data=True,
            table_name='TaxLotState'
        )

        # update the address
        new_data = {
            "state": {
                "address_line_1": "742 Evergreen Terrace",
                "extra_data": {"Some Extra Data": "111"}
            }
        }
        url = reverse('api:v3:taxlots-detail', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.put(url, json.dumps(new_data), content_type='application/json')

        self.assertEqual(view.notes.count(), 1)

        # update the address again
        new_data = {
            "state": {
                "address_line_1": "123 note street",
                "extra_data": {"Some Extra Data": "222"}
            }
        }
        url = reverse('api:v3:taxlots-detail', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.put(url, json.dumps(new_data), content_type='application/json')

        self.assertEqual(view.notes.count(), 2)
        refreshed_view = TaxLotView.objects.get(id=view.id)
        note = refreshed_view.notes.order_by('created').last()

        expected_log_data = [
            {
                "field": "address_line_1",
                "previous_value": "742 Evergreen Terrace",
                "new_value": "123 note street",
                "state_id": refreshed_view.state_id
            },
            {
                "field": "Some Extra Data",
                "previous_value": "111",
                "new_value": "222",
                "state_id": refreshed_view.state_id
            },
        ]
        self.assertEqual(note.note_type, Note.LOG)
        self.assertEqual(note.name, "Automatically Created")
        # import pdb; pdb.set_trace()
        self.assertCountEqual(note.log_data, expected_log_data)

    def test_first_lat_long_edit(self):
        state = self.taxlot_state_factory.get_taxlot_state()
        taxlot = self.taxlot_factory.get_taxlot()
        view = TaxLotView.objects.create(
            taxlot=taxlot, cycle=self.cycle, state=state
        )

        # update the address
        new_data = {
            "state": {
                "latitude": 39.765251,
                "longitude": -104.986138,
            }
        }
        url = reverse('api:v3:taxlots-detail', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        response = self.client.put(url, json.dumps(new_data), content_type='application/json')
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')

        response = self.client.get(url, content_type='application/json')
        data = json.loads(response.content)

        self.assertEqual(data['status'], 'success')

        self.assertIsNotNone(data['state']['long_lat'])
        self.assertIsNotNone(data['state']['geocoding_confidence'])

    def test_merged_indicators_provided_on_filter_endpoint(self):
        _import_record, import_file_1 = self.create_import_file(self.user, self.org, self.cycle)

        base_details = {
            'custom_id_1': 'CustomID123',
            'import_file_id': import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
            "raw_access_level_instance_id": self.org.root.id,
        }
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file_1 mapping done so that record is "created for users to view".
        import_file_1.mapping_done = True
        import_file_1.save()
        geocode_and_match_buildings_task(import_file_1.id)

        _import_record_2, import_file_2 = self.create_import_file(self.user, self.org, self.cycle)

        url = reverse('api:v3:taxlots-filter') + '?cycle_id={}&organization_id={}&page=1&per_page=999999999'.format(self.cycle.pk, self.org.pk)
        response = self.client.post(url, content_type='application/json')
        data = json.loads(response.content)

        self.assertFalse(data['results'][0]['merged_indicator'])

        # make sure merged_indicator is True when merge occurs
        base_details['city'] = 'Denver'
        base_details['import_file_id'] = import_file_2.id
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file_2 mapping done so that match merging can occur.
        import_file_2.mapping_done = True
        import_file_2.save()
        geocode_and_match_buildings_task(import_file_2.id)

        url = reverse('api:v3:taxlots-filter') + '?cycle_id={}&organization_id={}&page=1&per_page=999999999'.format(self.cycle.pk, self.org.pk)
        response = self.client.post(url, content_type='application/json')
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

        url = reverse('api:v3:taxlots-filter') + '?cycle_id={}&organization_id={}&page=1&per_page=999999999'.format(self.cycle.pk, self.org.pk)
        response = self.client.post(url, content_type='application/json')
        data = json.loads(response.content)

        related = data['results'][0]['related'][0]

        self.assertTrue('merged_indicator' in related)
        self.assertFalse(related['merged_indicator'])

    def test_taxlot_match_merge_link(self):
        base_details = {
            'jurisdiction_tax_lot_id': '123MatchID',
            'no_default_data': False,
        }

        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)
        taxlot = self.taxlot_factory.get_taxlot()
        view_1 = TaxLotView.objects.create(
            taxlot=taxlot, cycle=self.cycle, state=tls_1
        )

        cycle_2 = self.cycle_factory.get_cycle(
            start=datetime(2018, 10, 10, tzinfo=get_current_timezone()))
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)
        taxlot_2 = self.taxlot_factory.get_taxlot()
        TaxLotView.objects.create(
            taxlot=taxlot_2, cycle=cycle_2, state=tls_2
        )

        url = reverse('api:v3:taxlots-match-merge-link', args=[view_1.id])
        url += f'?organization_id={self.org.pk}'
        response = self.client.post(url, content_type='application/json')
        summary = response.json()

        expected_summary = {
            'view_id': None,
            'match_merged_count': 0,
            'match_link_count': 1,
        }
        self.assertEqual(expected_summary, summary)

        refreshed_view_1 = TaxLotView.objects.get(state_id=tls_1.id)
        view_2 = TaxLotView.objects.get(state_id=tls_2.id)
        self.assertEqual(refreshed_view_1.taxlot_id, view_2.taxlot_id)

    def test_taxlot_match_merge_link_different_alis(self):
        base_details = {
            'jurisdiction_tax_lot_id': '123MatchID',
            'no_default_data': False,
        }

        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)
        taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.me_ali)
        view_1 = TaxLotView.objects.create(
            taxlot=taxlot, cycle=self.cycle, state=tls_1
        )

        cycle_2 = self.cycle_factory.get_cycle(
            start=datetime(2018, 10, 10, tzinfo=get_current_timezone()))
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)
        taxlot_2 = self.taxlot_factory.get_taxlot(access_level_instance=self.sister_ali)
        TaxLotView.objects.create(
            taxlot=taxlot_2, cycle=cycle_2, state=tls_2
        )

        url = reverse('api:v3:taxlots-match-merge-link', args=[view_1.id])
        url += f'?organization_id={self.org.pk}'
        response = self.client.post(url, content_type='application/json')

        assert response.status_code == 400
        assert response.json()["message"] == 'This taxlot shares matching criteria with at least one taxlot in a different ali. This should not happen. Please contact your system administrator.'

    def test_taxlots_cycles_list(self):
        # Create TaxLot set in cycle 1
        state = self.taxlot_state_factory.get_taxlot_state(extra_data={"field_1": "value_1"})
        taxlot = self.taxlot_factory.get_taxlot()
        TaxLotView.objects.create(
            taxlot=taxlot, cycle=self.cycle, state=state
        )

        cycle_2 = self.cycle_factory.get_cycle(
            start=datetime(2018, 10, 10, tzinfo=get_current_timezone()))
        state_2 = self.taxlot_state_factory.get_taxlot_state(extra_data={"field_1": "value_2"})
        taxlot_2 = self.taxlot_factory.get_taxlot()
        TaxLotView.objects.create(
            taxlot=taxlot_2, cycle=cycle_2, state=state_2
        )

        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(state)
        # get the columnlistprofile (default) for all columns
        columnlistprofile = self.column_list_factory.get_columnlistprofile(
            inventory_type=VIEW_LIST_TAXLOT,
            columns=['address_line_1', 'field_1'],
            table_name='TaxLotState'
        )

        post_params = json.dumps({
            'organization_id': self.org.pk,
            'profile_id': columnlistprofile.id,
            'cycle_ids': [self.cycle.id, cycle_2.id]
        })
        url = reverse('api:v3:taxlots-filter-by-cycle')
        response = self.client.post(url, post_params, content_type='application/json')
        data = response.json()

        address_line_1_key = 'address_line_1_' + str(columnlistprofile.columns.get(column_name='address_line_1').id)
        field_1_key = 'field_1_' + str(columnlistprofile.columns.get(column_name='field_1').id)

        self.assertEqual(len(data), 2)

        result_1 = data[str(self.cycle.id)]
        self.assertEqual(result_1[0][address_line_1_key], state.address_line_1)
        self.assertEqual(result_1[0][field_1_key], 'value_1')
        self.assertEqual(result_1[0]['id'], taxlot.id)

        result_2 = data[str(cycle_2.id)]
        self.assertEqual(result_2[0][address_line_1_key], state_2.address_line_1)
        self.assertEqual(result_2[0][field_1_key], 'value_2')
        self.assertEqual(result_2[0]['id'], taxlot_2.id)


class TaxlotViewTestPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.cycle = self.cycle_factory.get_cycle()
        self.view = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle)
        self.taxlot = TaxLot.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.label = Label.objects.create(color="red", name="test_label", super_organization=self.org,)
        self.view.labels.add(self.label)
        self.view.taxlot = self.taxlot
        self.view.save()

    def test_taxlot_labels(self):
        url = reverse('api:v3:taxlots-labels') + f'?organization_id={self.org.pk}'

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, content_type='application/json')
        data = resp.json()
        label_data = next(d for d in data if d["name"] == "test_label")
        assert label_data["is_applied"] == [self.view.pk]

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, content_type='application/json')
        data = resp.json()
        label_data = next(d for d in data if d["name"] == "test_label")
        assert "is_applied" not in label_data

    def test_taxlot_list(self):
        url = reverse('api:v3:taxlots-list') + f'?cycle_id={self.cycle.pk}&organization_id={self.org.pk}'

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 1

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 0

    def test_taxlot_filter_by_cycle(self):
        url = reverse('api:v3:taxlots-filter-by-cycle') + f'?organization_id={self.org.pk}'
        params = json.dumps({"cycle_ids": [self.cycle.id], "organization_id": self.org.pk})

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, params, content_type='application/json')
        assert resp.status_code == 200
        assert len(resp.json()[str(self.cycle.id)]) == 1

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, params, content_type='application/json')
        assert resp.status_code == 200
        assert len(resp.json()[str(self.cycle.id)]) == 0

    def test_taxlot_filter(self):
        url = reverse('api:v3:taxlots-filter') + f'?cycle_id={self.cycle.pk}&organization_id={self.org.pk}'

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, content_type='application/json')
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 1

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, content_type='application/json')
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 0

    def test_taxlot_merge(self):
        self.state_2 = self.taxlot_state_factory.get_taxlot_state(address_line_1='2 taxlot state')
        self.taxlot_2 = self.taxlot_factory.get_taxlot()
        self.view_2 = TaxLotView.objects.create(
            taxlot=self.taxlot_2, cycle=self.cycle, state=self.state_2
        )

        # Merge the taxlots
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view.pk]
        })

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, post_params, content_type='application/json')
        assert resp.status_code == 400

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, post_params, content_type='application/json')
        assert resp.status_code == 200

    def test_taxlot_unmerge(self):
        self.state_2 = self.taxlot_state_factory.get_taxlot_state(address_line_1='2 taxlot state')
        self.taxlot_2 = self.taxlot_factory.get_taxlot()
        self.view_2 = TaxLotView.objects.create(
            taxlot=self.taxlot_2, cycle=self.cycle, state=self.state_2
        )
        merged_state = merge_taxlots([self.view.state.pk, self.state_2.pk], self.org.pk, 'Manual Match')
        _, _, view_id = match_merge_link(merged_state.taxlotview_set.first().id, 'TaxLotState')
        view_id = TaxLotView.objects.first().id
        url = reverse('api:v3:taxlots-unmerge', args=[view_id]) + '?organization_id={}'.format(self.org.pk)

        # child member cannot
        self.login_as_child_member()
        response = self.client.post(url, content_type='application/json')
        assert response.status_code == 400

        # root member can
        self.login_as_root_member()
        response = self.client.post(url, content_type='application/json')
        assert response.status_code == 200

    def test_taxlot_links(self):
        url = reverse('api:v3:taxlots-links', args=[self.view.id]) + f'?organization_id={self.org.pk}'

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 404

    def test_taxlot_match_merge_link(self):
        url = reverse('api:v3:taxlots-match-merge-link', args=[self.view.id]) + '?organization_id={}'.format(self.org.pk)

        # root member can
        self.login_as_root_member()
        response = self.client.post(url, content_type='application/json')
        assert response.status_code == 200

        # child member cannot
        self.login_as_child_member()
        response = self.client.post(url, content_type='application/json')
        assert response.status_code == 404

    def test_taxlot_pair(self):
        self.property_view = self.property_view_factory.get_property_view(cycle=self.cycle)
        url = reverse('api:v3:taxlots-pair', args=[self.view.id]) + f'?property_id={self.property_view.pk}&organization_id={self.org.pk}'

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, content_type='application/json')
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.put(url, content_type='application/json')
        assert resp.status_code == 404

    def test_taxlot_unpair(self):
        self.property_view = self.property_view_factory.get_property_view(cycle=self.cycle)
        pair_unpair_property_taxlot(self.view.id, self.property_view.id, self.org.pk, True)
        url = reverse('api:v3:taxlots-unpair', args=[self.view.id]) + f'?property_id={self.property_view.pk}&organization_id={self.org.pk}'

        # child member cannot
        self.login_as_child_member()
        resp = self.client.put(url, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, content_type='application/json')
        assert resp.status_code == 200

    def test_taxlot_batch_delete(self):
        self.state_2 = self.taxlot_state_factory.get_taxlot_state(address_line_1='2 taxlot state')
        self.taxlot_2 = self.taxlot_factory.get_taxlot(access_level_instance=self.child_level_instance)
        self.view_2 = TaxLotView.objects.create(
            taxlot=self.taxlot_2, cycle=self.cycle, state=self.state_2
        )
        url = reverse('api:v3:taxlots-batch-delete') + '?organization_id={}'.format(self.org.pk)
        params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view.pk]
        })

        # child member only deletes the one it has access to.
        self.login_as_child_member()
        resp = self.client.delete(url, params, content_type='application/json')
        assert resp.status_code == 200
        assert resp.json() == {'status': 'success', 'taxlots': 1}

    def test_taxlot_retrieve(self):
        url = reverse('api:v3:taxlots-detail', args=[self.view.id]) + f'?organization_id={self.org.pk}'

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 404

    def test_taxlot_update(self):
        url = reverse('api:v3:taxlots-detail', args=[self.view.id]) + f'?organization_id={self.org.pk}'
        param = json.dumps({"state": {"address_line_1": "742 Evergreen Terrace"}})

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, param, content_type='application/json')
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.put(url, param, content_type='application/json')
        assert resp.status_code == 404


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

        # create tree
        self.org.access_level_names = ["1st Gen", "2nd Gen", "3rd Gen"]
        mom_ali = self.org.add_new_access_level_instance(self.org.root.id, "mom")
        self.me_ali = self.org.add_new_access_level_instance(mom_ali.id, "me")
        self.sister_ali = self.org.add_new_access_level_instance(mom_ali.id, "sister")
        self.org.save()

    def test_taxlots_merge_without_losing_labels(self):
        # Create 3 Labels
        label_factory = FakeStatusLabelFactory(organization=self.org)

        label_1 = label_factory.get_statuslabel()
        label_2 = label_factory.get_statuslabel()
        label_3 = label_factory.get_statuslabel()

        self.view_1.labels.add(label_1, label_2)
        self.view_2.labels.add(label_2, label_3)

        # Merge the taxlots
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]
        })
        self.client.post(url, post_params, content_type='application/json')

        # The resulting -View should have 3 notes
        view = TaxLotView.objects.first()

        self.assertEqual(view.labels.count(), 3)
        label_names = list(view.labels.values_list('name', flat=True))
        self.assertCountEqual(label_names, [label_1.name, label_2.name, label_3.name])

    def test_taxlots_merge_mismatched_alis(self):
        # set taxlots alis
        self.taxlot_1.access_level_instance = self.me_ali
        self.taxlot_1.save()
        self.taxlot_2.access_level_instance = self.sister_ali
        self.taxlot_2.save()

        # Merge the properties
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]
        })
        response = self.client.post(url, post_params, content_type='application/json')

        assert response.status_code == 400
        assert TaxLot.objects.count() == 2

    def test_taxlots_merge_causes_link(self):
        self.state_2.custom_id_1 = 1
        self.state_2.save()

        # create a state in a new cycle whose matching_criteria are the combo of state 1 and 2s.
        self.other_cycle = self.cycle_factory.get_cycle(
            start=datetime(2020, 10, 10, tzinfo=get_current_timezone()))
        self.state_3 = self.taxlot_state_factory.get_taxlot_state()
        self.taxlot_3 = self.taxlot_factory.get_taxlot()
        self.view_3 = TaxLotView.objects.create(
            taxlot=self.taxlot_3, cycle=self.other_cycle, state=self.state_3
        )
        self.state_3.jurisdiction_tax_lot_id = self.state_1.jurisdiction_tax_lot_id
        self.state_3.custom_id_1 = self.state_2.custom_id_1
        self.state_3.save()

        # Merge the taxlots
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]
        })
        response = self.client.post(url, post_params, content_type='application/json')

        assert response.status_code == 200
        assert response.json() == {'status': 'success', 'match_merged_count': 0, 'match_link_count': 1}
        views = TaxLotView.objects.all()
        assert views.count() == 2
        assert list(views.values_list("taxlot_id", flat=True)) == [self.taxlot_3.id, self.taxlot_3.id]

    def test_taxlots_merge_causes_link_mismatched_alis(self):
        self.state_2.custom_id_1 = 1
        self.state_2.save()

        # create a state in a new cycle whose matching_criteria are the combo of state 1 and 2s.
        self.other_cycle = self.cycle_factory.get_cycle(
            start=datetime(2020, 10, 10, tzinfo=get_current_timezone()))
        self.state_3 = self.taxlot_state_factory.get_taxlot_state()
        self.taxlot_3 = self.taxlot_factory.get_taxlot(access_level_instance=self.sister_ali)
        self.view_3 = TaxLotView.objects.create(
            taxlot=self.taxlot_3, cycle=self.other_cycle, state=self.state_3
        )
        self.state_3.jurisdiction_tax_lot_id = self.state_1.jurisdiction_tax_lot_id
        self.state_3.custom_id_1 = self.state_2.custom_id_1
        self.state_3.save()

        # Merge the taxlots
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]
        })
        response = self.client.post(url, post_params, content_type='application/json')

        assert response.status_code == 400
        views = TaxLotView.objects.all()
        assert views.count() == 3

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
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]
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
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]  # priority given to state_1
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
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        self.assertFalse(TaxLotView.objects.filter(taxlot_id=deleted_taxlot_id).exists())
        self.assertFalse(TaxLot.objects.filter(pk=deleted_taxlot_id).exists())

        self.assertEqual(TaxLotView.objects.filter(taxlot_id=persisting_taxlot_id).count(), 1)

    def test_taxlots_unmerge_without_losing_labels(self):
        # Merge the taxlots
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        # Create 3 Labels - add 2 to view
        label_factory = FakeStatusLabelFactory(organization=self.org)

        label_1 = label_factory.get_statuslabel()
        label_2 = label_factory.get_statuslabel()

        view = TaxLotView.objects.first()  # There's only one TaxLotView
        view.labels.add(label_1, label_2)

        # Unmerge the taxlots
        url = reverse('api:v3:taxlots-unmerge', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(url, content_type='application/json')

        for new_view in TaxLotView.objects.all():
            self.assertEqual(new_view.labels.count(), 2)
            label_names = list(new_view.labels.values_list('name', flat=True))
            self.assertCountEqual(label_names, [label_1.name, label_2.name])

    def test_unmerge_results_in_the_use_of_new_canonical_taxlots_and_deletion_of_old_canonical_state_if_unrelated_to_any_views(self):
        # Merge the taxlots
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        # Capture "old" taxlot_id - there's only one TaxLotView
        view = TaxLotView.objects.first()
        taxlot_id = view.taxlot_id

        # Unmerge the taxlots
        url = reverse('api:v3:taxlots-unmerge', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(url, content_type='application/json')

        self.assertFalse(TaxLot.objects.filter(pk=taxlot_id).exists())
        self.assertEqual(TaxLot.objects.count(), 2)

    def test_unmerge_results_in_the_persistence_of_old_canonical_state_if_related_to_any_views(self):
        # Merge the taxlots
        url = reverse('api:v3:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'taxlot_view_ids': [self.view_2.pk, self.view_1.pk]  # priority given to state_1
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
        url = reverse('api:v3:taxlots-unmerge', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(url, content_type='application/json')

        self.assertTrue(TaxLot.objects.filter(pk=view.taxlot_id).exists())
        self.assertEqual(TaxLot.objects.count(), 3)
