# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from datetime import datetime

from django.core.urlresolvers import reverse, reverse_lazy
from django.test import TestCase
from django.utils import timezone

from seed import decorators
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    Column,
    ColumnMapping,
    FLOAT,
    PropertyView,
    StatusLabel,
    TaxLot,
    TaxLotProperty,
    TaxLotView,
    Unit,
)
from seed.test_helpers.fake import (
    FakeCycleFactory, FakeColumnFactory,
    FakePropertyFactory, FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.utils.cache import set_cache

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]

from seed.tests.util import DeleteModelsTestCase

COLUMNS_TO_SEND = DEFAULT_CUSTOM_COLUMNS + ['postal_code', 'pm_parent_property_id',
                                            'calculated_taxlot_ids', 'primary', 'extra_data_field',
                                            'jurisdiction_tax_lot_id', 'is secret lair',
                                            'paint color', 'number of secret gadgets']


class MainViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)
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
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)
        self.client.login(**user_details)

    def test_get_datasets(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(reverse('api:v2:datasets-list'),
                                   {'organization_id': self.org.pk})
        self.assertEqual(1, len(json.loads(response.content)['datasets']))

    def test_get_datasets_count(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(reverse('api:v2:datasets-count'),
                                   {'organization_id': self.org.pk})
        self.assertEqual(200, response.status_code)
        j = json.loads(response.content)
        self.assertEqual(j['status'], 'success')
        self.assertEqual(j['datasets_count'], 1)

    def test_get_datasets_count_invalid(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(reverse('api:v2:datasets-count'),
                                   {'organization_id': 666})
        self.assertEqual(200, response.status_code)
        j = json.loads(response.content)
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
        self.assertEqual('success', json.loads(response.content)['status'])

    def test_delete_dataset(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()

        response = self.client.delete(
            reverse_lazy('api:v2:datasets-detail',
                         args=[import_record.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json'
        )
        self.assertEqual('success', json.loads(response.content)['status'])
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
        self.assertEqual('success', json.loads(response.content)['status'])
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
        self.org = Organization.objects.create()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2016, 1, 1, tzinfo=timezone.get_current_timezone()))
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.import_record = ImportRecord.objects.create(owner=self.user, super_organization=self.org)
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            cycle=self.cycle,
            cached_first_row='Name|#*#|Address'
        )

        self.client.login(**user_details)

    def test_get_import_file(self):
        response = self.client.get(reverse('api:v2:import_files-detail', args=[self.import_file.pk]))
        self.assertEqual(self.import_file.pk, json.loads(response.content)['import_file']['id'])

    def test_delete_file(self):
        url = reverse("api:v2:import_files-detail", args=[self.import_file.pk])
        response = self.client.delete(
            url + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        self.assertEqual('success', json.loads(response.content)['status'])
        self.assertFalse(ImportFile.objects.filter(pk=self.import_file.pk).exists())

    def test_get_matching_results(self):
        response = self.client.get(
            '/api/v2/import_files/' + str(self.import_file.pk) + '/matching_results/')
        self.assertEqual('success', json.loads(response.content)['status'])


# @skip('Fix for new data model')
# class ReportViewsTests(TestCase):
#
#     def setUp(self):
#         user_details = {
#             'username': 'test_user@demo.com',
#             'password': 'test_pass',
#             'email': 'test_user@demo.com'
#         }
#         self.user = User.objects.create_superuser(**user_details)
#         self.org = Organization.objects.create()
#         OrganizationUser.objects.create(user=self.user, organization=self.org)
#
#         self.import_record = ImportRecord.objects.create(owner=self.user)
#         self.import_record.super_organization = self.org
#         self.import_record.save()
#         self.import_file = ImportFile.objects.create(
#             import_record=self.import_record,
#             cached_first_row='Name|#*#|Address'
#         )
#
#         BuildingSnapshot.objects.create(super_organization=self.org,
#                                         import_file=self.import_file)
#
#         self.client.login(**user_details)
#
#     def test_get_building_summary_report_data(self):
#         params = {
#             'start_date': (datetime.now() - timedelta(days=30)).strftime(
#                 '%Y-%m-%d'),
#             'end_date': datetime.now().strftime('%Y-%m-%d'),
#             'organization_id': self.org.pk
#         }
#
#         response = self.client.get(
#             reverse('seed:get_building_summary_report_data'), params)
#         self.assertEqual('success', json.loads(response.content)['status'])
#
#     # TODO replace with test for inventory report
#     @skip('Fix for new data model')
#     def test_get_building_report_data(self):
#         params = {
#             'start_date': (datetime.now() - timedelta(days=30)).strftime(
#                 '%Y-%m-%d'),
#             'end_date': datetime.now().strftime('%Y-%m-%d'),
#             'x_var': 'use_description',
#             'y_var': 'year_built',
#             'organization_id': self.org.pk
#         }
#
#         response = self.client.get(reverse('seed:get_building_report_data'),
#                                    params)
#         self.assertEqual('success', json.loads(response.content)['status'])
#
#     @skip('Fix for new data model')
#     def test_get_inventory_report_data(self):
#         pass  # TODO
#
#     # TODO replace with test for inventory report
#     @skip('Fix for new data model')
#     def test_get_aggregated_building_report_data(self):
#         params = {
#             'start_date': (datetime.now() - timedelta(days=30)).strftime(
#                 '%Y-%m-%d'),
#             'end_date': datetime.now().strftime('%Y-%m-%d'),
#             'x_var': 'energy_score',
#             'y_var': 'year_built',
#             'organization_id': self.org.pk
#         }
#
#         response = self.client.get(
#             reverse('seed:get_aggregated_building_report_data'), params)
#         self.assertEqual('success', json.loads(response.content)['status'])
#
#     @skip('Fix for new data model')
#     def test_get_aggregated_inventory_report_data(self):
#         pass  # TODO


class TestMCMViews(TestCase):
    expected_mappings = {
        u'address': [u'owner_address', 70],
        u'building id': [u'Building air leakage', 64],
        u'name': [u'Name of Audit Certification Holder', 47],
        u'year built': [u'year_built', 50]
    }

    raw_columns_expected = {
        u'status': u'success',
        u'raw_columns': [u'name', u'address', u'year built', u'building id']
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
        self.org = Organization.objects.create()
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
        }
        self.user = User.objects.create_superuser(**user_details)
        OrganizationUser.objects.create(user=self.user, organization=self.org)
        self.client.login(**user_details)
        self.import_record = ImportRecord.objects.create(
            owner=self.user
        )
        self.import_record.super_organization = self.org
        self.import_record.save()
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            cached_first_row=ROW_DELIMITER.join(
                [u'name', u'address', u'year built', u'building id']
            )
        )

    def test_get_column_mapping_suggestions(self):
        response = self.client.get(
            reverse_lazy('api:v2:import_files-mapping-suggestions',
                         args=[self.import_file.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json'
        )
        self.assertEqual('success', json.loads(response.content)['status'])

    def test_get_column_mapping_suggestions_pm_file(self):
        response = self.client.get(
            reverse_lazy('api:v2:import_files-mapping-suggestions',
                         args=[self.import_file.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        self.assertEqual('success', json.loads(response.content)['status'])

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
        self.assertEqual('success', json.loads(response.content)['status'])

    def test_get_raw_column_names(self):
        """Good case for ``get_raw_column_names``."""
        resp = self.client.get(
            reverse_lazy('api:v2:import_files-raw-column-names', args=[self.import_file.id]),
            content_type='application/json'
        )

        body = json.loads(resp.content)

        self.assertDictEqual(body, self.raw_columns_expected)

    def test_save_column_mappings(self):
        self.assertEqual(
            ColumnMapping.objects.filter(super_organization=self.org).count(),
            0
        )

        # create a National Median Site Energy use
        float_unit = Unit.objects.create(unit_name='test energy use intensity',
                                         unit_type=FLOAT)
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

        self.assertDictEqual(json.loads(resp.content), {'status': 'success'})

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
        self.assertEqual(eu_col.unit.unit_type, FLOAT)

    def test_save_column_mappings_idempotent(self):
        """We need to make successive calls to save_column_mappings."""
        # Save the first mapping, just like before
        self.assertEqual(
            ColumnMapping.objects.filter(super_organization=self.org).count(),
            0
        )
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
        self.assertDictEqual(json.loads(resp.content), {'status': 'success'})
        self.assertEqual(
            ColumnMapping.objects.filter(super_organization=self.org).count(),
            1
        )

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
        self.assertDictEqual(json.loads(resp.content), {'status': 'success'})
        self.assertEqual(
            ColumnMapping.objects.filter(super_organization=self.org).count(),
            1
        )

    def test_progress(self):
        """Make sure we retrieve data from cache properly."""
        progress_key = decorators.get_prog_key('fun_func', 23)
        test_progress = {
            'progress': 50.0,
            'status': 'parsing',
            'progress_key': progress_key
        }
        set_cache(progress_key, 'parsing', test_progress)
        resp = self.client.get(reverse('api:v2:progress-detail', args=[progress_key]),
                               content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertEqual(body.get('progress', 0), test_progress['progress'])
        self.assertEqual(body.get('progress_key', ''), progress_key)

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
        data = json.loads(resp.content)
        self.assertEqual(data['name'], DATASET_NAME_1)

        resp = self.client.post(
            reverse_lazy('api:v2:datasets-list') + '?organization_id=' + str(self.org.pk),
            data=json.dumps({
                'name': DATASET_NAME_2,
            }),
            content_type='application/json',
        )
        data = json.loads(resp.content)

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
        data_3 = json.loads(resp.content)
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
        self.org = Organization.objects.create()
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org,
                                              user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.org
        )
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone()))
        self.status_label = StatusLabel.objects.create(
            name='test', super_organization=self.org
        )
        self.client.login(**user_details)

    def test_get_properties(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
            'columns': COLUMNS_TO_SEND,
        }
        response = self.client.get('/api/v2/properties/', params)
        result = json.loads(response.content)
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results['address_line_1'], state.address_line_1)

    def test_get_properties_cycle_id(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        params = {
            'organization_id': self.org.pk,
            'cycle': self.cycle.pk,
            'page': 1,
            'per_page': 999999999,
            'columns': COLUMNS_TO_SEND,
        }
        response = self.client.get('/api/v2/properties/', params)
        result = json.loads(response.content)
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results['address_line_1'], state.address_line_1)

    def test_get_properties_property_extra_data(self):
        extra_data = {
            'is secret lair': True,
            'paint color': 'pink',
            'number of secret gadgets': 5
        }
        state = self.property_state_factory.get_property_state(extra_data=extra_data)
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
            'columns': COLUMNS_TO_SEND,
        }
        response = self.client.get('/api/v2/properties/', params)
        result = json.loads(response.content)
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results['address_line_1'], state.address_line_1)
        self.assertTrue(results['is secret lair'])
        self.assertEquals(results['paint color'], 'pink')
        self.assertEquals(results['number of secret gadgets'], 5)

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
        result = json.loads(response.content)
        self.assertEqual(result['state']['gross_floor_area'], 3.14)

        # test writing the field -- does not work for pint fields, but other fields should persist fine
        # /api/v2/properties/4/?cycle_id=4&organization_id=3
        url = reverse('api:v2:properties-detail', args=[pv.id]) + '?cycle_id=%s&organization_id=%s' % (
            self.cycle.id, self.org.id)
        params = {
            'state': {
                'gross_floor_area': 11235,
                'site_eui': 90.1,
            }
        }
        response = self.client.put(url, data=json.dumps(params), content_type='application/json')
        result = json.loads(response.content)
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
        ), data={'columns': COLUMNS_TO_SEND})
        results = json.loads(response.content)
        self.assertEquals(len(results['results']), 1)
        result = results['results'][0]
        self.assertTrue(result['campus'])
        self.assertEquals(len(result['related']), 1)
        related = result['related'][0]
        self.assertEquals(related['postal_code'], result['postal_code'])
        self.assertEquals(related['primary'], 'P')

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
        ), data={'columns': COLUMNS_TO_SEND})
        result = json.loads(response.content)
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(len(results['related']), 1)
        related = results['related'][0]
        self.assertTrue(related['is secret lair'])
        self.assertEquals(related['paint color'], 'pink')
        self.assertEquals(related['number of secret gadgets'], 5)

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
        ), data={'columns': COLUMNS_TO_SEND})
        result = json.loads(response.content)
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
        response = self.client.post(filter_properties_url, data={'columns': COLUMNS_TO_SEND})
        result = json.loads(response.content)
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
        property_property.labels.add(self.status_label)
        property_property.save()
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
        params = {
            'organization_id': self.org.pk
        }
        response = self.client.get(
            '/api/v2/properties/' + str(property_view.id) + '/',
            params
        )
        results = json.loads(response.content)

        self.assertEqual(results['status'], 'success')

        # there should be 1 history item now because we are creating an audit log entry
        self.assertEqual(len(results['history']), 1)
        self.assertEqual(results['property']['labels'], [self.status_label.pk])
        self.assertEqual(results['changed_fields'], None)

        expected_property = {
            'id': property_property.pk,
            'campus': False,
            'organization': self.org.pk,
            'parent_property': None,
            'labels': [self.status_label.pk]
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

        rtaxlot = results['taxlots'][0]
        self.assertEqual(rtaxlot['id'], taxlot.pk)
        self.assertDictContainsSubset(
            {'id': taxlot.pk, 'organization': self.org.pk, 'labels': []},
            rtaxlot['taxlot'],
        )

        tcycle = rtaxlot['cycle']
        self.assertEquals(tcycle['name'], '2010 Annual')
        self.assertEquals(tcycle['user'], self.user.pk)
        self.assertEquals(tcycle['organization'], self.org.pk)

        tstate = rtaxlot['state']
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
        response = self.client.get(
            '/api/v2/properties/' + str(property_view.id) + '/',
            params
        )
        results = json.loads(response.content)

        rcycle = results['cycle']
        self.assertEquals(rcycle['name'], '2010 Annual')
        self.assertEquals(rcycle['user'], self.user.pk)
        self.assertEquals(rcycle['organization'], self.org.pk)

        self.assertEquals(len(results['taxlots']), 2)

        rtaxlot_1 = results['taxlots'][0]
        self.assertEqual(rtaxlot_1['id'], taxlot_1.pk)
        self.assertDictContainsSubset(
            {'id': taxlot_1.pk, 'organization': self.org.pk, 'labels': []},
            rtaxlot_1['taxlot'],
        )

        tcycle_1 = rtaxlot_1['cycle']
        self.assertEquals(tcycle_1['name'], '2010 Annual')
        self.assertEquals(tcycle_1['user'], self.user.pk)
        self.assertEquals(tcycle_1['organization'], self.org.pk)

        tstate_1 = rtaxlot_1['state']
        self.assertEqual(tstate_1['id'], taxlot_state_1.pk)
        self.assertEqual(tstate_1['address_line_1'], taxlot_state_1.address_line_1)

        rtaxlot_2 = results['taxlots'][1]
        self.assertEqual(rtaxlot_2['id'], taxlot_2.pk)
        self.assertDictContainsSubset(
            {'id': taxlot_2.pk, 'organization': self.org.pk, 'labels': []},
            rtaxlot_2['taxlot'],
        )

        tcycle_2 = rtaxlot_2['cycle']
        self.assertEquals(tcycle_2['name'], '2010 Annual')
        self.assertEquals(tcycle_2['user'], self.user.pk)
        self.assertEquals(tcycle_2['organization'], self.org.pk)

        tstate_2 = rtaxlot_2['state']
        self.assertEqual(tstate_2['id'], taxlot_state_2.pk)
        self.assertEqual(tstate_2['address_line_1'], taxlot_state_2.address_line_1)

        expected_property = {
            'campus': False,
            'id': property_property.pk,
            'labels': [],
            'organization': self.org.pk,
            'parent_property': None,
        }
        self.assertDictContainsSubset(expected_property, results['property'])

        state = results['state']
        self.assertEquals(state['address_line_1'], property_state.address_line_1)
        self.assertEquals(state['id'], property_state.pk)

    def test_get_taxlots(self):
        property_state = self.property_state_factory.get_property_state(extra_data={'extra_data_field': 'edfval'})
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
        ), data={'columns': COLUMNS_TO_SEND})
        results = json.loads(response.content)['results']

        self.assertEquals(len(results), 1)

        result = results[0]
        self.assertEquals(len(result['related']), 1)
        self.assertEquals(result['address_line_1'], taxlot_state.address_line_1)
        self.assertEquals(result['block_number'], taxlot_state.block_number)

        related = result['related'][0]
        self.assertEquals(related['address_line_1'], property_state.address_line_1)
        self.assertEquals(related['pm_parent_property_id'], property_state.pm_parent_property_id)
        self.assertEquals(related['calculated_taxlot_ids'], taxlot_state.jurisdiction_tax_lot_id)
        self.assertEquals(related['calculated_taxlot_ids'], result['jurisdiction_tax_lot_id'])
        self.assertEquals(related['primary'], 'P')
        self.assertIn('extra_data_field', related)
        self.assertEquals(related['extra_data_field'], 'edfval')

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
        url = '/api/v2/taxlots/filter/?{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'page', 1
        )
        response = self.client.post(url, data={'columns': COLUMNS_TO_SEND})
        results = json.loads(response.content)['results']

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
        data = {'columns': COLUMNS_TO_SEND}
        response = self.client.post(url, data=data)
        result = json.loads(response.content)
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(len(result['results'][0]['related']), 2)

        related_1 = result['results'][0]['related'][0]
        related_2 = result['results'][0]['related'][1]
        self.assertEqual(
            property_state.address_line_1, related_1['address_line_1']
        )
        self.assertEqual(
            property_state_1.address_line_1, related_2['address_line_1']
        )
        self.assertEqual(
            taxlot_state.jurisdiction_tax_lot_id,
            related_1['calculated_taxlot_ids']
        )

    def test_get_taxlots_multiple_taxlots(self):
        property_state = self.property_state_factory.get_property_state(extra_data={'extra_data_field': 'edfval'})
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
        ), data={'columns': COLUMNS_TO_SEND})
        results = json.loads(response.content)['results']
        self.assertEquals(len(results), 2)

        result = results[0]
        self.assertEquals(len(result['related']), 1)
        self.assertEquals(result['address_line_1'], taxlot_state_1.address_line_1)
        self.assertEquals(result['block_number'], taxlot_state_1.block_number)

        related = result['related'][0]
        self.assertEquals(related['address_line_1'], property_state.address_line_1)
        self.assertEquals(related['pm_parent_property_id'], property_state.pm_parent_property_id)
        calculated_taxlot_ids = related['calculated_taxlot_ids'].split('; ')
        self.assertIn(str(taxlot_state_1.jurisdiction_tax_lot_id), calculated_taxlot_ids)
        self.assertIn(str(taxlot_state_2.jurisdiction_tax_lot_id), calculated_taxlot_ids)
        self.assertEquals(related['primary'], 'P')
        self.assertIn('extra_data_field', related)
        self.assertEquals(related['extra_data_field'], 'edfval')

        result = results[1]
        self.assertEquals(len(result['related']), 1)
        self.assertEquals(result['address_line_1'], taxlot_state_2.address_line_1)
        self.assertEquals(result['block_number'], taxlot_state_2.block_number)

        related = result['related'][0]
        self.assertEquals(related['address_line_1'], property_state.address_line_1)
        self.assertEquals(related['pm_parent_property_id'], property_state.pm_parent_property_id)

        calculated_taxlot_ids = related['calculated_taxlot_ids'].split('; ')
        self.assertIn(str(taxlot_state_1.jurisdiction_tax_lot_id), calculated_taxlot_ids)
        self.assertIn(str(taxlot_state_2.jurisdiction_tax_lot_id), calculated_taxlot_ids)
        self.assertEquals(related['primary'], 'P')
        self.assertIn('extra_data_field', related)
        self.assertEquals(related['extra_data_field'], 'edfval')

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
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 1
        ), data={'columns': COLUMNS_TO_SEND})
        results = json.loads(response.content)['results']

        self.assertEquals(len(results), 1)

        result = results[0]
        self.assertIn('extra_data_field', result)
        self.assertEquals(result['extra_data_field'], 'edfval')
        self.assertEquals(len(result['related']), 1)

    def test_get_taxlots_page_not_an_integer(self):
        property_state = self.property_state_factory.get_property_state(extra_data={'extra_data_field': 'edfval'})
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
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 'bad'
        ), data={'columns': COLUMNS_TO_SEND})
        result = json.loads(response.content)

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
        property_state = self.property_state_factory.get_property_state(extra_data={'extra_data_field': 'edfval'})
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
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 'bad'
        ), data={'columns': COLUMNS_TO_SEND})
        result = json.loads(response.content)

        self.assertEquals(len(result['results']), 1)
        pagination = result['pagination']
        self.assertEquals(pagination['page'], 1)
        self.assertEquals(pagination['start'], 1)
        self.assertEquals(pagination['end'], 1)
        self.assertEquals(pagination['num_pages'], 1)
        self.assertEquals(pagination['has_next'], False)
        self.assertEquals(pagination['has_previous'], False)
        self.assertEquals(pagination['total'], 1)

    def test_get_taxlots_missing_jurisdiction_tax_lot_id(self):
        property_state = self.property_state_factory.get_property_state(extra_data={'extra_data_field': 'edfval'})
        property_property = self.property_factory.get_property(self.org)
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            postal_code=property_state.postal_code,
            jurisdiction_tax_lot_id=None
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post('/api/v2/taxlots/filter/?{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 'bad'
        ), data={'columns': COLUMNS_TO_SEND})
        related = json.loads(response.content)['results'][0]['related'][0]
        self.assertEqual(related['calculated_taxlot_ids'], 'Missing')

    def test_get_taxlot(self):
        taxlot_state = self.taxlot_state_factory.get_taxlot_state()
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot.labels.add(self.status_label)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )

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
        result = json.loads(response.content)

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
                'labels': [self.status_label.pk],
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
        results = json.loads(response.content)
        self.assertEqual(results['status'], 'success')

        self.assertEqual(len(results['cycles']), 2)
        cycle = results['cycles'][0]
        self.assertEqual(cycle['id'], self.cycle.pk)
        self.assertEqual(cycle['name'], self.cycle.name)

    def test_get_property_columns(self):
        self.column_factory.get_column(
            'property_extra_data_column',
            is_extra_data=True,
            table_name='PropertyState'
        )
        self.column_factory.get_column(
            'taxlot_extra_data_column',
            is_extra_data=True,
            table_name='TaxLotState'
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get('/api/v2/properties/columns/', params)
        results = json.loads(response.content)['columns']

        self.assertTrue('id' in results[0].keys())

        # go through and delete all the results.ids so that it is easy to do a compare
        for result in results:
            del result['id']
            
        pm_property_id_col = {
            'name': 'pm_property_id',
            'dbName': 'pm_property_id',
            'table': 'PropertyState',
            'displayName': 'PM Property ID',
            'dataType': 'string',
            'sharedFieldType': 'None',
            'pinnedLeft': True,
            'related': False,
        }
        self.assertIn(pm_property_id_col, results)

        expected_property_extra_data_column = {
            'extraData': True,
            'name': 'property_extra_data_column',
            'dbName': 'property_extra_data_column',
            'table': 'PropertyState',
            'displayName': 'Property Extra Data Column',
            'sharedFieldType': 'None',
            'related': False,
        }
        self.assertIn(expected_property_extra_data_column, results)

        expected_taxlot_extra_data_column = {
            'extraData': True,
            'table': 'TaxLotState',
            'name': 'taxlot_extra_data_column',
            'dbName': 'taxlot_extra_data_column',
            'displayName': 'Taxlot Extra Data Column',
            'sharedFieldType': 'None',
            'related': True,
        }
        self.assertIn(expected_taxlot_extra_data_column, results)

    def test_get_taxlot_columns(self):
        self.column_factory.get_column(
            'property_extra_data_column',
            is_extra_data=True,
            table_name='PropertyState'
        )
        self.column_factory.get_column(
            'taxlot_extra_data_column',
            is_extra_data=True,
            table_name='TaxLotState'
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get('/api/v2/taxlots/columns/', params)
        results = json.loads(response.content)['columns']

        self.assertTrue('id' in results[0].keys())

        # go through and delete all the results.ids so that it is easy to do a compare
        for result in results:
            del result['id']

        jurisdiction_tax_lot_id_col = {
            'name': 'jurisdiction_tax_lot_id',
            'dbName': 'jurisdiction_tax_lot_id',
            'table': 'TaxLotState',
            'displayName': 'Jurisdiction Tax Lot ID',
            'dataType': 'string',
            'sharedFieldType': 'None',
            'pinnedLeft': True,
            'related': False,
        }
        self.assertIn(jurisdiction_tax_lot_id_col, results)

        expected_property_extra_data_column = {
            'extraData': True,
            'name': 'property_extra_data_column',
            'dbName': 'property_extra_data_column',
            'table': 'PropertyState',
            'displayName': u'Property Extra Data Column',
            'sharedFieldType': 'None',
            'related': True,
        }
        self.assertIn(expected_property_extra_data_column, results)

        expected_taxlot_extra_data_column = {
            'extraData': True,
            'name': 'taxlot_extra_data_column',
            'dbName': 'taxlot_extra_data_column',
            'table': 'TaxLotState',
            'displayName': 'Taxlot Extra Data Column',
            'sharedFieldType': 'None',
            'related': False,
        }
        self.assertIn(expected_taxlot_extra_data_column, results)
