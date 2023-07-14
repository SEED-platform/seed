"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from dataclasses import dataclass
from datetime import datetime

from django.db import models
from django.db.models import Q
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce, Replace
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
        latitude_id = Column.objects.get(table_name="PropertyState", column_name="latitude").id
        year_built_id = Column.objects.get(table_name="PropertyState", column_name="year_built").id
        custom_id_1_id = Column.objects.get(table_name="PropertyState", column_name="custom_id_1").id
        property_footprint_id = Column.objects.get(table_name="PropertyState", column_name="property_footprint").id
        updated_id = Column.objects.get(table_name="PropertyState", column_name="updated").id
        year_ending_id = Column.objects.get(table_name="PropertyState", column_name="year_ending").id
        gross_floor_area_id = Column.objects.get(table_name="PropertyState", column_name="gross_floor_area").id
        site_eui_id = Column.objects.get(table_name="PropertyState", column_name="site_eui").id

        test_cases = [
            TestCase('canonical column with number data_type', QueryDict(f'latitude_{latitude_id}=12.3'), Q(state__latitude=12.3)),
            TestCase('canonical column with integer data_type', QueryDict(f'year_built_{year_built_id}=123'), Q(state__year_built=123)),
            TestCase('canonical column with string data_type', QueryDict(f'custom_id_1_{custom_id_1_id}=123'), Q(state__custom_id_1='123')),
            TestCase('canonical column with geometry data_type', QueryDict(f'property_footprint_{property_footprint_id}=abcdefg'), Q(state__property_footprint='abcdefg')),
            TestCase('canonical column with datetime data_type', QueryDict(f'updated_{updated_id}=2022-01-01 10:11:12'), Q(state__updated=datetime(2022, 1, 1, 10, 11, 12))),
            TestCase('canonical column with date data_type', QueryDict(f'year_ending_{year_ending_id}=2022-01-01'), Q(state__year_ending=datetime(2022, 1, 1).date())),
            TestCase('canonical column with area data_type', QueryDict(f'gross_floor_area_{gross_floor_area_id}=12.3'), Q(state__gross_floor_area=12.3)),
            TestCase('canonical column with eui data_type', QueryDict(f'site_eui_{site_eui_id}=12.3'), Q(state__site_eui=12.3)),
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
        test_string_column = Column.objects.create(
            **{
                'column_name': 'test_string',
                'data_type': 'string',
                'is_extra_data': True,
                'table_name': 'PropertyState',
                'organization': self.fake_org,
            }
        )
        test_number_column = Column.objects.create(
            **{
                'column_name': 'test_number',
                'data_type': 'number',
                'is_extra_data': True,
                'table_name': 'PropertyState',
                'organization': self.fake_org,
            }
        )

        test_cases = [
            TestCase(
                name='extra_data column with string data_type',
                input=QueryDict(f'{test_string_column.column_name}_{test_string_column.id}=hello'),
                expected_filter=Q(_test_string_final='hello'),
                expected_annotations={
                    '_test_string_to_text': KeyTextTransform('test_string', 'state__extra_data',
                                                             output_field=models.TextField()),
                    '_test_string_final': Coalesce('_test_string_to_text', models.Value(''),
                                                   output_field=models.TextField()),
                }
            ),
            TestCase(
                name='extra_data column with number data_type',
                input=QueryDict(f'{test_number_column.column_name}_{test_number_column.id}=12.3'),
                expected_filter=Q(_test_number_final=12.3),
                expected_annotations={
                    '_test_number_to_text': KeyTextTransform('test_number', 'state__extra_data',
                                                             output_field=models.TextField()),
                    '_test_number_final': Cast(
                        Replace('_test_number_to_text', models.Value(','), models.Value('')),
                        output_field=models.FloatField()),
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
        city_id = Column.objects.get(table_name="PropertyState", column_name="city").id
        site_eui_id = Column.objects.get(table_name="PropertyState", column_name="site_eui").id
        gross_floor_area_id = Column.objects.get(table_name="PropertyState", column_name="gross_floor_area").id
        query_dict = QueryDict(f'city_{city_id}=Denver&site_eui_{site_eui_id}=100&gross_floor_area_{gross_floor_area_id}=200')

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
        site_eui_id = Column.objects.get(table_name="PropertyState", column_name="site_eui").id

        test_cases = [
            TestCase('field lookup <', QueryDict(f'site_eui_{site_eui_id}__lt=12.3'), Q(state__site_eui__lt=12.3)),
            TestCase('field lookup <=', QueryDict(f'site_eui_{site_eui_id}__lte=12.3'), Q(state__site_eui__lte=12.3)),
            TestCase('field lookup >', QueryDict(f'site_eui_{site_eui_id}__gt=12.3'), Q(state__site_eui__gt=12.3)),
            TestCase('field lookup >=', QueryDict(f'site_eui_{site_eui_id}__gte=12.3'), Q(state__site_eui__gte=12.3)),
            TestCase('field lookup exact', QueryDict(f'site_eui_{site_eui_id}__exact=12.3'), Q(state__site_eui__exact=12.3)),
            TestCase('field lookup icontains', QueryDict(f'site_eui_{site_eui_id}__icontains=12.3'), Q(state__site_eui__icontains=12.3)),
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
        city_id = Column.objects.get(table_name="PropertyState", column_name="city").id
        query_dict = QueryDict(f'city_{city_id}__ne=Denver')

        # -- Act
        columns = Column.retrieve_all(self.fake_org, 'property', only_used=False, include_related=False)
        filters, _, _ = build_view_filters_and_sorts(query_dict, columns)

        # -- Assert
        self.assertEqual(filters, ~Q(state__city='Denver'))

    def test_parse_filters_raises_exception_when_filter_value_is_invalid(self):
        # -- Setup
        # site_eui is a number type, so the string 'hello' will fail to be parsed
        site_eui_id = Column.objects.get(table_name="PropertyState", column_name="site_eui").id
        query_dict = QueryDict(f'site_eui_{site_eui_id}=hello')

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
        test_string_column = Column.objects.create(
            **{
                'column_name': 'test_string',
                'data_type': 'string',
                'is_extra_data': True,
                'table_name': 'PropertyState',
                'organization': self.fake_org,
            }
        )
        test_number_column = Column.objects.create(
            **{
                'column_name': 'test_number',
                'data_type': 'number',
                'is_extra_data': True,
                'table_name': 'PropertyState',
                'organization': self.fake_org,
            }
        )

        site_eui_id = Column.objects.get(table_name="PropertyState", column_name="site_eui").id
        city_id = Column.objects.get(table_name="PropertyState", column_name="city").id

        test_cases = [
            TestCase(
                name='order_by canonical column',
                input=QueryDict(f'order_by=site_eui_{site_eui_id}'),
                expected_order_by=['state__site_eui'],
                expected_annotations={}
            ),
            TestCase(
                name='order_by extra data string column',
                input=QueryDict(f'order_by=test_string_{test_string_column.id}'),
                expected_order_by=['_test_string_final'],
                expected_annotations={
                    '_test_string_to_text': KeyTextTransform('test_string', 'state__extra_data', output_field=models.TextField()),
                    '_test_string_final': Coalesce('_test_string_to_text', models.Value(''), output_field=models.TextField()),
                }
            ),
            TestCase(
                name='order_by extra data number column',
                input=QueryDict(f'order_by=test_number_{test_number_column.id}'),
                expected_order_by=['_test_number_final'],
                expected_annotations={
                    '_test_number_to_text': KeyTextTransform('test_number', 'state__extra_data', output_field=models.TextField()),
                    '_test_number_final': Cast(
                        Replace('_test_number_to_text', models.Value(','), models.Value('')), output_field=models.FloatField()),
                }
            ),
            TestCase(
                name='order_by multiple columns',
                input=QueryDict(f'order_by=city_{city_id}&order_by=site_eui_{site_eui_id}'),
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
                input=QueryDict(f'order_by=-site_eui_{site_eui_id}'),
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
        test_number_column = Column.objects.create(
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
        input = QueryDict(f'test_number_{test_number_column.id}__gte=10')
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
