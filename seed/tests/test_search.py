from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q
from django.http.request import QueryDict
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import Column
from seed.search import FilterException, build_view_filters_and_sorts
from seed.utils.organizations import create_organization


class TestInventoryViewSearchParsers(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.fake_user = User.objects.create(username='test')
        cls.fake_org, _, _ = create_organization(cls.fake_user)

    def test_parse_filters_works_for_canonical_columns(self):
        @dataclass
        class TestCase:
            name: str
            input: QueryDict
            expected: Q

        # -- Setup
        test_cases = [
            TestCase('canonical column with number data_type', QueryDict('latitude=12.3'), Q(state__latitude=12.3)),
            TestCase('canonical column with integer data_type', QueryDict('year_built=123'), Q(state__year_built=123)),
            TestCase('canonical column with string data_type', QueryDict('custom_id_1=123'), Q(state__custom_id_1='123')),
            TestCase('canonical column with geometry data_type', QueryDict('property_footprint=abcdefg'), Q(state__property_footprint='abcdefg')),
            TestCase('canonical column with datetime data_type', QueryDict('updated=2022-01-01 10:11:12'), Q(state__updated=datetime(2022, 1, 1, 10, 11, 12))),
            TestCase('canonical column with date data_type', QueryDict('year_ending=2022-01-01'), Q(state__year_ending=datetime(2022, 1, 1))),
            TestCase('canonical column with boolean data_type', QueryDict('campus=True'), Q(property__campus=True)),
            TestCase('canonical column with area data_type', QueryDict('gross_floor_area=12.3'), Q(state__gross_floor_area=12.3)),
            TestCase('canonical column with eui data_type', QueryDict('site_eui=12.3'), Q(state__site_eui=12.3)),
        ]

        for test_case in test_cases:
            # -- Act
            columns = Column.retrieve_all(self.fake_org, 'property', only_used=False)
            filters, _ = build_view_filters_and_sorts(test_case.input, columns)

            # -- Assert
            self.assertEqual(
                filters,
                test_case.expected,
                f'Failed "{test_case.name}"; actual: {filters}; expected: {test_case.expected}'
            )

    def test_parse_filters_works_for_extra_data_columns(self):
        @dataclass
        class TestCase:
            name: str
            input: QueryDict
            expected: Q

        # -- Setup
        # create some extra data columns
        extra_data_columns = [
            {
                'column_name': 'test_string',
                'data_type': 'string',
                'is_extra_data': True,
                'table_name': 'PropertyState',
                'organization': self.fake_org,
            },
            {
                'column_name': 'test_number',
                'data_type': 'number',
                'is_extra_data': True,
                'table_name': 'PropertyState',
                'organization': self.fake_org,
            }
        ]
        for col in extra_data_columns:
            Column.objects.create(**col)

        test_cases = [
            TestCase('extra_data column with string data_type', QueryDict('test_string=hello'), Q(state__extra_data__test_string='hello')),
            TestCase('extra_data column with number data_type', QueryDict('test_number=12.3'), Q(state__extra_data__test_number=12.3)),
        ]

        for test_case in test_cases:
            # -- Act
            columns = Column.retrieve_all(self.fake_org, 'property', only_used=False)
            filters, _ = build_view_filters_and_sorts(test_case.input, columns)

            # -- Assert
            self.assertEqual(
                filters,
                test_case.expected,
                f'Failed "{test_case.name}"; actual: {filters}; expected: {test_case.expected}'
            )

    def test_parse_filters_returns_empty_q_object_for_invalid_columns(self):
        # -- Setup
        query_dict = QueryDict('this_column_does_not_exits=123')

        # -- Act
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False)
        filters, _ = build_view_filters_and_sorts(query_dict, columns)

        # -- Assert
        self.assertEqual(filters, Q())

    def test_parse_filters_can_handle_multiple_filters(self):
        # -- Setup
        query_dict = QueryDict('city=Denver&site_eui=100&gross_floor_area=200')

        # -- Act
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False)
        filters, _ = build_view_filters_and_sorts(query_dict, columns)

        # -- Assert
        expected = (
            Q(state__city='Denver')
            & Q(state__site_eui=100)
            & Q(state__gross_floor_area=200)
        )
        self.assertEqual(filters, expected)

    def test_parse_filters_preserves_field_lookups(self):
        @dataclass
        class TestCase:
            name: str
            input: QueryDict
            expected: Q

        # -- Setup
        test_cases = [
            TestCase('field lookup <', QueryDict('site_eui__lt=12.3'), Q(state__site_eui__lt=12.3)),
            TestCase('field lookup <=', QueryDict('site_eui__lte=12.3'), Q(state__site_eui__lte=12.3)),
            TestCase('field lookup >', QueryDict('site_eui__gt=12.3'), Q(state__site_eui__gt=12.3)),
            TestCase('field lookup >=', QueryDict('site_eui__gte=12.3'), Q(state__site_eui__gte=12.3)),
            TestCase('field lookup exact', QueryDict('site_eui__exact=12.3'), Q(state__site_eui__exact=12.3)),
            TestCase('field lookup icontains', QueryDict('site_eui__icontains=12.3'), Q(state__site_eui__icontains=12.3)),
        ]

        for test_case in test_cases:
            # -- Act
            columns = Column.retrieve_all(self.fake_org, 'property', only_used=False)
            filters, _ = build_view_filters_and_sorts(test_case.input, columns)

            # -- Assert
            self.assertEqual(
                filters,
                test_case.expected,
                f'Failed "{test_case.name}"; actual: {filters}; expected: {test_case.expected}'
            )

    def test_parse_filters_returns_negated_q_object_for_ne_lookup(self):
        # -- Setup
        query_dict = QueryDict('city__ne=Denver')

        # -- Act
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False)
        filters, _ = build_view_filters_and_sorts(query_dict, columns)

        # -- Assert
        self.assertEqual(filters, ~Q(state__city='Denver'))

    def test_parse_filters_raises_exception_when_filter_value_is_invalid(self):
        # -- Setup
        # site_eui is a number type, so the string 'hello' will fail to be parsed
        query_dict = QueryDict('site_eui=hello')

        # -- Act, Assert
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False)
        with self.assertRaises(FilterException):
            build_view_filters_and_sorts(query_dict, columns)

    def test_parse_sorts_works(self):
        @dataclass
        class TestCase:
            name: str
            input: QueryDict
            expected: list[str]

        # -- Setup
        # create an extra data column
        Column.objects.create(
            column_name='test_column',
            data_type='string',
            is_extra_data=True,
            table_name='PropertyState',
            organization=self.fake_org,
        )

        test_cases = [
            TestCase('order_by canonical column', QueryDict('order_by=site_eui'), ['state__site_eui']),
            TestCase('order_by extra data column', QueryDict('order_by=test_column'), ['state__extra_data__test_column']),
            TestCase('order_by multiple columns', QueryDict('order_by=city&order_by=site_eui'), ['state__city', 'state__site_eui']),
            TestCase('order_by defaults to id', QueryDict(''), ['id']),
            TestCase('order_by can handle descending operator', QueryDict('order_by=-site_eui'), ['-state__site_eui']),
        ]

        # -- Act
        for test_case in test_cases:
            columns = Column.retrieve_all(self.fake_org, 'property', only_used=False)
            _, order_by = build_view_filters_and_sorts(test_case.input, columns)

            # -- Assert
            self.assertEqual(
                order_by,
                test_case.expected,
                f'Failed "{test_case.name}"; actual: {order_by}; expected: {test_case.expected}'
            )
