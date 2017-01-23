# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from datetime import date, datetime, timedelta
from unittest import skip

from django.core.cache import cache
from django.core.urlresolvers import reverse, reverse_lazy
from django.test import TestCase

from seed import decorators
from seed.audit_logs.models import AuditLog, LOG
from seed.data_importer.models import ImportFile, ImportRecord
from seed.factory import SEEDFactory
from seed.landing.models import SEEDUser as User
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    ASSESSED_RAW,
    ASSESSED_BS,
    BuildingSnapshot,
    CanonicalBuilding,
    COMPOSITE_BS,
    Column,
    ColumnMapping,
    Cycle,
    FLOAT,
    PORTFOLIO_BS,
    Property,
    ProjectBuilding,
    PropertyState,
    PropertyView,
    StatusLabel,
    TaxLot,
    TaxLotProperty,
    TaxLotState,
    TaxLotView,
    Unit,
)
from seed.test_helpers.fake import (
    FakeCycleFactory, FakeColumnFactory,
    FakePropertyFactory, FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.tests import util as test_util
from seed.utils.cache import set_cache, get_cache
from seed.views.main import (
    DEFAULT_CUSTOM_COLUMNS,
    _parent_tree_coparents,
)

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

    def test_export_buildings(self):
        cb = CanonicalBuilding(active=True)
        cb.save()
        b = SEEDFactory.building_snapshot(canonical_building=cb)
        cb.canonical_snapshot = b
        cb.save()
        b.super_organization = self.org
        b.save()

        payload = {
            "export_name": "My Export",
            "export_type": "csv",
            "selected_buildings": [b.pk]
        }
        response = self.client.post(reverse('seed:export_buildings'),
                                    json.dumps(payload),
                                    content_type='application/json')
        self.assertTrue(json.loads(response.content)['success'])

    def test_export_buildings_empty(self):
        payload = {
            "export_name": "My Export",
            "export_type": "csv",
            "selected_buildings": []
        }
        response = self.client.post(reverse('seed:export_buildings'),
                                    json.dumps(payload),
                                    content_type='application/json')
        self.assertTrue(json.loads(response.content)['success'])

    def test_export_buildings_progress(self):
        payload = {
            "export_id": "1234"
        }
        cache.set('export_buildings__1234',
                  {'progress': 85, 'total_buildings': 1, 'status': 'success'})
        response = self.client.post(reverse('seed:export_buildings_progress'),
                                    json.dumps(payload),
                                    content_type='application/json')
        self.assertTrue(json.loads(response.content)['success'])


class DefaultColumnsViewTests(TestCase):
    """
    Tests of the SEED default custom saved columns
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        Column.objects.create(column_name='test')
        Column.objects.create(column_name='extra_data_test',
                              is_extra_data=True)

        self.client.login(**user_details)

    def test_get_default_columns_with_set_columns(self):
        columns = ["source_facility_id", "test_column_0"]
        self.user.default_custom_columns = columns
        self.user.save()
        columns = ["source_facility_id", "test_column_0"]
        url = reverse_lazy("seed:get_default_columns")
        response = self.client.get(url)
        json_string = response.content
        data = json.loads(json_string)

        self.assertEqual(200, response.status_code)
        self.assertEqual(data['columns'], columns)

    def test_get_default_columns_initial_state(self):
        url = reverse_lazy("seed:get_default_columns")
        response = self.client.get(url)
        json_string = response.content
        data = json.loads(json_string)

        self.assertEqual(200, response.status_code)
        self.assertEqual(data['columns'], DEFAULT_CUSTOM_COLUMNS)

    def test_set_default_columns(self):
        url = reverse_lazy("seed:set_default_columns")
        columns = ['s', 'c1', 'c2']
        post_data = {
            'columns': columns,
            'show_shared_buildings': True
        }
        # set the columns
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)
        self.assertEqual(200, response.status_code)

        # get the columns
        url = reverse_lazy("seed:get_default_columns")
        response = self.client.get(url)
        json_string = response.content
        data = json.loads(json_string)
        self.assertEqual(data['columns'], columns)

        # get show_shared_buildings
        url = reverse_lazy("apiv2:users-shared-buildings", args=[self.user.pk])
        response = self.client.get(url)
        json_string = response.content
        data = json.loads(json_string)
        self.assertEqual(data['show_shared_buildings'], True)

        # set show_shared_buildings to False
        post_data['show_shared_buildings'] = False
        url = reverse_lazy("seed:set_default_columns")
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)
        self.assertEqual(200, response.status_code)

        # get show_shared_buildings
        url = reverse_lazy("apiv2:users-shared-buildings", args=[self.user.pk])
        response = self.client.get(url)
        json_string = response.content
        data = json.loads(json_string)
        self.assertEqual(data['show_shared_buildings'], False)

    def test_get_columns(self):
        url = reverse_lazy("seed:get_columns")

        # test building list columns
        response = self.client.get(
            url,
            {
                'organization_id': self.org.id
            }
        )

        data = json.loads(response.content)
        self.assertEqual(data['fields'][0], {
            u'checked': False,
            u'class': u'is_aligned_right',
            u'field_type': u'building_information',
            u'link': True,
            u'sort_column': u'address_line_1',
            u'sortable': True,
            u'static': False,
            u'title': u'Address Line 1',
            u'type': u'string',
        })

        # test org settings columns
        response = self.client.get(
            url,
            {
                'organization_id': self.org.id,
                'all_fields': "true"
            }
        )

    def tearDown(self):
        self.user.delete()


class SearchViewTests(TestCase):
    """
    Tests of the SEED search_buildings
    """

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

    @skip("Fix for new data model")
    def test_search_active_canonicalbuildings(self):
        """
        tests the search_buildings method used throughout the app for only
        returning active CanonicalBuilding BuildingSnapshot instances.
        """
        # arrange
        NUMBER_ACTIVE = 50
        NUMBER_INACTIVE = 25
        NUMBER_WITHOUT_CANONICAL = 5
        NUMBER_PER_PAGE = 10
        for i in range(NUMBER_ACTIVE):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(canonical_building=cb)
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.org
            b.save()
        for i in range(NUMBER_INACTIVE):
            cb = CanonicalBuilding(active=False)
            cb.save()
            b = SEEDFactory.building_snapshot(canonical_building=cb)
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.org
            b.save()
        for i in range(NUMBER_WITHOUT_CANONICAL):
            b = SEEDFactory.building_snapshot()
            b.super_organization = self.org
            b.save()
        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {},
            'number_per_page': NUMBER_PER_PAGE,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(
            BuildingSnapshot.objects.all().count(),
            NUMBER_ACTIVE + NUMBER_INACTIVE + NUMBER_WITHOUT_CANONICAL
        )
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], NUMBER_ACTIVE)
        self.assertEqual(data['number_returned'], NUMBER_PER_PAGE)
        self.assertEqual(len(data['buildings']), NUMBER_PER_PAGE)

    @skip("Fix for new data model")
    def test_search_sort(self):
        """
        tests the search_buildings method used throughout the app for only
        returning active CanonicalBuilding BuildingSnapshot instances.
        """
        # arrange
        NUMBER_ACTIVE = 10  # if more than 10, then alpha sort puts 11 before 2
        NUMBER_PER_PAGE = 10
        for i in range(NUMBER_ACTIVE):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(
                canonical_building=cb,
                tax_lot_id="%s" % i
            )
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.org
            b.save()
        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {},
            'number_per_page': NUMBER_PER_PAGE,
            'order_by': 'tax_lot_id',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['buildings'][0]['tax_lot_id'], '0')
        self.assertEqual(data['buildings'][9]['tax_lot_id'], '9')

        # sort reverse
        # arrange
        post_data['sort_reverse'] = True

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['buildings'][0]['tax_lot_id'], '9')
        self.assertEqual(data['buildings'][9]['tax_lot_id'], '0')

    @skip("Fix for new data model")
    def test_search_extra_data(self):
        """
        tests the search_buildings method used throughout the app for only
        returning active CanonicalBuilding BuildingSnapshot instances.
        """
        # arrange
        NUMBER_ACTIVE = 10  # if more than 10, then alpha sort puts 11 before 2
        NUMBER_PER_PAGE = 10
        for i in range(NUMBER_ACTIVE):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(
                canonical_building=cb,
                tax_lot_id="%s" % i
            )
            if i > 4:
                b.extra_data = {
                    'nearest national park': 'mt hood'
                }
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.org
            b.save()
        url = reverse_lazy("seed:search_buildings")
        # filters on DB column and extra_data json field
        post_data = {
            'filter_params': {
                'tax_lot_id': '7',
                'nearest national park': 'hood'
            },
            'number_per_page': NUMBER_PER_PAGE,
            'order_by': 'tax_lot_id',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['buildings']), 1)
        self.assertEqual(data['buildings'][0]['tax_lot_id'], '7')
        self.assertEqual(
            data['buildings'][0]['extra_data']['nearest national park'],
            'mt hood'
        )

        # sort reverse
        # arrange
        post_data['sort_reverse'] = True
        post_data['filter_params'] = {
            'nearest national park': 'hood'
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['buildings'][0]['tax_lot_id'], '9')
        self.assertEqual(data['buildings'][4]['tax_lot_id'], '5')

    @skip("Fix for new data model")
    def test_sort_extra_data(self):
        """
        Tests that sorting on extra data takes the column type
        into account.
        """
        # arrange
        float_unit = Unit.objects.create(
            unit_name='test float unit',
            unit_type=FLOAT
        )

        ed_col_name = 'some float column'
        float_col = Column.objects.create(
            organization=self.org,
            column_name=ed_col_name,
            unit=float_unit,
        )

        test_mapping = ColumnMapping.objects.create(
            super_organization=self.org,
        )

        test_mapping.column_mapped.add(float_col)

        NUMBER_ACTIVE = 10  # if more than 10, then alpha sort puts 11 before 2
        NUMBER_PER_PAGE = 10
        for i in range(NUMBER_ACTIVE):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(
                organization=self.org,
                canonical_building=cb,
                tax_lot_id="%s" % i
            )
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.org
            b.extra_data = {
                ed_col_name: str(i * 13.17)
            }
            b.save()
        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {},
            'number_per_page': NUMBER_PER_PAGE,
            'order_by': ed_col_name,
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')

        float_col_data = map(lambda b: b['extra_data'][ed_col_name],
                             data['buildings'])
        expected_data = map(
            lambda b: b.extra_data[ed_col_name],
            BuildingSnapshot.objects.order_by('pk')
        )

        self.assertEqual(float_col_data, expected_data)

        # sort reverse
        # arrange
        post_data['sort_reverse'] = True

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')

        float_col_data = map(lambda b: b['extra_data'][ed_col_name],
                             data['buildings'])
        expected_data.reverse()  # in-place mutation!

        self.assertEqual(float_col_data, expected_data)

    def test_search_filter_range(self):
        """
        Tests search_buildings method when called with a range.
        """
        # arrange
        NUMBER_ACTIVE = 10  # if more than 10, then alpha sort puts 11 before 2
        NUMBER_PER_PAGE = 10
        for i in range(NUMBER_ACTIVE):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(
                canonical_building=cb,
                tax_lot_id="%s" % i,
                year_built=(i + 1)
            )
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.org
            b.save()
        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                # should return 3 buildings with years built of:
                # 5, 6, and 7
                'year_built__gte': 5,
                'year_built__lte': 7
            },
            'number_per_page': NUMBER_PER_PAGE,
            'order_by': 'year_built',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 3)
        self.assertEqual(len(data['buildings']), 3)
        self.assertEqual(data['buildings'][0]['year_built'], 5)
        self.assertEqual(data['buildings'][1]['year_built'], 6)
        self.assertEqual(data['buildings'][2]['year_built'], 7)

    @skip("Fix for new data model")
    def test_search_filter_date_range_ISO8601(self):
        cb = CanonicalBuilding(active=True)
        cb.save()
        b = SEEDFactory.building_snapshot(
            canonical_building=cb,
            tax_lot_id="1",
            year_ending=date(year=2015, month=1, day=1)
        )
        cb.canonical_snapshot = b
        cb.save()
        b.super_organization = self.org
        b.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'year_ending__gte': '2014-01-01T00:00:00.000Z',
                'year_ending__lte': '2016-01-01T00:00:00.000Z'
            },
            'number_per_page': 100,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 1)
        self.assertEqual(len(data['buildings']), 1)

    @skip("Fix for new data model")
    def test_search_exact_match(self):
        """
        Tests search_buildings method when called with an exact match.
        """

        # Uppercase address
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            address_line_1="Address"
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        # Lowercase address
        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            address_line_1="address"
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'address_line_1': '"Address"'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 1)
        self.assertEqual(len(data['buildings']), 1)
        self.assertEqual(data['buildings'][0]['address_line_1'], 'Address')

    @skip("Fix for new data model")
    def test_search_case_insensitive_exact_match(self):
        """
        Tests search_buildings method when called with a case insensitive exact match.
        """

        # Uppercase address
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            address_line_1="Address"
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        # Lowercase address
        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            address_line_1="address"
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        # Additional words
        cb3 = CanonicalBuilding(active=True)
        cb3.save()
        b3 = SEEDFactory.building_snapshot(
            canonical_building=cb3,
            address_line_1="fake address"
        )
        cb3.canonical_snapshot = b3
        cb3.save()
        b3.super_organization = self.org
        b3.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'address_line_1': '^"Address"'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 2)
        self.assertEqual(len(data['buildings']), 2)

        addresses = []

        addresses.append(data['buildings'][0]['address_line_1'])
        addresses.append(data['buildings'][1]['address_line_1'])

        self.assertIn('address', addresses)
        self.assertIn('Address', addresses)
        self.assertNotIn('fake address', addresses)

    @skip("Fix for new data model")
    def test_search_empty_column(self):
        """
        Tests search_buildings method when called with an empty column query.
        """

        # Empty column
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            address_line_1=""
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        # Populated column
        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            address_line_1="Address"
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'address_line_1': '""'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 1)
        self.assertEqual(len(data['buildings']), 1)
        self.assertEqual(data['buildings'][0]['address_line_1'], '')
        self.assertEqual(data['buildings'][0]['pk'], b1.pk)

    @skip("Fix for new data model")
    def test_search_not_empty_column(self):
        """
        Tests search_buildings method when called with a not-empty column query.
        """

        # Empty column
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            address_line_1=""
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        # Populated column
        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            address_line_1="Address"
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'address_line_1': '!""'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 1)
        self.assertEqual(len(data['buildings']), 1)
        self.assertEqual(data['buildings'][0]['address_line_1'], 'Address')
        self.assertEqual(data['buildings'][0]['pk'], b2.pk)

    @skip("Fix for new data model")
    def test_search_extra_data_exact_match(self):
        """Exact match on extra_data json keys"""
        # Uppercase
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            extra_data={'testing': 'TEST'}
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        # Lowercase
        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            extra_data={'testing': 'test'}
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'testing': '"TEST"'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 1)
        self.assertEqual(len(data['buildings']), 1)
        self.assertEqual(data['buildings'][0]['pk'], b1.pk)

    @skip("Fix for new data model")
    def test_search_extra_data_non_existent_column(self):
        """
        Empty column query on extra_data key should match key not existing in JsonField.
        """
        # Empty column
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            extra_data={}
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        # Populated column
        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            extra_data={'testing': 'test'}
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'testing': '""'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 1)
        self.assertEqual(len(data['buildings']), 1)
        self.assertEqual(data['buildings'][0]['pk'], b1.pk)

    @skip("Fix for new data model")
    def test_search_extra_data_empty_column(self):
        """
        Empty column query on extra_data key should match key's value being empty in JsonField.
        """
        # Empty column
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            extra_data={'testing': ''}
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        # Populated column
        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            extra_data={'testing': 'test'}
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'testing': '""'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 1)
        self.assertEqual(len(data['buildings']), 1)
        self.assertEqual(data['buildings'][0]['pk'], b1.pk)

    @skip("Fix for new data model")
    def test_search_extra_data_non_empty_column(self):
        """
        Not-empty column query on extra_data key.
        """
        # Empty column
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            extra_data={'testing': ''}
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        # Populated column
        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            extra_data={'testing': 'test'}
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'testing': '!""'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 1)
        self.assertEqual(len(data['buildings']), 1)
        self.assertEqual(data['buildings'][0]['pk'], b2.pk)

    @skip("Fix for new data model")
    def test_search_exclude_filter(self):
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            address_line_1="Include"
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            address_line_1="Exclude"
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        # Additional words
        cb3 = CanonicalBuilding(active=True)
        cb3.save()
        b3 = SEEDFactory.building_snapshot(
            canonical_building=cb3,
            address_line_1="Include 2"
        )
        cb3.canonical_snapshot = b3
        cb3.save()
        b3.super_organization = self.org
        b3.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'address_line_1': '!Exclude'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 2)
        self.assertEqual(len(data['buildings']), 2)

        addresses = []

        addresses.append(data['buildings'][0]['address_line_1'])
        addresses.append(data['buildings'][1]['address_line_1'])

        self.assertIn('Include', addresses)
        self.assertIn('Include 2', addresses)
        self.assertNotIn('Exclude', addresses)

    @skip("Fix for new data model")
    def test_search_extra_data_exclude_filter(self):
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            extra_data={'testing': 'Include'}
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            extra_data={'testing': 'Exclude'}
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        cb3 = CanonicalBuilding(active=True)
        cb3.save()
        b3 = SEEDFactory.building_snapshot(
            canonical_building=cb3,
            extra_data={'testing': 'Include 2'}
        )
        cb3.canonical_snapshot = b3
        cb3.save()
        b3.super_organization = self.org
        b3.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'testing': '!Exclude'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 2)
        self.assertEqual(len(data['buildings']), 2)

        fields = []

        fields.append(data['buildings'][0]['extra_data']['testing'])
        fields.append(data['buildings'][1]['extra_data']['testing'])

        self.assertIn('Include', fields)
        self.assertIn('Include 2', fields)
        self.assertNotIn('Exclude', fields)

    @skip("Fix for new data model")
    def test_search_exact_exclude_filter(self):
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            address_line_1="Include"
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            address_line_1="Exclude"
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        # Additional words
        cb3 = CanonicalBuilding(active=True)
        cb3.save()
        b3 = SEEDFactory.building_snapshot(
            canonical_building=cb3,
            address_line_1="exclude"
        )
        cb3.canonical_snapshot = b3
        cb3.save()
        b3.super_organization = self.org
        b3.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'address_line_1': '!"Exclude"'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 2)
        self.assertEqual(len(data['buildings']), 2)

        addresses = []

        addresses.append(data['buildings'][0]['address_line_1'])
        addresses.append(data['buildings'][1]['address_line_1'])

        self.assertIn('Include', addresses)
        self.assertIn('exclude', addresses)
        self.assertNotIn('Exclude', addresses)

    @skip("Fix for new data model")
    def test_search_extra_data_exact_exclude_filter(self):
        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            extra_data={'testing': 'Include'}
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        cb2 = CanonicalBuilding(active=True)
        cb2.save()
        b2 = SEEDFactory.building_snapshot(
            canonical_building=cb2,
            extra_data={'testing': 'Exclude'}
        )
        cb2.canonical_snapshot = b2
        cb2.save()
        b2.super_organization = self.org
        b2.save()

        cb3 = CanonicalBuilding(active=True)
        cb3.save()
        b3 = SEEDFactory.building_snapshot(
            canonical_building=cb3,
            extra_data={'testing': 'exclude'}
        )
        cb3.canonical_snapshot = b3
        cb3.save()
        b3.super_organization = self.org
        b3.save()

        url = reverse_lazy("seed:search_buildings")
        post_data = {
            'filter_params': {
                'testing': '!"Exclude"'
            },
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        # act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['number_matching_search'], 2)
        self.assertEqual(len(data['buildings']), 2)

        fields = []

        fields.append(data['buildings'][0]['extra_data']['testing'])
        fields.append(data['buildings'][1]['extra_data']['testing'])

        self.assertIn('Include', fields)
        self.assertIn('exclude', fields)
        self.assertNotIn('Exclude', fields)


class SearchBuildingSnapshotsViewTests(TestCase):

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

    @skip("Fix for new data model")
    def test_search_mapping_results(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        import_file = ImportFile.objects.create(
            import_record=import_record
        )

        cb1 = CanonicalBuilding(active=True)
        cb1.save()
        b1 = SEEDFactory.building_snapshot(
            canonical_building=cb1,
            address_line_1="test",
            import_file=import_file,
            source_type=ASSESSED_BS
        )
        cb1.canonical_snapshot = b1
        cb1.save()
        b1.super_organization = self.org
        b1.save()

        post_data = {
            'filter_params': {},
            'number_per_page': 10,
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None
        }

        # act
        response = self.client.post(
            reverse_lazy("apiv2:import_files-search-mapping-results", args=[import_file.pk]),
            content_type='application/json',
            data=json.dumps(post_data)
        )
        self.assertEqual(1, json.loads(response.content)['number_returned'])


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
        response = self.client.get(reverse("apiv2:datasets-list"),
                                   {'organization_id': self.org.pk})
        self.assertEqual(1, len(json.loads(response.content)['datasets']))

    def test_get_datasets_count(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(reverse("apiv2:datasets-count"),
                                   {'organization_id': self.org.pk})
        self.assertEqual(200, response.status_code)
        j = json.loads(response.content)
        self.assertEqual(j['status'], 'success')
        self.assertEqual(j['datasets_count'], 1)

    def test_get_datasets_count_invalid(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(reverse("apiv2:datasets-count"),
                                   {'organization_id': 666})
        self.assertEqual(400, response.status_code)
        j = json.loads(response.content)
        self.assertEqual(j['status'], 'error')
        self.assertEqual(j['message'],
                         'Could not find organization_id: 666')

    def test_get_dataset(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()
        response = self.client.get(
            reverse("apiv2:datasets-detail", args=[import_record.pk]) + '?organization_id=' + str(
                self.org.pk)
        )
        self.assertEqual('success', json.loads(response.content)['status'])

    def test_delete_dataset(self):
        import_record = ImportRecord.objects.create(owner=self.user)
        import_record.super_organization = self.org
        import_record.save()

        response = self.client.delete(
            reverse_lazy("apiv2:datasets-detail",
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
            reverse_lazy("apiv2:datasets-detail",
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
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.import_record = ImportRecord.objects.create(owner=self.user)
        self.import_record.super_organization = self.org
        self.import_record.save()
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            cached_first_row="Name|#*#|Address"
        )

        self.client.login(**user_details)

    def test_get_import_file(self):
        response = self.client.get(reverse("apiv2:import_files-detail", args=[self.import_file.pk]))
        self.assertEqual(self.import_file.pk,
                         json.loads(response.content)['import_file']['id'])

    def test_delete_file(self):
        post_data = {
            'file_id': self.import_file.pk,
            'organization_id': self.org.pk
        }

        response = self.client.delete(
            reverse_lazy("seed:delete_file"),
            content_type='application/json',
            data=json.dumps(post_data)
        )
        self.assertEqual('success', json.loads(response.content)['status'])
        self.assertFalse(
            ImportFile.objects.filter(pk=self.import_file.pk).exists())

    def test_get_matching_results(self):
        response = self.client.get(
            '/api/v2/import_files/' + str(self.import_file.pk) + '/matching_results/')
        self.assertEqual('success', json.loads(response.content)['status'])

    def test_delete_duplicates_from_import_file(self):
        response = self.client.get(
            reverse("seed:delete_duplicates_from_import_file"),
            {'import_file_id': self.import_file.pk}
        )
        self.assertEqual('success', json.loads(response.content)['status'])


@skip("Fix for new data model")
class ReportViewsTests(TestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.import_record = ImportRecord.objects.create(owner=self.user)
        self.import_record.super_organization = self.org
        self.import_record.save()
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            cached_first_row="Name|#*#|Address"
        )

        BuildingSnapshot.objects.create(super_organization=self.org,
                                        import_file=self.import_file)

        self.client.login(**user_details)

    def test_get_building_summary_report_data(self):
        params = {
            'start_date': (datetime.now() - timedelta(days=30)).strftime(
                '%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'organization_id': self.org.pk
        }

        response = self.client.get(
            reverse("seed:get_building_summary_report_data"), params)
        self.assertEqual('success', json.loads(response.content)['status'])

    # TODO replace with test for inventory report
    @skip("Fix for new data model")
    def test_get_building_report_data(self):
        params = {
            'start_date': (datetime.now() - timedelta(days=30)).strftime(
                '%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'x_var': 'use_description',
            'y_var': 'year_built',
            'organization_id': self.org.pk
        }

        response = self.client.get(reverse("seed:get_building_report_data"),
                                   params)
        self.assertEqual('success', json.loads(response.content)['status'])

    @skip("Fix for new data model")
    def test_get_inventory_report_data(self):
        pass  # TODO

    # TODO replace with test for inventory report
    @skip("Fix for new data model")
    def test_get_aggregated_building_report_data(self):
        params = {
            'start_date': (datetime.now() - timedelta(days=30)).strftime(
                '%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'x_var': 'energy_score',
            'y_var': 'year_built',
            'organization_id': self.org.pk
        }

        response = self.client.get(
            reverse("seed:get_aggregated_building_report_data"), params)
        self.assertEqual('success', json.loads(response.content)['status'])

    @skip("Fix for new data model")
    def test_get_aggregated_inventory_report_data(self):
        pass  # TODO


@skip("Fix for new data model")
class BuildingDetailViewTests(TestCase):
    """
    Tests of the SEED Building Detail page
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_user(**user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)
        self.client.login(**user_details)

        import_record = ImportRecord.objects.create()
        import_file_1 = ImportFile.objects.create(
            import_record=import_record,
        )
        import_file_1.save()
        import_file_2 = ImportFile.objects.create(
            import_record=import_record,
        )
        import_file_2.save()
        cb = CanonicalBuilding(active=True)
        cb.save()
        parent_1 = SEEDFactory.building_snapshot(
            canonical_building=cb,
            gross_floor_area=None
        )
        cb.canonical_snapshot = parent_1
        cb.save()
        parent_1.super_organization = self.org
        parent_1.import_file = import_file_1
        parent_1.source_type = 2
        parent_1.save()

        cb = CanonicalBuilding(active=True)
        cb.save()
        parent_2 = SEEDFactory.building_snapshot(canonical_building=cb)
        cb.canonical_snapshot = parent_2
        cb.save()
        parent_2.super_organization = self.org
        parent_2.import_file = import_file_2
        parent_2.source_type = 3
        parent_2.save()

        self.import_record = import_record
        self.import_file_1 = import_file_1
        self.import_file_2 = import_file_2
        self.parent_1 = parent_1
        self.parent_2 = parent_2

    # # TODO Replace with test_get_property, test_get_taxlot
    # @skip("Fix for new data model")
    # def test_get_building(self):
    #     """ tests the get_building view which returns building detail and source
    #         information from parent buildings.
    #     """
    #     # arrange
    #     child, changelist = save_snapshot_match(self.parent_1.pk,
    #                                             self.parent_2.pk)
    #
    #     url = reverse_lazy("seed:get_building")
    #     get_data = {
    #         'building_id': child.canonical_building.pk,
    #         'organization_id': self.org.pk,
    #     }
    #
    #     # act
    #     response = self.client.get(
    #         url,
    #         get_data,
    #         content_type='application/json',
    #     )
    #     json_string = response.content
    #     data = json.loads(json_string)
    #
    #     # assert
    #     self.assertEqual(data['status'], 'success')
    #     self.assertEqual(len(data['imported_buildings']), 2)
    #     # both parents have the same child
    #     self.assertEqual(
    #         data['imported_buildings'][0]['children'][0],
    #         child.pk
    #     )
    #     self.assertEqual(
    #         data['imported_buildings'][1]['children'][0],
    #         child.pk
    #     )
    #     # both parents link to their import file
    #     self.assertEqual(
    #         data['imported_buildings'][0]['import_file'],
    #         self.import_file_1.pk
    #     )
    #     self.assertEqual(
    #         data['imported_buildings'][1]['import_file'],
    #         self.import_file_2.pk
    #     )
    #     # child should get the first address
    #     self.assertEqual(
    #         data['building']['address_line_1'],
    #         self.parent_1.address_line_1
    #     )
    #     self.assertEqual(
    #         data['building']['address_line_1_source'],
    #         self.parent_1.pk
    #     )
    #     # child should get second gross floor area since first is set to None
    #     self.assertEqual(
    #         data['building']['gross_floor_area_source'],
    #         self.parent_2.pk
    #     )

    # TODO
    @skip("Fix for new data model")
    def test_get_property(self):
        pass

    # TODO
    @skip("Fix for new data model")
    def test_get_taxlot(self):
        pass

    # # TODO replace with test for inventory report
    # @skip("Fix for new data model")
    # def test_get_building_with_project(self):
    #     """ tests get_building projects payload"""
    #     # arrange
    #     child, changelist = save_snapshot_match(self.parent_1.pk,
    #                                             self.parent_2.pk)
    #     # create project wtihout compliance
    #     project = Project.objects.create(
    #         name='test project',
    #         owner=self.user,
    #         super_organization=self.org,
    #     )
    #     ProjectBuilding.objects.create(
    #         building_snapshot=child,
    #         project=project
    #     )
    #
    #     url = reverse_lazy("seed:get_building")
    #     get_data = {
    #         'building_id': child.canonical_building.pk,
    #         'organization_id': self.org.pk,
    #     }
    #
    #     # act
    #     response = self.client.get(
    #         url,
    #         get_data,
    #         content_type='application/json',
    #     )
    #     json_string = response.content
    #     data = json.loads(json_string)
    #
    #     # assert that the project is returned with the building
    #     self.assertEqual(data['status'], 'success')
    #     self.assertEqual(len(data['projects']), 1)
    #     self.assertEqual(
    #         data['projects'][0]['name'],
    #         'test project'
    #     )

    # TODO replace with test for inventory report
    # @skip("Fix for new data model")
    # def test_get_building_with_deleted_dataset(self):
    #     """ tests the get_building view where the dataset has been deleted and
    #         the building should load without showing the sources from deleted
    #         import files.
    #     """
    #     # arrange
    #     child, changelist = save_snapshot_match(self.parent_1.pk,
    #                                             self.parent_2.pk)
    #
    #     url = reverse_lazy("seed:get_building")
    #     get_data = {
    #         'building_id': child.canonical_building.pk,
    #         'organization_id': self.org.pk,
    #     }
    #
    #     # act
    #     self.import_record.delete()
    #     response = self.client.get(
    #         url,
    #         get_data,
    #         content_type='application/json',
    #     )
    #     json_string = response.content
    #     data = json.loads(json_string)
    #
    #     # assert
    #     self.assertEqual(data['status'], 'success')
    #     # empty list of parents
    #     self.assertEqual(len(data['imported_buildings']), 0)
    #     # building should still have all its info
    #     self.assertEqual(
    #         data['building']['address_line_1'],
    #         self.parent_1.address_line_1
    #     )
    #     self.assertEqual(
    #         data['building']['address_line_1_source'],
    #         self.parent_1.pk
    #     )
    #     self.assertEqual(
    #         data['building']['gross_floor_area_source'],
    #         self.parent_2.pk
    #     )
    #     self.assertAlmostEqual(
    #         data['building']['gross_floor_area'],
    #         self.parent_2.gross_floor_area,
    #         places=1,
    #     )
    #
    # # TODO replace with test for inventory report
    # @skip("Fix for new data model")
    # def test_get_building_imported_buildings_includes_green_button(self):
    #     # arrange
    #     self.parent_2.source_type = 6
    #     self.parent_2.save()
    #     child, changelist = save_snapshot_match(self.parent_1.pk,
    #                                             self.parent_2.pk)
    #
    #     url = reverse_lazy("seed:get_building")
    #     get_data = {
    #         'building_id': child.canonical_building.pk,
    #         'organization_id': self.org.pk,
    #     }
    #
    #     # act
    #     response = self.client.get(
    #         url,
    #         get_data,
    #         content_type='application/json',
    #     )
    #     json_string = response.content
    #     data = json.loads(json_string)
    #
    #     self.assertEqual(2, len(data['imported_buildings']))
    #
    #     # both parents link to their import file
    #     self.assertEqual(
    #         data['imported_buildings'][0]['import_file'],
    #         self.import_file_1.pk
    #     )
    #     self.assertEqual(
    #         data['imported_buildings'][1]['import_file'],
    #         self.import_file_2.pk
    #     )

    # TODO replace with test for inventory
    @skip("Fix for new data model")
    def test_update_building_audit_log(self):
        """tests that a building update logs an audit_log"""
        # arrange
        building = self.parent_1.to_dict()
        building['gross_floor_area'] = 112233445566

        # act
        self.client.put(
            reverse_lazy("seed:update_building"),
            data=json.dumps({
                'organization_id': self.org.pk,
                'building': building,
            }),
            content_type='application/json'
        )

        # assert
        self.assertEqual(AuditLog.objects.count(), 1)
        audit_log = AuditLog.objects.first()
        self.assertEqual(
            audit_log.content_object,
            self.parent_1.canonical_building
        )
        self.assertTrue('update_building' in audit_log.action)
        self.assertEqual(audit_log.audit_type, LOG)

    @skip("Fix for new data model")
    def test_save_match_audit_log(self):
        """tests that a building match logs an audit_log"""
        # act
        self.client.put(
            reverse_lazy("seed:save_match"),
            data=json.dumps({
                'organization_id': self.org.pk,
                'source_building_id': self.parent_1.pk,
                'target_building_id': self.parent_2.pk,
                'create_match': True
            }),
            content_type='application/json'
        )

        # assert
        self.assertEqual(AuditLog.objects.count(), 1)
        audit_log = AuditLog.objects.first()
        self.assertEqual(
            audit_log.content_object,
            self.parent_1.canonical_building
        )
        self.assertTrue('save_match' in audit_log.action)
        self.assertEqual(audit_log.action_note, 'Matched building.')
        self.assertEqual(audit_log.audit_type, LOG)

    @skip("Fix for new data model")
    def test_get_match_tree(self):
        """tests get_match_tree"""
        # arrange
        self.client.put(
            reverse_lazy("seed:save_match"),
            data=json.dumps({
                'organization_id': self.org.pk,
                'source_building_id': self.parent_1.pk,
                'target_building_id': self.parent_2.pk,
                'create_match': True
            }),
            content_type='application/json'
        )

        # act
        resp = self.client.get(
            reverse_lazy("seed:get_match_tree"),
            {
                'organization_id': self.org.pk,
                'building_id': self.parent_1.pk,
            },
            content_type='application/json'
        )

        # assert
        body = json.loads(resp.content)
        ids = [b['id'] for b in body['match_tree']]
        self.assertIn(self.parent_1.pk, ids)
        self.assertIn(self.parent_2.pk, ids)
        self.assertIn(self.parent_1.children.first().pk, ids)

    @skip("Fix for new data model")
    def test_get_match_tree_from_child(self):
        """tests get_match_tree from the child"""
        # arrange
        self.client.put(
            reverse_lazy("seed:save_match"),
            data=json.dumps({
                'organization_id': self.org.pk,
                'source_building_id': self.parent_1.pk,
                'target_building_id': self.parent_2.pk,
                'create_match': True
            }),
            content_type='application/json'
        )

        # act
        resp = self.client.get(
            reverse_lazy("seed:get_match_tree"),
            {
                'organization_id': self.org.pk,
                'building_id': self.parent_1.children.first().pk,
            },
            content_type='application/json'
        )

        # assert
        body = json.loads(resp.content)
        ids = [b['id'] for b in body['match_tree']]
        self.assertIn(self.parent_1.pk, ids)
        self.assertIn(self.parent_2.pk, ids)
        self.assertIn(self.parent_1.children.first().pk, ids)

    def test_save_match_wrong_perms_org_id(self):
        """tests that a building match is valid for the org id"""
        # arrange
        new_org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=new_org)

        # act
        resp = self.client.put(
            reverse_lazy("seed:save_match"),
            data=json.dumps({
                'organization_id': new_org.pk,
                'source_building_id': self.parent_1.pk,
                'target_building_id': self.parent_2.pk,
                'create_match': True
            }),
            content_type='application/json'
        )

        # assert
        body = json.loads(resp.content)
        self.assertEqual(body, {
            'status': 'error',
            'message': 'The source building does not belong to the organization'
        })

    def test_save_match_invalid_org(self):
        """tests that a building match checks perm of org id"""
        # arrange
        new_org = Organization.objects.create()

        # act
        resp = self.client.put(
            reverse_lazy("seed:save_match"),
            data=json.dumps({
                'organization_id': new_org.pk,
                'source_building_id': self.parent_1.pk,
                'target_building_id': self.parent_2.pk,
                'create_match': True
            }),
            content_type='application/json'
        )

        # assert
        body = json.loads(resp.content)
        self.assertEqual(body, {
            'status': 'error',
            'message': 'No relationship to organization',
        })

    def test_save_match_wrong_perms_different_building_orgs(self):
        """tests that a building match is valid for BS orgs"""
        # arrange
        new_org = Organization.objects.create()
        self.parent_1.super_organization = new_org
        self.parent_1.save()
        OrganizationUser.objects.create(user=self.user, organization=new_org)

        # act
        resp = self.client.put(
            reverse_lazy("seed:save_match"),
            data=json.dumps({
                'organization_id': self.org.pk,
                'source_building_id': self.parent_1.pk,
                'target_building_id': self.parent_2.pk,
                'create_match': True
            }),
            content_type='application/json'
        )

        # assert
        body = json.loads(resp.content)
        self.assertEqual(body, {
            'status': 'error',
            'message': 'Only buildings within an organization can be matched'
        })

    @skip("Fix for new data model")
    def test_save_unmatch_audit_log(self):
        """tests that a building unmatch logs an audit_log"""
        # arrange match to unmatch
        self.client.post(
            reverse_lazy("seed:save_match"),
            data=json.dumps({
                'organization_id': self.org.pk,
                'source_building_id': self.parent_1.pk,
                'target_building_id': self.parent_2.pk,
                'create_match': True
            }),
            content_type='application/json'
        )
        # act
        self.client.post(
            reverse_lazy("seed:save_match"),
            data=json.dumps({
                'organization_id': self.org.pk,
                'source_building_id': self.parent_2.pk,
                'create_match': False
            }),
            content_type='application/json'
        )

        # assert
        self.assertEqual(AuditLog.objects.count(), 2)
        audit_log = AuditLog.objects.first()
        self.assertEqual(
            audit_log.content_object,
            self.parent_2.canonical_building
        )
        self.assertTrue('save_match' in audit_log.action)
        self.assertEqual(audit_log.action_note, 'Unmatched building.')
        self.assertEqual(audit_log.audit_type, LOG)


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
        # depending on the columns in the db and the mapper implementaion
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
            reverse_lazy("apiv2:data_files-mapping-suggestions",
                         args=[self.import_file.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json'
        )
        self.assertEqual('success', json.loads(response.content)['status'])

    def test_get_column_mapping_suggestions_pm_file(self):
        response = self.client.get(
            reverse_lazy("apiv2:data_files-mapping-suggestions",
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
            reverse_lazy("apiv2:data_files-mapping-suggestions",
                         args=[self.import_file.pk]) + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        self.assertEqual('success', json.loads(response.content)['status'])

    def test_get_raw_column_names(self):
        """Good case for ``get_raw_column_names``."""
        resp = self.client.get(
            reverse_lazy("apiv2:import_files-raw-column-names", args=[self.import_file.id]),
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
            column_name='Global National Median Site Energy Use',
            unit=float_unit)

        resp = self.client.post(
            reverse_lazy("apiv2:import_files-save-column-mappings", args=[self.import_file.id]),
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
            column_name="Global National Median Site Energy Use"
        )

        self.assertEquals(len(energy_use_columns), 1)

        eu_col = energy_use_columns.first()

        assert (eu_col.unit is not None)
        self.assertEqual(eu_col.unit.unit_name, "test energy use intensity")
        self.assertEqual(eu_col.unit.unit_type, FLOAT)

    def test_save_column_mappings_idempotent(self):
        """We need to make successive calls to save_column_mappings."""
        # Save the first mapping, just like before
        self.assertEqual(
            ColumnMapping.objects.filter(super_organization=self.org).count(),
            0
        )
        resp = self.client.post(
            reverse_lazy("apiv2:import_files-save-column-mappings", args=[self.import_file.id]),
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

        # the second user in the org makes the same save, which shouldn't be
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
            reverse_lazy("apiv2:import_files-save-column-mappings", args=[self.import_file.id]),
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
        resp = self.client.post(
            reverse_lazy("apiv2:progress"),
            data=json.dumps({
                'progress_key': progress_key,
            }),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertEqual(body.get('progress', 0), test_progress['progress'])
        self.assertEqual(body.get('progress_key', ''), progress_key)

    @skip("Fix for new data model")
    def test_remap_buildings(self):
        """Test good case for resetting mapping."""
        # Make raw BSes, these should stick around.
        for x in range(10):
            test_util.make_fake_property(self.import_file, {}, ASSESSED_RAW)

        # Make "mapped" BSes, these should get removed.
        for x in range(10):
            test_util.make_fake_property(self.import_file, {}, ASSESSED_BS)

        # Set import file like we're done mapping
        self.import_file.mapping_done = True
        self.import_file.mapping_progress = 100
        self.import_file.save()

        # Set cache like we're done mapping.
        cache_key = decorators.get_prog_key('map_data', self.import_file.pk)
        set_cache(cache_key, 'success', 100)

        resp = self.client.post(
            reverse_lazy("seed:remap_buildings"),
            data=json.dumps({
                'file_id': self.import_file.pk,
            }),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            BuildingSnapshot.objects.filter(
                import_file=self.import_file,
                source_type__in=(ASSESSED_BS, PORTFOLIO_BS)
            ).count(),
            0
        )

        self.assertEqual(
            BuildingSnapshot.objects.filter(
                import_file=self.import_file,
            ).count(),
            10
        )

        self.assertEqual(get_cache(cache_key)['progress'], 0)

    @skip("Fix for new data model")
    def test_reset_mapped_w_previous_matches(self):
        """Ensure we ignore mapped buildings with children BuildingSnapshots."""
        # Make the raw BSes for us to make new mappings from
        for x in range(10):
            test_util.make_fake_property(self.import_file, {}, ASSESSED_RAW)
        # Simulate existing mapped BSes, which should be deleted.
        for x in range(10):
            test_util.make_fake_property(self.import_file, {}, ASSESSED_BS)

        # Setup our exceptional case: here the first BS has a child, COMPOSITE.
        child = test_util.make_fake_property(None, {}, COMPOSITE_BS)
        first = BuildingSnapshot.objects.filter(
            import_file=self.import_file
        )[:1].get()

        # We add a child to our first BuildingSnapshot, which should exclude it
        # from deletion and thus it should remain after a remapping is issued.
        first.children.add(child)

        # Here we mark all of the mapped building snapshots. These should all
        # get deleted when we remap from the raw snapshots after the call to
        # to this function.
        for item in BuildingSnapshot.objects.filter(source_type=ASSESSED_BS):
            item.property_name = 'Touched'
            item.save()

        # Ensure we have all 10 mapped BuildingSnapshots saved.
        self.assertEqual(
            BuildingSnapshot.objects.filter(property_name='Touched').count(),
            10
        )

        self.client.post(
            reverse_lazy("seed:remap_buildings"),
            data=json.dumps({
                'file_id': self.import_file.pk,
            }),
            content_type='application/json'
        )

        # Assert that only one remains that was touched, and that it has the
        # child.
        self.assertEqual(
            BuildingSnapshot.objects.filter(property_name='Touched').count(),
            1
        )
        self.assertEqual(
            BuildingSnapshot.objects.get(
                property_name='Touched'
            ).children.all()[0],
            child
        )

    @skip("Fix for new data model")
    def test_reset_mapped_w_matching_done(self):
        """Make sure we don't delete buildings that have been merged."""
        self.import_file.matching_done = True
        self.import_file.matching_progress = 100
        self.import_file.save()

        for x in range(10):
            test_util.make_fake_property(self.import_file, {}, ASSESSED_BS)

        resp = self.client.post(
            reverse_lazy("seed:remap_buildings"),
            data=json.dumps({
                'file_id': self.import_file.pk,
            }),
            content_type='application/json'
        )
        json_result = json.loads(resp.content)

        self.assertEqual(json_result['status'], 'warning')
        self.assertEqual(json_result['message'],
                         'Mapped buildings already merged')
        self.assertEqual(json_result['progress'], 100)
        # self.assertItemsEqualqual(json_result['progress_key'], 100)

        # Verify that we haven't deleted those mapped buildings.
        self.assertEqual(
            BuildingSnapshot.objects.filter(
                import_file=self.import_file
            ).count(),
            10
        )

    def test_create_dataset(self):
        """tests the create_dataset view, allows duplicate dataset names"""
        DATASET_NAME_1 = 'test_name 1'
        DATASET_NAME_2 = 'city compliance dataset 2014'
        resp = self.client.post(
            reverse_lazy("apiv2:datasets-list") + '?organization_id=' + str(self.org.pk),
            data=json.dumps({
                'name': DATASET_NAME_1,
            }),
            content_type='application/json',
        )
        data = json.loads(resp.content)
        self.assertEqual(data['name'], DATASET_NAME_1)

        resp = self.client.post(
            reverse_lazy("apiv2:datasets-list") + '?organization_id=' + str(self.org.pk),
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
            reverse_lazy("apiv2:datasets-list") + '?organization_id=' + str(self.org.pk),
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


@skip("Fix for new data model")
class MatchTreeTests(TestCase):
    """Currently only tests _parent_tree_coparents"""

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.client.login(**user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        # setup the snapshot tree from the doc string of
        # _parent_tree_coparents
        #  C0       C1
        #  |       |
        # B0  B1   |
        #  \  /   B3
        #   B2   /
        #    \  /
        #     B4  B5
        #      \  /
        #       B6
        #       |
        #       B7  B8
        #        \  /
        #         B9

        snapshots = {}
        for i in range(10):
            temp = BuildingSnapshot.objects.create(
                super_organization=self.org,
            )
            key = 'bs{0}'.format(i)
            snapshots[key] = temp

        cb0 = CanonicalBuilding.objects.create(
            canonical_snapshot=snapshots['bs9']
        )

        cb1 = CanonicalBuilding.objects.create(
            canonical_snapshot=snapshots['bs3']
        )

        # set canonical buildings
        for key in ['bs0', 'bs2', 'bs4', 'bs6', 'bs7', 'bs9']:
            temp = snapshots[key]
            temp.canonical_building = cb0
            temp.save()

        # set bs3 canonical building
        bs3 = snapshots['bs3']
        bs3.canonical_building = cb1
        bs3.save()

        # small helper for setting up parent child relationships
        def link_child(parent_key, child_key):
            parent = snapshots[parent_key]
            child = snapshots[child_key]
            parent.children.add(child)

        # setup parent child relationships
        link_child('bs0', 'bs2')
        link_child('bs1', 'bs2')

        link_child('bs2', 'bs4')
        link_child('bs3', 'bs4')

        link_child('bs4', 'bs6')
        link_child('bs5', 'bs6')

        link_child('bs6', 'bs7')

        link_child('bs7', 'bs9')
        link_child('bs8', 'bs9')

        # set attrs on self
        self.cb0 = CanonicalBuilding.objects.get(pk=cb0.pk)
        self.cb1 = CanonicalBuilding.objects.get(pk=cb1.pk)

        for k, bs in snapshots.iteritems():
            reloaded = BuildingSnapshot.objects.get(pk=bs.pk)
            setattr(self, k, reloaded)

    def test_parent_tree_coparents(self):
        """Tests that _parent_tree_coparents returns what we expect"""

        # test with bs9
        bs9_root, bs9_cps = _parent_tree_coparents(self.bs9)
        bs9_expected_parent_coparents = [
            self.bs0, self.bs1, self.bs3, self.bs5, self.bs8
        ]

        self.assertEqual(bs9_root, self.bs0)
        self.assertItemsEqual(bs9_cps, bs9_expected_parent_coparents)

        # test with bs4
        bs4_root, bs4_cps = _parent_tree_coparents(self.bs4)
        bs4_expected_parent_coparents = [
            self.bs0, self.bs1, self.bs3
        ]

        self.assertEqual(bs4_root, self.bs0)
        self.assertItemsEqual(bs4_cps, bs4_expected_parent_coparents)

        # test with bs5
        bs5_root, bs5_cps = _parent_tree_coparents(self.bs5)
        bs5_expected_parent_coparents = [
            self.bs0, self.bs1, self.bs3
        ]

        self.assertEqual(bs5_root, self.bs0)
        self.assertItemsEqual(bs5_cps, bs5_expected_parent_coparents)

        # test with bs4 when its canonical building is cb1
        self.bs4.canonical_building = self.cb1
        self.bs4.save()
        self.cb1.canonical_snapshot = self.bs4
        self.cb1.save()

        bs4_root, bs4_cps = _parent_tree_coparents(self.bs4)
        bs4_expected_parent_coparents = [
            self.bs2, self.bs3
        ]

        self.assertEqual(bs4_root, self.bs3)
        self.assertItemsEqual(bs4_cps, bs4_expected_parent_coparents)

    def test_get_coparents(self):
        response = self.client.get(reverse('seed:get_coparents'),
                                   {'organization_id': self.org.pk,
                                    'building_id': self.cb0.canonical_snapshot.pk})
        self.assertEqual('success', json.loads(response.content)['status'])


class InventoryViewTests(TestCase):

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
        self.property_state_factory = FakePropertyStateFactory()
        self.taxlot_state_factory = FakeTaxLotStateFactory()
        self.org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.org
        )
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10))
        self.status_label = StatusLabel.objects.create(
            name='test', super_organization=self.org
        )
        self.client.login(**user_details)

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()
        self.status_label.delete()
        Column.objects.all().delete()
        Cycle.objects.all().delete()
        Property.objects.all().delete()
        ProjectBuilding.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        TaxLot.objects.all().delete()
        TaxLotProperty.objects.all().delete()
        TaxLotState.objects.all().delete()
        TaxLotView.objects.all().delete()

    def test_get_properties(self):
        state = self.property_state_factory.get_property_state(self.org)
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
        state = self.property_state_factory.get_property_state(self.org)
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
        response = self.client.get("/api/v2/properties/", params)
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
        state = self.property_state_factory.get_property_state(
            self.org,
            extra_data=json.dumps(extra_data)
        )
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
        response = self.client.get("/api/v2/properties/", params)
        result = json.loads(response.content)
        results = result['results'][0]
        self.assertEquals(len(result['results']), 1)
        self.assertEquals(results['address_line_1'], state.address_line_1)
        self.assertTrue(results['is secret lair'])
        self.assertEquals(results['paint color'], 'pink')
        self.assertEquals(results['number of secret gadgets'], 5)

    def test_get_properties_with_taxlots(self):
        property_state = self.property_state_factory.get_property_state(self.org)
        property_property = self.property_factory.get_property(campus=True)
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
        response = self.client.post("/api/v2/properties/filter/?{}={}&{}={}&{}={}".format(
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
        property_state = self.property_state_factory.get_property_state(self.org)
        prprty = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
            address_line_1=property_state.address_line_1,
            postal_code=property_state.postal_code,
            extra_data=json.dumps(extra_data)
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post("/api/v2/properties/filter/?{}={}&{}={}&{}={}".format(
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
        state = self.property_state_factory.get_property_state(self.org)
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        response = self.client.post("/api/v2/properties/filter/?{}={}&{}={}&{}={}".format(
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
        filter_properties_url = "/api/v2/properties/filter/?{}={}&{}={}&{}={}".format(
            'organization_id', self.org.pk,
            'page', 10,
            'per_page', 999999999
        )
        print("Filter properties URL: " + filter_properties_url)
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
        property_state = self.property_state_factory.get_property_state(self.org)
        property_property = self.property_factory.get_property()
        property_property.labels.add(self.status_label)
        property_property.save()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get(
            "/api/v2/properties/" + str(property_property.id) + "/",
            params
        )
        results = json.loads(response.content)

        self.assertEqual(results['status'], 'success')
        self.assertEqual(results['history'], [])
        self.assertEqual(results['property']['labels'], [self.status_label.pk])
        self.assertEqual(results['source'], 'ImportFile')
        self.assertEqual(results['changed_fields'], None)

        expected_property = {
            'campus': False, 'id': property_property.pk,
            'organization': self.org.pk, 'parent_property': None,
            'labels': [self.status_label.pk]
        }
        self.assertEquals(results['property'], expected_property)

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
        self.assertEqual(
            rtaxlot['taxlot'],
            {'id': taxlot.pk, 'organization': self.org.pk, 'labels': []}
        )

        tcycle = rtaxlot['cycle']
        self.assertEquals(tcycle['name'], '2010 Annual')
        self.assertEquals(tcycle['user'], self.user.pk)
        self.assertEquals(tcycle['organization'], self.org.pk)

        tstate = rtaxlot['state']
        self.assertEqual(tstate['id'], taxlot_state.pk)
        self.assertEqual(tstate['address_line_1'], taxlot_state.address_line_1)

    def test_get_property_history(self):
        pass  # TODO

    def test_get_property_multiple_taxlots(self):
        property_state = self.property_state_factory.get_property_state(self.org)
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state_1 = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
            self.org,
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
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get(
            "/api/v2/properties/" + str(property_property.id) + "/",
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
        self.assertEqual(
            rtaxlot_1['taxlot'],
            {'id': taxlot_1.pk, 'organization': self.org.pk, 'labels': []}
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
        self.assertEqual(
            rtaxlot_2['taxlot'],
            {'id': taxlot_2.pk, 'organization': self.org.pk, 'labels': []}
        )

        tcycle_2 = rtaxlot_2['cycle']
        self.assertEquals(tcycle_2['name'], '2010 Annual')
        self.assertEquals(tcycle_2['user'], self.user.pk)
        self.assertEquals(tcycle_2['organization'], self.org.pk)

        tstate_2 = rtaxlot_2['state']
        self.assertEqual(tstate_2['id'], taxlot_state_2.pk)
        self.assertEqual(tstate_2['address_line_1'], taxlot_state_2.address_line_1)

        expected_property = {
            'campus': False, 'id': property_property.pk, 'labels': [],
            'organization': self.org.pk, 'parent_property': None,
        }
        self.assertEquals(results['property'], expected_property)

        state = results['state']
        self.assertEquals(state['address_line_1'],
                          property_state.address_line_1)
        self.assertEquals(state['id'], property_state.pk)

    def test_get_taxlots(self):
        property_state = self.property_state_factory.get_property_state(
            self.org,
            extra_data=json.dumps({'extra_data_field': 'edfval'})
        )
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
        response = self.client.post("/api/v2/taxlots/filter/?{}={}&{}={}&{}={}&{}={}".format(
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
        property_state = self.property_state_factory.get_property_state(self.org)
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
        url = "/api/v2/taxlots/filter/?{}={}&{}={}".format(
            'organization_id', self.org.pk,
            'page', 1
        )
        response = self.client.post(url, data={'columns': COLUMNS_TO_SEND})
        results = json.loads(response.content)['results']

        self.assertEquals(len(results), 1)

        property_state_1 = self.property_state_factory.get_property_state(self.org)
        prprty_1 = self.property_factory.get_property()
        property_view_1 = PropertyView.objects.create(
            property=prprty_1, cycle=self.cycle, state=property_state_1
        )
        TaxLotProperty.objects.create(
            property_view=property_view_1, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        url = "/api/v2/taxlots/filter/?{}={}&{}={}&{}={}".format(
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
        property_state = self.property_state_factory.get_property_state(
            self.org,
            extra_data=json.dumps({'extra_data_field': 'edfval'})
        )
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state_1 = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
            self.org,
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
        response = self.client.post("/api/v2/taxlots/filter/?{}={}&{}={}&{}={}&{}={}".format(
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
        property_state = self.property_state_factory.get_property_state(self.org)
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
            postal_code=property_state.postal_code,
            extra_data=json.dumps({'extra_data_field': 'edfval'})
        )
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )
        TaxLotProperty.objects.create(
            property_view=property_view, taxlot_view=taxlot_view,
            cycle=self.cycle
        )
        response = self.client.post("/api/v2/taxlots/filter/?{}={}&{}={}&{}={}".format(
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
        property_state = self.property_state_factory.get_property_state(
            self.org,
            extra_data=json.dumps({'extra_data_field': 'edfval'})
        )
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
        response = self.client.post("/api/v2/taxlots/filter/?{}={}&{}={}&{}={}".format(
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
        property_state = self.property_state_factory.get_property_state(
            self.org,
            extra_data=json.dumps({'extra_data_field': 'edfval'})
        )
        property_property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
        response = self.client.post("/api/v2/taxlots/filter/?{}={}&{}={}&{}={}".format(
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
        property_state = self.property_state_factory.get_property_state(
            self.org,
            extra_data=json.dumps({'extra_data_field': 'edfval'})
        )
        property_property = self.property_factory.get_property(self.org)
        property_view = PropertyView.objects.create(
            property=property_property, cycle=self.cycle, state=property_state
        )
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(
            self.org,
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
        response = self.client.post("/api/v2/taxlots/filter/?{}={}&{}={}&{}={}".format(
            'organization_id', self.org.pk,
            'cycle', self.cycle.pk,
            'page', 'bad'
        ), data={'columns': COLUMNS_TO_SEND})
        related = json.loads(response.content)['results'][0]['related'][0]
        self.assertEqual(related['calculated_taxlot_ids'], 'Missing')

    def test_get_taxlot(self):
        taxlot_state = self.taxlot_state_factory.get_taxlot_state(self.org)
        taxlot = TaxLot.objects.create(organization=self.org)
        taxlot.labels.add(self.status_label)
        taxlot_view = TaxLotView.objects.create(
            taxlot=taxlot, state=taxlot_state, cycle=self.cycle
        )

        property_state_1 = self.property_state_factory.get_property_state(self.org)
        property_property_1 = self.property_factory.get_property()
        property_view_1 = PropertyView.objects.create(
            property=property_property_1, cycle=self.cycle,
            state=property_state_1
        )
        TaxLotProperty.objects.create(
            property_view=property_view_1, taxlot_view=taxlot_view,
            cycle=self.cycle
        )

        property_state_2 = self.property_state_factory.get_property_state(self.org)
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
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get("/api/v2/taxlots/" + str(taxlot.id) + "/", params)
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
        self.assertEqual(
            result['taxlot'], {
                'id': taxlot.pk,
                'labels': [self.status_label.pk],
                'organization': self.org.pk
            }
        )

    def test_get_cycles(self):
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get(
            reverse("apiv2:cycles-list"), params
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
            extra_data_source='property'
        )
        self.column_factory.get_column(
            'taxlot_extra_data_column',
            is_extra_data=True,
            extra_data_source='taxlot'
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get(
            "/api/v2/properties/columns/", params
        )
        results = json.loads(response.content)['columns']

        pm_property_id_col = {
            'name': 'pm_property_id',
            'displayName': 'PM Property ID',
            'pinnedLeft': True,
            'type': 'number',
            'related': False,
        }
        self.assertEqual(results[0], pm_property_id_col)

        expected_property_extra_data_column = {
            'extraData': True,
            'name': 'property_extra_data_column',
            'displayName': 'property_extra_data_column',
            'related': False,
        }
        self.assertIn(expected_property_extra_data_column, results)

        expected_taxlot_extra_data_column = {
            'extraData': True,
            'name': 'taxlot_extra_data_column',
            'displayName': 'taxlot_extra_data_column',
            'related': True,
        }
        self.assertIn(expected_taxlot_extra_data_column, results)

    def test_get_taxlot_columns(self):
        self.column_factory.get_column(
            'property_extra_data_column',
            is_extra_data=True,
            extra_data_source='property'
        )
        self.column_factory.get_column(
            'taxlot_extra_data_column',
            is_extra_data=True,
            extra_data_source='taxlot'
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
        }
        response = self.client.get("/api/v2/taxlots/columns/", params)
        results = json.loads(response.content)['columns']

        jurisdiction_tax_lot_id_col = {
            'name': 'jurisdiction_tax_lot_id',
            'displayName': 'Jurisdiction Tax Lot ID',
            'pinnedLeft': True,
            'type': 'numberStr',
            'related': False,
        }
        self.assertEqual(results[0], jurisdiction_tax_lot_id_col)

        expected_property_extra_data_column = {
            'extraData': True,
            'name': 'property_extra_data_column',
            'displayName': 'property_extra_data_column',
            'related': True,
        }
        self.assertIn(expected_property_extra_data_column, results)

        expected_taxlot_extra_data_column = {
            'extraData': True,
            'name': 'taxlot_extra_data_column',
            'displayName': 'taxlot_extra_data_column',
            'related': False,
        }
        self.assertIn(expected_taxlot_extra_data_column, results)
