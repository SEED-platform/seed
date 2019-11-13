# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from datetime import datetime

from django.core.urlresolvers import reverse, reverse_lazy
from django.test import TestCase
from django.utils import timezone

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.models import OrganizationUser
from seed.models import (
    Column,
    ColumnMapping,
    PropertyView,
    StatusLabel,
    TaxLot,
    TaxLotProperty,
    TaxLotView,
    Unit,
    VIEW_LIST_TAXLOT)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeColumnFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotFactory,
    FakeColumnListSettingsFactory,
)
from seed.utils.organizations import create_organization

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]

from seed.tests.util import DeleteModelsTestCase

COLUMNS_TO_SEND = DEFAULT_CUSTOM_COLUMNS + ['postal_code', 'pm_parent_property_id',
                                            # 'calculated_taxlot_ids', 'primary',
                                            'extra_data_field', 'jurisdiction_tax_lot_id',
                                            'is secret lair',
                                            'paint color', 'number of secret gadgets']


class MainViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

    def test_home(self):
        response = self.client.get(reverse('seed:home'))
        self.assertEqual(200, response.status_code)


class GetDatasetsViewsTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

    def test_get_datasets(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(reverse('api:v2:datasets-list'),
                                   {'organization_id': self.org.pk})
        self.assertEqual(1, len(response.json()['datasets']))

    def test_get_datasets_count(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(reverse('api:v2:datasets-count'),
                                   {'organization_id': self.org.pk})
        self.assertEqual(200, response.status_code)
        j = response.json()
        self.assertEqual(j['status'], 'success')
        self.assertEqual(j['datasets_count'], 1)

    def test_get_datasets_count_invalid(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(reverse('api:v2:datasets-count'),
                                   {'organization_id': 666})
        self.assertEqual(200, response.status_code)
        j = response.json()
        self.assertEqual(j['status'], 'success')
        self.assertEqual(j['datasets_count'], 0)

    def test_get_dataset(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(
            reverse('api:v2:datasets-detail', args=[import_record.pk]) + '?organization_id=' + str(
                self.org.pk)
        )
        self.assertEqual('success', response.json()['status'])

    def test_delete_dataset(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()

        response = self.client.delete(
            reverse_lazy('api:v2:datasets-detail',
                         args=[import_record.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json'
        )
        self.assertEqual('success', response.json()['status'])
        self.assertFalse(
            ImportRecord.objects.filter(pk=import_record.pk).exists())

    def test_update_dataset(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()

        post_data = {
            'dataset': 'new'
        }

        response = self.client.put(
            reverse_lazy('api:v2:datasets-detail',
                         args=[import_record.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
            data=json.dumps(post_data)
        )
        self.assertEqual('success', response.json()['status'])
        self.assertTrue(ImportRecord.objects.filter(pk=import_record.pk,
                                                    name='new').exists())


class ImportFileViewsTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2016, 1, 1, tzinfo=timezone.get_current_timezone()))

        self.import_record = ImportRecord.objects.create(owner=self.user,
                                                         super_organization=self.org)
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            cycle=self.cycle,
            cached_first_row='Name|#*#|Address'
        )

        self.client.login(**user_details)

    def test_get_import_file(self):
        response = self.client.get(
            reverse('api:v2:import_files-detail', args=[self.import_file.pk]))
        self.assertEqual(self.import_file.pk, response.json()['import_file']['id'])

    def test_delete_file(self):
        url = reverse("api:v2:import_files-detail", args=[self.import_file.pk])
        response = self.client.delete(
            url + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        self.assertEqual('success', response.json()['status'])
        self.assertFalse(ImportFile.objects.filter(pk=self.import_file.pk).exists())

    def test_get_matching_and_geocoding_results(self):
        response = self.client.get(
            '/api/v2/import_files/' + str(self.import_file.pk) + '/matching_and_geocoding_results/')
        self.assertEqual('success', response.json()['status'])


class TestMCMViews(TestCase):
    expected_mappings = {
        'address': ['owner_address', 70],
        'building id': ['Building air leakage', 64],
        'name': ['Name of Audit Certification Holder', 47],
        'year built': ['year_built', 50]
    }

    raw_columns_expected = {
        'status': 'success',
        'raw_columns': ['name', 'address', 'year built', 'building id']
    }

    def assert_expected_mappings(self, actual, expected):
        """
        For each k,v pair of form column_name: [dest_col, confidence]
        in actual, assert that expected contains the same column_name
        and dest_col mapping.
        """
        # fields returned by mapping will change depending on the
        # BEDES columns in the database; confidence will also change
        # depending on the columns in the db and the mapper implementation
        for orig_col in actual:
            expected_dest, expected_confidence = expected[orig_col]
            dest_col, suggested_confidence = actual[orig_col]

            # don't assert confidence matches since the implementation
            # is changing and it depends on the mappings in the system
            self.assertEqual(dest_col, expected_dest)

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)

        self.client.login(**user_details)
        self.import_record = ImportRecord.objects.create(
            owner=self.user
        )
        self.import_record.super_organization = self.org
        self.import_record.save()
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            cached_first_row=ROW_DELIMITER.join(
                ['name', 'address', 'year built', 'building id']
            )
        )

    def test_get_column_mapping_suggestions(self):
        response = self.client.get(
            reverse_lazy('api:v2:import_files-mapping-suggestions',
                         args=[self.import_file.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json'
        )
        self.assertEqual('success', response.json()['status'])

    def test_get_column_mapping_suggestions_pm_file(self):
        response = self.client.get(
            reverse_lazy('api:v2:import_files-mapping-suggestions',
                         args=[self.import_file.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        self.assertEqual('success', response.json()['status'])

    def test_get_column_mapping_suggestions_with_columns(self):
        # create some mappings to model columns in the org
        # in order to test that model columns are always
        # only returned as the first 37 building_columns
        raw_col = Column.objects.create(
            organization=self.org,
            column_name='address'
        )
        model_col = Column.objects.create(
            organization=self.org,
            column_name='address_line_1'
        )
        mapping = ColumnMapping.objects.create(
            super_organization=self.org
        )
        mapping.column_raw.add(raw_col)
        mapping.column_mapped.add(model_col)
        mapping.save()

        response = self.client.get(
            reverse_lazy('api:v2:import_files-mapping-suggestions',
                         args=[self.import_file.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        self.assertEqual('success', response.json()['status'])

    def test_get_raw_column_names(self):
        """Good case for ``get_raw_column_names``."""
        resp = self.client.get(
            reverse_lazy('api:v2:import_files-raw-column-names', args=[self.import_file.id]),
            content_type='application/json'
        )

        body = resp.json()
        self.assertDictEqual(body, self.raw_columns_expected)

    def test_save_column_mappings(self):
        self.assertEqual(
            ColumnMapping.objects.filter(super_organization=self.org).count(),
            0
        )

        # create a National Median Site Energy use
        float_unit = Unit.objects.create(unit_name='test energy use intensity',
                                         unit_type=Unit.FLOAT)
        Column.objects.create(
            organization=self.org,
            table_name='PropertyState',
            column_name='Global National Median Site Energy Use',
            unit=float_unit,
            is_extra_data=True)

        resp = self.client.post(
            reverse_lazy('api:v2:import_files-save-column-mappings', args=[self.import_file.id]),
            data=json.dumps({
                'mappings': [
                    {
                        'from_field': 'eui',
                        'to_field': 'site_eui',
                        'to_table_name': 'PropertyState',
                    },
                    {
                        'from_field': 'National Median Site EUI (kBtu/ft2)',
                        'to_field': 'Global National Median Site Energy Use',
                        'to_table_name': 'PropertyState',
                    },
                ]
            }),
            content_type='application/json',
        )

        self.assertDictEqual(resp.json(), {'status': 'success'})

        # test mapping a column that already has a global definition
        # should create a new column for that org with the same data
        # as the global definition
        # NL: There is not a global definition in the test cases, so we created one above.
        energy_use_columns = Column.objects.filter(
            organization=self.org,
            column_name='Global National Median Site Energy Use'
        )

        self.assertEquals(len(energy_use_columns), 1)

        eu_col = energy_use_columns.first()
        self.assertTrue(eu_col.unit is not None)
        self.assertEqual(eu_col.unit.unit_name, 'test energy use intensity')
        self.assertEqual(eu_col.unit.unit_type, Unit.FLOAT)

    def test_save_column_mappings_idempotent(self):
        """We need to make successive calls to save_column_mappings."""
        # Save the first mapping, just like before
        self.assertEqual(ColumnMapping.objects.filter(super_organization=self.org).count(), 0)
        resp = self.client.post(
            reverse_lazy('api:v2:import_files-save-column-mappings', args=[self.import_file.id]),
            data=json.dumps({
                'mappings': [
                    {
                        'from_field': 'eui',
                        'to_field': 'site_eui',
                        'to_table_name': 'PropertyState',
                    },
                ]
            }),
            content_type='application/json',
        )
        self.assertDictEqual(resp.json(), {'status': 'success'})
        self.assertEqual(ColumnMapping.objects.filter(super_organization=self.org).count(), 1)

        # the second user in the org makes the same save, which should not be
        # unique
        user_2_details = {
            'username': 'test_2_user@demo.com',
            'password': 'test_pass',
            'email': 'test_2_user@demo.com',
        }
        user_2 = User.objects.create_superuser(**user_2_details)
        OrganizationUser.objects.create(
            user=user_2, organization=self.org
        )
        self.client.login(**user_2_details)

        self.client.post(
            reverse_lazy('api:v2:import_files-save-column-mappings', args=[self.import_file.id]),
            data=json.dumps({
                'import_file_id': self.import_file.id,
                'mappings': [
                    {
                        'from_field': 'eui',
                        'to_field': 'site_eui',
                        'to_table_name': 'PropertyState',
                    },
                ]
            }),
            content_type='application/json',
        )

        # Sure enough, we haven't created a new ColumnMapping
        self.assertDictEqual(resp.json(), {'status': 'success'})
        self.assertEqual(ColumnMapping.objects.filter(super_organization=self.org).count(), 1)

    def test_progress(self):
        """Make sure we retrieve data from cache properly."""
        progress_data = ProgressData(func_name='fun_func', unique_id=23)
        progress_data.total = 2
        progress_data.save()
        progress_data.step('Some Status Message')  # bump to 50%

        resp = self.client.get(reverse('api:v2:progress-detail', args=[progress_data.key]),
                               content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get('progress', None), 50)
        self.assertEqual(body.get('status_message', None), progress_data.data['status_message'])

    def test_create_dataset(self):
        """tests the create_dataset view, allows duplicate dataset names"""
        DATASET_NAME_1 = 'test_name 1'
        DATASET_NAME_2 = 'city compliance dataset 2014'
        resp = self.client.post(
            reverse_lazy('api:v2:datasets-list') + '?organization_id=' + str(self.org.pk),
            data=json.dumps({
                'name': DATASET_NAME_1,
            }),
            content_type='application/json',
        )
        data = resp.json()
        self.assertEqual(data['name'], DATASET_NAME_1)

        resp = self.client.post(
            reverse_lazy('api:v2:datasets-list') + '?organization_id=' + str(self.org.pk),
            data=json.dumps({
                'name': DATASET_NAME_2,
            }),
            content_type='application/json',
        )
        data = resp.json()

        self.assertEqual(data['name'], DATASET_NAME_2)
        the_id = data['id']

        # ensure future API changes to create_dataset are tested
        self.assertDictEqual(data, {
            'id': the_id,
            'name': DATASET_NAME_2,
            'status': 'success',
        })

        # test duplicate name
        resp = self.client.post(
            reverse_lazy('api:v2:datasets-list') + '?organization_id=' + str(self.org.pk),
            data=json.dumps({
                'name': DATASET_NAME_1,
            }),
            content_type='application/json',
        )
        data_3 = resp.json()
        import_record = ImportRecord.objects.get(pk=data_3['id'])

        # test data set was created properly
        self.assertEqual(data_3['status'], 'success')
        self.assertEqual(data_3['name'], DATASET_NAME_1)
        self.assertNotEqual(data_3['id'], data['id'])
        self.assertEqual(import_record.owner, self.user)
        self.assertEqual(import_record.last_modified_by, self.user)
        self.assertEqual(import_record.app, 'seed')
        self.assertEqual(import_record.name, DATASET_NAME_1)
        self.assertEqual(self.org, import_record.super_organization)


class InventoryViewTests(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_factory = FakeTaxLotFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone()))
        self.status_label = StatusLabel.objects.create(
            name='test', super_organization=self.org
        )
        self.column_list_factory = FakeColumnListSettingsFactory(organization=self.org)

        self.client.login(**user_details)

    def test_get_properties(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )

        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'property'):
            if not c['related']:
                column_name_mappings[c['column_name']] = c['name']

        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': None})
        result = response.json()
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results[column_name_mappings['address_line_1']], state.address_line_1)

    def test_get_properties_profile_id(self):
        state = self.property_state_factory.get_property_state(extra_data={"field_1": "value_1"})
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )

        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(state)
        # get the columnlistsetting (default) for all columns
        columnlistsetting = self.column_list_factory.get_columnlistsettings()

        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'property'):
            if not c['related']:
                column_name_mappings[c['column_name']] = c['name']

        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': columnlistsetting.pk})
        result = response.json()
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results[column_name_mappings['field_1']], state.extra_data['field_1'])

        # test with queryparam

        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999,
            'profile_id', columnlistsetting.pk,
        ))
        result = response.json()
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results[column_name_mappings['field_1']], state.extra_data['field_1'])

    def test_get_properties_cycle_id(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )

        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'property'):
            if not c['related']:
                column_name_mappings[c['column_name']] = c['name']

        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': None})
        result = response.json()
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results[column_name_mappings['address_line_1']], state.address_line_1)

    def test_get_properties_property_extra_data(self):
        extra_data = {
            'is secret lair': True,
            'paint color': 'pink',
            'number of secret gadgets': 5
        }
        state = self.property_state_factory.get_property_state(extra_data=extra_data)

        # Save the columns to the database that are in the extra data
        Column.save_column_names(state)

        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': None})
        result = response.json()
        results = result['results'][0]

        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'property'):
            if not c['related']:
                column_name_mappings[c['column_name']] = c['name']

        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results[column_name_mappings['address_line_1']], state.address_line_1)
        # Extra data is not returned by default
        self.assertNotIn(column_name_mappings['is secret lair'], results)
        self.assertNotIn(column_name_mappings['number of secret gadgets'], results)
        self.assertNotIn(column_name_mappings['paint color'], results)

    def test_get_properties_pint_fields(self):
        state = self.property_state_factory.get_property_state(
            self.org,
            gross_floor_area=3.14159
        )
        prprty = self.property_factory.get_property()
        pv = PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        params = {
            'organization_id': self.org.pk,
            'cycle_id': self.cycle.id
        }
        url = reverse('api:v2:properties-detail', args=[pv.id])
        response = self.client.get(url, params)
        result = response.json()
        self.assertEqual(result['state']['gross_floor_area'], 3.14)

        # test writing the field -- does not work for pint fields, but other fields should persist fine
        # /api/v2/properties/4/?cycle_id=4&organization_id=3
        url = reverse(
            'api:v2:properties-detail', args=[pv.id]
        ) + '?cycle_id=%s&organization_id=%s' % (self.cycle.id, self.org.id)
        params = {
            'state': {
                'gross_floor_area': 11235,
                'site_eui': 90.1,
            }
        }
        response = self.client.put(url, data=json.dumps(params), content_type='application/json')
        result = response.json()
        self.assertEqual(result['state']['gross_floor_area'], 11235.00)
        self.assertEqual(result['state']['site_eui'], 90.10)

    def test_get_properties_with_taxlots(self):
        property_state = self.property_state_factory.get_property_state()
        property_property = self.property_factory.get_property(campus=True)
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            address_line_1=property_state.address_line_1,
            postal_code=property_state.postal_code
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': None})

        column_name_mappings_related = {}
        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'property'):
            if c['related']:
                column_name_mappings_related[c['column_name']] = c['name']
            else:
                column_name_mappings[c['column_name']] = c['name']

        results = response.json()
        self.assertEquals(len(results['results']), 1)
        result = results['results'][0]
        self.assertTrue(result[column_name_mappings['campus']])
        self.assertEquals(len(result['related']), 1)
        related = result['related'][0]
        self.assertEquals(related[column_name_mappings_related['postal_code']],
                          result[column_name_mappings['postal_code']])
        # self.assertEquals(related['primary'], 'P')

    def test_get_properties_with_taxlots_with_footprints(self):
        property_state = self.property_state_factory.get_property_state(
            property_footprint="POLYGON ((0 0, 1 1, 1 0, 0 0))"
        )

        property_property = self.property_factory.get_property(campus=True)
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            address_line_1=property_state.address_line_1,
            postal_code=property_state.postal_code,
            taxlot_footprint="POLYGON ((0 0, 1 1, 1 0, 0 0))"
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': None})

        column_name_mappings_related = {}
        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'property'):
            if c['related']:
                column_name_mappings_related[c['column_name']] = c['name']
            else:
                column_name_mappings[c['column_name']] = c['name']

        results = response.json()
        self.assertEquals(len(results['results']), 1)
        result = results['results'][0]
        self.assertTrue(result[column_name_mappings['campus']])
        self.assertEquals(len(result['related']), 1)
        related = result['related'][0]
        self.assertEquals(related[column_name_mappings_related['postal_code']],
                          result[column_name_mappings['postal_code']])

    def test_get_properties_taxlot_extra_data(self):
        extra_data = {
            'is secret lair': True,
            'paint color': 'pink',
            'number of secret gadgets': 5
        }
        property_state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            address_line_1=property_state.address_line_1,
            postal_code=property_state.postal_code,
            extra_data=extra_data,
        )

        Column.save_column_names(taxlot_state)

        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': None})
        result = response.json()

        column_name_mappings_related = {}
        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'property'):
            if c['related']:
                column_name_mappings_related[c['column_name']] = c['name']
            else:
                column_name_mappings[c['column_name']] = c['name']

        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(len(results['related']), 1)
        # Extra data is not returned by default
        self.assertNotIn('is secret lair', column_name_mappings)
        self.assertNotIn('paint color', column_name_mappings)
        self.assertNotIn('number of secret gadgets', column_name_mappings)

    def test_get_properties_page_not_an_integer(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        response = self.client.post('/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 'one',
            'per_page', 999999999
        ), data={'profile_id': None})
        result = response.json()

        self.assertEquals(len(result['results']), 1)
        pagination = result['pagination']
        self.assertEquals(pagination['page'], 1)
        self.assertEquals(pagination['start'], 1)
        self.assertEquals(pagination['end'], 1)
        self.assertEquals(pagination['num_pages'], 1)
        self.assertEquals(pagination['has_next'], False)
        self.assertEquals(pagination['has_previous'], False)
        self.assertEquals(pagination['total'], 1)

    def test_get_properties_empty_page(self):
        filter_properties_url = '/api/v2/properties/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 10,
            'per_page', 999999999
        )
        response = self.client.post(filter_properties_url, data={'profile_id': None})
        result = response.json()
        self.assertEquals(len(result['results']), 0)
        pagination = result['pagination']
        self.assertEquals(pagination['page'], 1)
        self.assertEquals(pagination['start'], 0)
        self.assertEquals(pagination['end'], 0)
        self.assertEquals(pagination['num_pages'], 1)
        self.assertEquals(pagination['has_next'], False)
        self.assertEquals(pagination['has_previous'], False)
        self.assertEquals(pagination['total'], 0)

    def test_get_property(self):
        property_state = self.property_state_factory.get_property_state()
        property_property = self.property_factory.get_property()
        property_property.save()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        property_view.labels.add(self.status_label)
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        params = {
            'organization_id': self.org.pk
        }
        response = self.client.get(
            '/api/v2/properties/' + str(property_view.id) + '/',
            params
        )
        results = response.json()

        self.assertEqual(results['status'], 'success')

        # there should be 1 history item now because we are creating an audit log entry
        self.assertEqual(len(results['history']), 1)
        self.assertEqual(results['labels'], [self.status_label.pk])
        self.assertEqual(results['changed_fields'], None)

        expected_property = {
            'id': property_property.pk,
            'campus': False,
            'organization': self.org.pk,
            'parent_property': None,
        }
        self.assertDictContainsSubset(expected_property, results['property'])
        self.assertTrue(results['property']['created'])

        state = results['state']
        self.assertEquals(state['id'], property_state.pk)
        self.assertEquals(state['address_line_1'], property_state.address_line_1)

        rcycle = results['cycle']
        self.assertEquals(rcycle['name'], '2010 Annual')
        self.assertEquals(rcycle['user'], self.user.pk)
        self.assertEquals(rcycle['organization'], self.org.pk)

        self.assertEquals(len(results['taxlots']), 1)

        rtaxlot_view = results['taxlots'][0]
        self.assertEqual(rtaxlot_view['id'], taxlot_view.pk)
        self.assertEqual(rtaxlot_view['labels'], [])
        self.assertDictContainsSubset(
            {'id': taxlot.pk, 'organization': self.org.pk},
            rtaxlot_view['taxlot'],
        )

        tcycle = rtaxlot_view['cycle']
        self.assertEquals(tcycle['name'], '2010 Annual')
        self.assertEquals(tcycle['user'], self.user.pk)
        self.assertEquals(tcycle['organization'], self.org.pk)

        tstate = rtaxlot_view['state']
        self.assertEqual(tstate['id'], taxlot_state.pk)
        self.assertEqual(tstate['address_line_1'], taxlot_state.address_line_1)

    def test_get_property_multiple_taxlots(self):
        property_state = self.property_state_factory.get_property_state()
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state_1 = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot_1 = TaxLot.objects.create(organization=self.org)
        taxlot_view_1 = TaxLotView.objects.create(
            taxlot=taxlot_1, state=taxlot_state_1, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view_1,
            cycle=self.cycle
        )
        taxlot_state_2 = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot_2 = TaxLot.objects.create(organization=self.org)
        taxlot_view_2 = TaxLotView.objects.create(
            taxlot=taxlot_2, state=taxlot_state_2, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view_2,
            cycle=self.cycle
        )
        params = {
            'organization_id': self.org.pk
        }
        response = self.client.get('/api/v2/properties/' + str(property_view.id) + '/', params)
        results = response.json()

        rcycle = results['cycle']
        self.assertEquals(rcycle['name'], '2010 Annual')
        self.assertEquals(rcycle['user'], self.user.pk)
        self.assertEquals(rcycle['organization'], self.org.pk)

        self.assertEquals(len(results['taxlots']), 2)

        rtaxlot_view_1 = results['taxlots'][0]
        self.assertEqual(rtaxlot_view_1['id'], taxlot_view_1.pk)
        self.assertEqual(rtaxlot_view_1['labels'], [])
        self.assertDictContainsSubset(
            {'id': taxlot_1.pk, 'organization': self.org.pk},
            rtaxlot_view_1['taxlot'],
        )

        tcycle_1 = rtaxlot_view_1['cycle']
        self.assertEquals(tcycle_1['name'], '2010 Annual')
        self.assertEquals(tcycle_1['user'], self.user.pk)
        self.assertEquals(tcycle_1['organization'], self.org.pk)

        tstate_1 = rtaxlot_view_1['state']
        self.assertEqual(tstate_1['id'], taxlot_state_1.pk)
        self.assertEqual(tstate_1['address_line_1'], taxlot_state_1.address_line_1)

        rtaxlot_view_2 = results['taxlots'][1]
        self.assertEqual(rtaxlot_view_2['id'], taxlot_view_2.pk)
        self.assertEqual(rtaxlot_view_2['labels'], [])
        self.assertDictContainsSubset(
            {'id': taxlot_2.pk, 'organization': self.org.pk},
            rtaxlot_view_2['taxlot'],
        )

        tcycle_2 = rtaxlot_view_2['cycle']
        self.assertEquals(tcycle_2['name'], '2010 Annual')
        self.assertEquals(tcycle_2['user'], self.user.pk)
        self.assertEquals(tcycle_2['organization'], self.org.pk)

        tstate_2 = rtaxlot_view_2['state']
        self.assertEqual(tstate_2['id'], taxlot_state_2.pk)
        self.assertEqual(tstate_2['address_line_1'], taxlot_state_2.address_line_1)

        expected_property = {
            'campus': False,
            'id': property_property.pk,
            'organization': self.org.pk,
            'parent_property': None,
        }
        self.assertDictContainsSubset(expected_property, results['property'])
        state = results['state']
        self.assertEquals(state['address_line_1'], property_state.address_line_1)
        self.assertEquals(state['id'], property_state.pk)

    def test_get_taxlots(self):
        property_state = self.property_state_factory.get_property_state(
            extra_data={'extra_data_field': 'edfval'})
        Column.save_column_names(property_state)
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999,
            'cycle', self.cycle.pk
        ), data={'profile_id': None})
        results = response.json()['results']

        column_name_mappings_related = {}
        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'taxlot'):
            if c['related']:
                column_name_mappings_related[c['column_name']] = c['name']
            else:
                column_name_mappings[c['column_name']] = c['name']

        self.assertEquals(len(results), 1)

        result = results[0]
        self.assertEquals(len(result['related']), 1)
        self.assertEquals(result[column_name_mappings['address_line_1']],
                          taxlot_state.address_line_1)
        self.assertEquals(result[column_name_mappings['block_number']], taxlot_state.block_number)

        related = result['related'][0]
        self.assertEquals(related[column_name_mappings_related['address_line_1']],
                          property_state.address_line_1)
        self.assertEquals(related[column_name_mappings_related['pm_parent_property_id']],
                          property_state.pm_parent_property_id)
        # self.assertEquals(related['calculated_taxlot_ids'], taxlot_state.jurisdiction_tax_lot_id)
        # self.assertEquals(related['calculated_taxlot_ids'], result[column_name_mappings['jurisdiction_tax_lot_id']])
        # self.assertEquals(related['primary'], 'P')
        self.assertNotIn(column_name_mappings_related['extra_data_field'], related)

    def test_get_taxlots_profile_id(self):
        state = self.taxlot_state_factory.get_taxlot_state(extra_data={"field_1": "value_1"})
        taxlot = self.taxlot_factory.get_taxlot()
        TaxLotView.objects.create(
            taxlot=taxlot, cycle=self.cycle, state=state
        )

        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(state)
        # get the columnlistsetting (default) for all columns
        columnlistsetting = self.column_list_factory.get_columnlistsettings(
            inventory_type=VIEW_LIST_TAXLOT
        )

        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'taxlot'):
            if not c['related']:
                column_name_mappings[c['column_name']] = c['name']

        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': columnlistsetting.pk})
        result = response.json()
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results[column_name_mappings['field_1']], state.extra_data['field_1'])

        # test with queryparam

        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999,
            'profile_id', columnlistsetting.pk,
        ))
        result = response.json()
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results[column_name_mappings['field_1']], state.extra_data['field_1'])

    def test_get_taxlots_no_cycle_id(self):
        property_state = self.property_state_factory.get_property_state()
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        url = '/api/v2/taxlots/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999,
        )
        response = self.client.post(url, data={'profile_id': None})
        results = response.json()['results']

        self.assertEquals(len(results), 1)

        property_state_1 = self.property_state_factory.get_property_state()
        property_1 = self.property_factory.get_property()
        property_view_1 = PropertyView.objects.create(
            property=property_1, cycle=self.cycle, state=property_state_1
        )
        TaxLotProperty.objects.create(
            property_view=property_view_1, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        url = '/api/v2/taxlots/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1,
            'per_page', 999999999
        )
        data = {'profile_id': None}
        response = self.client.post(url, data=data)
        result = response.json()

        column_name_mappings_related = {}
        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'taxlot'):
            if c['related']:
                column_name_mappings_related[c['column_name']] = c['name']
            else:
                column_name_mappings[c['column_name']] = c['name']

        self.assertEquals(len(result['results']), 1)
        self.assertEquals(len(result['results'][0]['related']), 2)

        related_1 = result['results'][0]['related'][0]
        related_2 = result['results'][0]['related'][1]
        self.assertEqual(property_state.address_line_1,
                         related_1[column_name_mappings_related['address_line_1']])
        self.assertEqual(property_state_1.address_line_1,
                         related_2[column_name_mappings_related['address_line_1']])
        # self.assertEqual(taxlot_state.jurisdiction_tax_lot_id, related_1['calculated_taxlot_ids'])

    def test_get_taxlots_multiple_taxlots(self):
        property_state = self.property_state_factory.get_property_state(
            extra_data={'extra_data_field': 'edfval'})
        Column.save_column_names(property_state)
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state_1 = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot_1 = TaxLot.objects.create(organization=self.org)
        taxlot_view_1 = TaxLotView.objects.create(
            taxlot=taxlot_1, state=taxlot_state_1, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view_1, cycle=self.cycle
        )
        taxlot_state_2 = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot_2 = TaxLot.objects.create(organization=self.org)
        taxlot_view_2 = TaxLotView.objects.create(
            taxlot=taxlot_2, state=taxlot_state_2, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view_2,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 1,
            'per_page', 999999999
        ), data={'profile_id': None})
        results = response.json()['results']
        self.assertEquals(len(results), 2)

        column_name_mappings_related = {}
        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'taxlot'):
            if c['related']:
                column_name_mappings_related[c['column_name']] = c['name']
            else:
                column_name_mappings[c['column_name']] = c['name']

        result = results[0]
        self.assertEquals(len(result['related']), 1)
        self.assertEquals(result[column_name_mappings['address_line_1']],
                          taxlot_state_1.address_line_1)
        self.assertEquals(result[column_name_mappings['block_number']], taxlot_state_1.block_number)

        related = result['related'][0]
        self.assertEquals(related[column_name_mappings_related['address_line_1']],
                          property_state.address_line_1)
        self.assertEquals(related[column_name_mappings_related['pm_parent_property_id']],
                          property_state.pm_parent_property_id)
        # calculated_taxlot_ids = related['calculated_taxlot_ids'].split('; ')
        # self.assertIn(str(taxlot_state_1.jurisdiction_tax_lot_id), calculated_taxlot_ids)
        # self.assertIn(str(taxlot_state_2.jurisdiction_tax_lot_id), calculated_taxlot_ids)
        # self.assertEquals(related['primary'], 'P')
        self.assertNotIn(column_name_mappings_related['extra_data_field'], related)

        result = results[1]
        self.assertEquals(len(result['related']), 1)
        self.assertEquals(result[column_name_mappings['address_line_1']],
                          taxlot_state_2.address_line_1)
        self.assertEquals(result[column_name_mappings['block_number']], taxlot_state_2.block_number)

        related = result['related'][0]
        self.assertEquals(related[column_name_mappings_related['address_line_1']],
                          property_state.address_line_1)
        self.assertEquals(related[column_name_mappings_related['pm_parent_property_id']],
                          property_state.pm_parent_property_id)

        # calculated_taxlot_ids = related['calculated_taxlot_ids'].split('; ')
        # self.assertIn(str(taxlot_state_1.jurisdiction_tax_lot_id), calculated_taxlot_ids)
        # self.assertIn(str(taxlot_state_2.jurisdiction_tax_lot_id), calculated_taxlot_ids)
        # self.assertEquals(related['primary'], 'P')
        self.assertNotIn(column_name_mappings_related['extra_data_field'], related)

    def test_get_taxlots_extra_data(self):
        property_state = self.property_state_factory.get_property_state()
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code,
            extra_data={'extra_data_field': 'edfval'}
        )
        Column.save_column_names(taxlot_state)
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 1,
            'per_page', 999999999,
        ), data={'profile_id': None})
        results = response.json()['results']

        column_name_mappings_related = {}
        column_name_mappings = {}
        for c in Column.retrieve_all(self.org.pk, 'taxlot'):
            if c['related']:
                column_name_mappings_related[c['column_name']] = c['name']
            else:
                column_name_mappings[c['column_name']] = c['name']

        self.assertEquals(len(results), 1)

        result = results[0]
        self.assertNotIn(column_name_mappings['extra_data_field'], result)

    def test_get_taxlots_page_not_an_integer(self):
        property_state = self.property_state_factory.get_property_state(
            extra_data={'extra_data_field': 'edfval'})
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 'bad',
            'per_page', 999999999,
        ), data={'profile_id': None})
        result = response.json()

        self.assertEquals(len(result['results']), 1)
        pagination = result['pagination']
        self.assertEquals(pagination['page'], 1)
        self.assertEquals(pagination['start'], 1)
        self.assertEquals(pagination['end'], 1)
        self.assertEquals(pagination['num_pages'], 1)
        self.assertEquals(pagination['has_next'], False)
        self.assertEquals(pagination['has_previous'], False)
        self.assertEquals(pagination['total'], 1)

    def test_get_taxlots_empty_page(self):
        property_state = self.property_state_factory.get_property_state(
            extra_data={'extra_data_field': 'edfval'})
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 1,
            'per_page', 999999999,
        ), data={'profile_id': None})
        result = response.json()

        self.assertEquals(len(result['results']), 1)
        pagination = result['pagination']
        self.assertEquals(pagination['page'], 1)
        self.assertEquals(pagination['start'], 1)
        self.assertEquals(pagination['end'], 1)
        self.assertEquals(pagination['num_pages'], 1)
        self.assertEquals(pagination['has_next'], False)
        self.assertEquals(pagination['has_previous'], False)
        self.assertEquals(pagination['total'], 1)

    def test_get_taxlot(self):
        taxlot_state = self.taxlot_state_factory.get_taxlot_state()
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        taxlot_view.labels.add(self.status_label)

        property_state_1 = self.property_state_factory.get_property_state()
        property_property_1 = self.property_factory.get_property()
        property_view_1 = PropertyView.objects.create(
            property=property_property_1, cycle=self.cycle,
            state=property_state_1
        )
        TaxLotProperty.objects.create(
            property_view=property_view_1, taxlot_view=taxlot_view,
            cycle=self.cycle
        )

        property_state_2 = self.property_state_factory.get_property_state()
        property_property_2 = self.property_factory.get_property()
        property_view_2 = PropertyView.objects.create(
            property=property_property_2, cycle=self.cycle,
            state=property_state_2
        )
        TaxLotProperty.objects.create(
            property_view=property_view_2, taxlot_view=taxlot_view,
            cycle=self.cycle
        )

        params = {
            'organization_id': self.org.pk,
        }
        response = self.client.get('/api/v2/taxlots/' + str(taxlot_view.id) + '/', params)
        result = response.json()

        labels = result['labels']
        self.assertEqual(labels, [self.status_label.pk])

        cycle = result['cycle']
        self.assertEqual(cycle['id'], self.cycle.pk)
        self.assertEqual(cycle['name'], self.cycle.name)
        self.assertEqual(cycle['organization'], self.org.pk)
        self.assertEqual(cycle['user'], self.user.pk)

        properties = result['properties']
        self.assertEqual(len(properties), 2)
        self.assertEqual(properties[0]['cycle']['name'], self.cycle.name)
        self.assertEqual(properties[1]['cycle']['name'], self.cycle.name)
        self.assertEqual(
            properties[0]['property']['id'], property_property_1.pk
        )
        self.assertEqual(
            properties[1]['property']['id'], property_property_2.pk
        )
        self.assertEqual(
            properties[0]['state']['address_line_1'],
            property_state_1.address_line_1
        )
        self.assertEqual(
            properties[1]['state']['address_line_1'],
            property_state_2.address_line_1
        )

        state = result['state']
        self.assertEqual(state['id'], taxlot_state.pk)
        self.assertEqual(state['block_number'], taxlot_state.block_number)
        self.assertDictContainsSubset(
            {
                'id': taxlot.pk,
                'organization': self.org.pk
            },
            result['taxlot'],
        )

    def test_get_cycles(self):
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get(
            reverse('api:v2:cycles-list'), params
        )
        results = response.json()
        self.assertEqual(results['status'], 'success')

        self.assertEqual(len(results['cycles']), 2)
        cycle = results['cycles'][0]
        self.assertEqual(cycle['id'], self.cycle.pk)
        self.assertEqual(cycle['name'], self.cycle.name)

    def test_get_property_columns(self):
        self.column_factory.get_column(
            'Property Extra Data Column',
            is_extra_data=True,
            table_name='PropertyState'
        )
        self.column_factory.get_column(
            'Taxlot Extra Data Column',
            is_extra_data=True,
            table_name='TaxLotState'
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get('/api/v2/properties/columns/', params)
        results = response.json()['columns']

        self.assertTrue('id' in results[0])

        # go through and delete all the results.ids so that it is easy to do a compare
        for result in results:
            del result['id']
            del result['name']
            del result['organization_id']

        pm_property_id_col = {
            'table_name': 'PropertyState',
            'column_name': 'pm_property_id',
            'display_name': 'PM Property ID',
            'data_type': 'string',
            'geocoding_order': 0,
            'is_extra_data': False,
            'merge_protection': 'Favor New',
            'sharedFieldType': 'None',
            'pinnedLeft': True,
            'related': False,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': True,
        }
        self.assertIn(pm_property_id_col, results)

        expected_property_extra_data_column = {
            'table_name': 'PropertyState',
            'column_name': 'Property Extra Data Column',
            'display_name': 'Property Extra Data Column',
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'geocoding_order': 0,
            'data_type': 'None',
            'sharedFieldType': 'None',
            'related': False,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
        }
        self.assertIn(expected_property_extra_data_column, results)

        expected_taxlot_extra_data_column = {
            'table_name': 'TaxLotState',
            'column_name': 'Taxlot Extra Data Column',
            'display_name': 'Taxlot Extra Data Column (Tax Lot)',
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'geocoding_order': 0,
            'data_type': 'None',
            'sharedFieldType': 'None',
            'related': True,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
        }
        self.assertIn(expected_taxlot_extra_data_column, results)

    def test_get_taxlot_columns(self):
        self.column_factory.get_column(
            'Property Extra Data Column',
            is_extra_data=True,
            table_name='PropertyState'
        )
        self.column_factory.get_column(
            'Taxlot Extra Data Column',
            is_extra_data=True,
            table_name='TaxLotState'
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get('/api/v2/taxlots/columns/', params)
        results = response.json()['columns']

        self.assertTrue('id' in results[0])

        # go through and delete all the results.ids so that it is easy to do a compare
        for result in results:
            del result['id']
            del result['name']
            del result['organization_id']

        jurisdiction_tax_lot_id_col = {
            'table_name': 'TaxLotState',
            'column_name': 'jurisdiction_tax_lot_id',
            'display_name': 'Jurisdiction Tax Lot ID',
            'is_extra_data': False,
            'merge_protection': 'Favor New',
            'data_type': 'string',
            'geocoding_order': 0,
            'sharedFieldType': 'None',
            'related': False,
            'pinnedLeft': True,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': True,
        }
        self.assertIn(jurisdiction_tax_lot_id_col, results)

        expected_property_extra_data_column = {
            'table_name': 'PropertyState',
            'column_name': 'Property Extra Data Column',
            'display_name': 'Property Extra Data Column (Property)',
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'geocoding_order': 0,
            'data_type': 'None',
            'sharedFieldType': 'None',
            'related': True,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
        }
        self.assertIn(expected_property_extra_data_column, results)

        expected_taxlot_extra_data_column = {
            'table_name': 'TaxLotState',
            'column_name': 'Taxlot Extra Data Column',
            'display_name': 'Taxlot Extra Data Column',
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'geocoding_order': 0,
            'data_type': 'None',
            'sharedFieldType': 'None',
            'related': False,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
        }
        self.assertIn(expected_taxlot_extra_data_column, results)
