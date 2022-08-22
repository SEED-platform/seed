from dataclasses import dataclass
from datetime import datetime

from django.db import models
from django.db.models import Q
from django.db.models.functions import Cast, NullIf, Replace
from django.http.request import QueryDict
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import Column, PropertyView
from seed.test_helpers.fake import FakePropertyViewFactory
from seed.utils.organizations import create_organization
from seed.utils.search import FilterException, build_view_filters_and_sorts


class TestInventoryViewSearchParsers(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.fake_user = User.objects.create(username='test')
        cls.fake_org, _, _ = create_organization(cls.fake_user)
        cls.property_view_factory = FakePropertyViewFactory(organization=cls.fake_org)

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
            columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
            filters, _, _ = build_view_filters_and_sorts(test_case.input, columns)

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
            expected_filter: Q
            expected_annotations: dict

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
            TestCase(
                name='extra_data column with string data_type',
                input=QueryDict('test_string=hello'),
                expected_filter=Q(_test_string_final='hello'),
                expected_annotations={
                    '_test_string_to_text': Cast('state__extra_data__test_string', output_field=models.TextField()),
                    '_test_string_final': Replace('_test_string_to_text', models.Value('"'), output_field=models.TextField()),
                }
            ),
            TestCase(
                name='extra_data column with number data_type',
                input=QueryDict('test_number=12.3'),
                expected_filter=Q(_test_number_final=12.3),
                expected_annotations={
                    '_test_number_to_text': Cast('state__extra_data__test_number', output_field=models.TextField()),
                    '_test_number_stripped': Replace('_test_number_to_text', models.Value('"'), output_field=models.TextField()),
                    '_test_number_cleaned': NullIf('_test_number_stripped', models.Value('null'), output_field=models.TextField()),
                    '_test_number_final': Cast('_test_number_cleaned', output_field=models.FloatField()),
                }
            ),
        ]

        for test_case in test_cases:
            # -- Act
            columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
            filters, annotations, _ = build_view_filters_and_sorts(test_case.input, columns)

            # -- Assert
            self.assertEqual(
                filters,
                test_case.expected_filter,
                f'Failed "{test_case.name}"; actual: {filters}; expected: {test_case.expected_filter}'
            )
            self.assertEqual(
                repr(annotations),
                repr(test_case.expected_annotations),
                f'Failed "{test_case.name}"; actual: {annotations}; expected: {test_case.expected_annotations}'
            )

    def test_parse_filters_returns_empty_q_object_for_invalid_columns(self):
        # -- Setup
        query_dict = QueryDict('this_column_does_not_exits=123')

        # -- Act
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
        filters, _, _ = build_view_filters_and_sorts(query_dict, columns)

        # -- Assert
        self.assertEqual(filters, Q())

    def test_parse_filters_can_handle_multiple_filters(self):
        # -- Setup
        query_dict = QueryDict('city=Denver&site_eui=100&gross_floor_area=200')

        # -- Act
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
        filters, _, _ = build_view_filters_and_sorts(query_dict, columns)

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
            columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
            filters, _, _ = build_view_filters_and_sorts(test_case.input, columns)

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
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
        filters, _, _ = build_view_filters_and_sorts(query_dict, columns)

        # -- Assert
        self.assertEqual(filters, ~Q(state__city='Denver'))

    def test_parse_filters_raises_exception_when_filter_value_is_invalid(self):
        # -- Setup
        # site_eui is a number type, so the string 'hello' will fail to be parsed
        query_dict = QueryDict('site_eui=hello')

        # -- Act, Assert
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
        with self.assertRaises(FilterException):
            build_view_filters_and_sorts(query_dict, columns)

    def test_parse_sorts_works(self):
        @dataclass
        class TestCase:
            name: str
            input: QueryDict
            expected_order_by: list[str]
            expected_annotations: dict

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
            TestCase(
                name='order_by canonical column',
                input=QueryDict('order_by=site_eui'),
                expected_order_by=['state__site_eui'],
                expected_annotations={}
            ),
            TestCase(
                name='order_by extra data string column',
                input=QueryDict('order_by=test_string'),
                expected_order_by=['_test_string_final'],
                expected_annotations={
                    '_test_string_to_text': Cast('state__extra_data__test_string', output_field=models.TextField()),
                    '_test_string_final': Replace('_test_string_to_text', models.Value('"'), output_field=models.TextField()),
                }
            ),
            TestCase(
                name='order_by extra data number column',
                input=QueryDict('order_by=test_number'),
                expected_order_by=['_test_number_final'],
                expected_annotations={
                    '_test_number_to_text': Cast('state__extra_data__test_number', output_field=models.TextField()),
                    '_test_number_stripped': Replace('_test_number_to_text', models.Value('"'), output_field=models.TextField()),
                    '_test_number_cleaned': NullIf('_test_number_stripped', models.Value('null'), output_field=models.TextField()),
                    '_test_number_final': Cast('_test_number_cleaned', output_field=models.FloatField()),
                }
            ),
            TestCase(
                name='order_by multiple columns',
                input=QueryDict('order_by=city&order_by=site_eui'),
                expected_order_by=['state__city', 'state__site_eui'],
                expected_annotations={}
            ),
            TestCase(
                name='order_by defaults to id',
                input=QueryDict(''),
                expected_order_by=['id'],
                expected_annotations={}
            ),
            TestCase(
                name='order_by can handle descending operator',
                input=QueryDict('order_by=-site_eui'),
                expected_order_by=['-state__site_eui'],
                expected_annotations={},
            ),
        ]

        # -- Act
        for test_case in test_cases:
            columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
            _, annotations, order_by = build_view_filters_and_sorts(test_case.input, columns)

            # -- Assert
            self.assertEqual(
                order_by,
                test_case.expected_order_by,
                f'Failed "{test_case.name}"; actual: {order_by}; expected: {test_case.expected_order_by}'
            )
            self.assertEqual(
                repr(annotations),
                repr(test_case.expected_annotations),
                f'Failed "{test_case.name}"; actual: {annotations}; expected: {test_case.expected_annotations}'
            )

    def test_filter_and_sorts_parser_annotations_works(self):
        # -- Setup
        # create extra data column with a number type
        Column.objects.create(
            column_name='test_number',
            data_type='number',
            is_extra_data=True,
            table_name='PropertyState',
            organization=self.fake_org,
        )

        # create two properties containing the extra data, but stored as a string!
        self.property_view_factory.get_property_view(
            extra_data={'test_number': '9'}
        )
        self.property_view_factory.get_property_view(
            extra_data={'test_number': '10'}
        )

        # just to prove that we can't do numeric filtering on these string values in extra data
        # i.e., the whole reason we are making these annotations which cast the
        # extra_data values
        uncast_property_views = PropertyView.objects.filter(state__extra_data__test_number__gte=10)
        self.assertEqual(uncast_property_views.count(), 0)

        # -- Act
        input = QueryDict('test_number__gte=10')
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
        filters, annotations, _ = build_view_filters_and_sorts(input, columns)
        cast_property_views = PropertyView.objects.annotate(**annotations).filter(filters)

        # -- Assert
        # we should only get one property view -- the one whose test_number is 10
        self.assertEqual(cast_property_views.count(), 1)

    def test_filter_and_sorts_parser_annotations_can_handle_null_values(self):
        """The database will complain if we try to cast the string 'null' (from extra data)
        into any type other than string. This test verifies we can handle the case
        where a property has a json null.
        """

        # -- Setup
        # create extra data column with a number type
        Column.objects.create(
            column_name='test_number',
            data_type='number',
            is_extra_data=True,
            table_name='PropertyState',
            organization=self.fake_org,
        )

        self.property_view_factory.get_property_view(
            extra_data={'test_number': None}
        )

        # -- Act
        input = QueryDict('test_number=10')
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
        filters, annotations, _ = build_view_filters_and_sorts(input, columns)
        cast_property_views = PropertyView.objects.annotate(**annotations).filter(filters)

        # -- Assert
        # evaluate the queryset -- no exception should be raised!
        list(cast_property_views)
