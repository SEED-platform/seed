# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
This files has faker methods for generating fake data.
The data is pseudo random, but still predictable. I.e. calling the same
method mutiple times will always return the same sequence of results
(after initialization)..
.. warning::
    Do not edit the seed unless you know what you are doing!
    .. codeauthor:: Paul Munday<paul@paulmunday.net>
"""
import datetime
import os
import re
import string
from collections import namedtuple

import mock
from django.db.models.fields.files import FieldFile
from django.utils import timezone
from faker import Factory

from seed.models import (
    Cycle, Column, GreenAssessment, GreenAssessmentURL, Measure,
    GreenAssessmentProperty, Property, PropertyAuditLog, PropertyView,
    PropertyState, StatusLabel, TaxLot, TaxLotAuditLog, TaxLotProperty,
    TaxLotState, TaxLotView, PropertyMeasure, Note, ColumnListSetting,
    ColumnListSettingColumn,
    VIEW_LIST,
    VIEW_LIST_PROPERTY)
from seed.models.auditlog import AUDIT_IMPORT, AUDIT_USER_CREATE
from seed.utils.strings import titlecase

Owner = namedtuple(
    'Owner',
    ['name', 'email', 'telephone', 'address', 'city_state', 'postal_code']
)

SEED = 'f89ceea9-2162-4e7f-a3ed-e0b76a0513d1'

# For added realism
STREET_SUFFIX = (
    'Avenue', 'Avenue', 'Avenue', 'Boulevard', 'Lane', 'Loop',
    'Road', 'Road', 'Street', 'Street', 'Street', 'Street'
)


class BaseFake(object):
    """
    Base class for fake factories.
    .. warning::
    *Always* call super, *first* when overridding init if you subclass this.
    """

    def __init__(self):
        self.fake = Factory.create()
        self.fake.seed(SEED)

    def _check_attr(self, attr):
        result = getattr(self, attr, None)
        if not result:
            msg = "{} was not set on instance of: {}".format(
                attr, self.__class__
            )
            raise AttributeError(msg)
        return result

    def _get_attr(self, attrname, attr=None):
        attr = attr if attr else self._check_attr(attrname)
        return attr

    def address_line_1(self):
        """Return realistic address line"""
        return "{} {} {}".format(
            self.fake.randomize_nb_elements(1000),
            self.fake.last_name(),
            self.fake.random_element(elements=STREET_SUFFIX)
        )

    def company(self, email=None):
        if not email:
            email = self.fake.company_email()
        ergx = re.compile(r'.*@(.*)\..*')
        company = "{} {}".format(
            string.capwords(ergx.match(email).group(1), '-').replace('-', ' '),
            self.fake.company_suffix()
        )
        return company

    def owner(self, city=None, state=None):
        """Return Owner named tuple"""
        email = self.fake.company_email()
        company = self.company(email)
        return Owner(
            company, email, self.fake.phone_number(), self.address_line_1(),
            "{}, {}".format(city if city else self.fake.city(),
                            state if state else self.fake.state_abbr()),
            self.fake.postalcode()
        )


class FakeColumnFactory(BaseFake):
    """
    Factory Class for producing Column instances.
    """

    def __init__(self, organization=None):
        super().__init__()
        self.organization = organization

    def get_column(self, name, organization=None, is_extra_data=False,
                   table_name='PropertyState', **kw):
        """Get column details."""
        column_details = {
            'organization': organization if organization else self.organization,
            'column_name': name,
            'table_name': table_name,
        }
        if is_extra_data:
            column_details.update({
                'is_extra_data': is_extra_data,
            })
        column_details.update(kw)
        return Column.objects.create(**column_details)


class FakeCycleFactory(BaseFake):
    """
    Factory Class for producing Cycle instances.
    """

    def __init__(self, organization=None, user=None):
        super().__init__()
        self.organization = organization
        self.user = user

    def get_cycle(self, organization=None, user=None, **kw):
        """Get cycle details."""
        # pylint:disable=unused-argument
        if 'start' in kw:
            start = kw.pop('start')
        else:
            start = datetime.datetime(2015, 1, 1, tzinfo=timezone.get_current_timezone())
        if 'end' in kw:
            end = kw.pop('end')
        else:
            end = start + datetime.timedelta(365)
        cycle_details = {
            'organization': getattr(self, 'organization', None),
            'user': getattr(self, 'user', None),
            'name': '{} Annual'.format(start.year),
            'start': start,
            'end': end,
        }
        cycle_details.update(kw)
        return Cycle.objects.create(**cycle_details)


class FakePropertyFactory(BaseFake):
    """
    Factory Class for producing Property instances.
    """

    def __init__(self, organization=None):
        super().__init__()
        self.organization = organization

    def get_property(self, organization=None, **kw):
        """Get property instance."""
        property_details = {
            'organization': self._get_attr('organization', organization),
        }
        property_details.update(kw)
        return Property.objects.create(**property_details)


class FakePropertyAuditLogFactory(BaseFake):
    """
    Factory Class for producing Property Audit Log instances.
    """

    def __init__(self, organization=None, user=None):
        self.organization = organization
        self.state_factory = FakePropertyStateFactory(organization=organization)
        self.view_factory = FakePropertyViewFactory(
            organization=organization, user=user
        )
        super().__init__()

    def get_property_audit_log(self, **kw):
        """Get property instance."""
        details = {
            'organization': self.organization,
            'record_type': AUDIT_USER_CREATE,
            'name': 'test audit log',
            'description': 'test audit log',
        }
        details.update(kw)
        if not details.get('state'):
            details['state'] = self.state_factory.get_property_state(organization=self.organization)
        if not details.get('view'):
            details['view'] = self.view_factory.get_property_view()
        return PropertyAuditLog.objects.create(**details)


class FakePropertyStateFactory(BaseFake):
    """
    Factory Class for producing PropertyState instances.
    """

    def __init__(self, num_owners=5, organization=None):
        # pylint:disable=unused-variable
        super().__init__()
        # pre-generate a list of owners so they occur more than once.
        self.owners = [self.owner() for i in range(num_owners)]
        self.organization = organization

    def get_details(self):
        """Return a dict of pseudo random data for use with PropertyState"""
        owner = self.fake.random_element(elements=self.owners)
        return {
            'jurisdiction_property_id': self.fake.numerify(text='#####'),
            'pm_parent_property_id': self.fake.numerify(text='#####'),
            'lot_number': self.fake.numerify(text='#####'),
            'address_line_1': self.address_line_1(),
            'city': 'Boring',
            'state': 'Oregon',
            'postal_code': "970{}".format(self.fake.numerify(text='##')),
            'year_built': self.fake.random_int(min=1880, max=2015),
            'site_eui': self.fake.random_int(min=50, max=600),
            'gross_floor_area': self.fake.random_number(digits=6),
            'owner': owner.name,
            'owner_email': owner.email,
            'owner_telephone': owner.telephone,
            'owner_address': owner.address,
            'owner_city_state': owner.city_state,
            'owner_postal_code': owner.postal_code,
        }

    def get_property_state_as_extra_data(self, organization=None, **kw):
        """Return the porperty state but only populated as extra_data (used for mapping)"""
        property_details = {}
        if 'no_default_data' not in kw:
            property_details = self.get_details()
        else:
            del kw['no_default_data']

        import_file_id = None
        if 'import_file_id' in kw:
            import_file_id = kw['import_file_id']
            del kw['import_file_id']

        data_state = None
        if 'data_state' in kw:
            data_state = kw['data_state']
            del kw['data_state']

        source_type = None
        if 'source_type' in kw:
            source_type = kw['source_type']
            del kw['source_type']

        property_details.update(kw)
        ps = PropertyState.objects.create(
            organization=self._get_attr('organization', self.organization),
            import_file_id=import_file_id,
            data_state=data_state,
            source_type=source_type,
            extra_data=property_details,
        )

        # Note that there is no audit log in this state which is typically the DATA_STATE_IMPORT
        return ps

    def get_property_state(self, organization=None, **kw):
        """Return a property state populated with pseudo random data"""
        property_details = {}
        if 'no_default_data' not in kw:
            property_details = self.get_details()
        else:
            del kw['no_default_data']

        property_details.update(kw)
        ps = PropertyState.objects.create(
            organization=self._get_attr('organization', self.organization),
            **property_details
        )
        # make sure to create an audit log so that we can test various methods (e.g. updating properties)
        PropertyAuditLog.objects.create(
            organization=self._get_attr('organization', self.organization),
            state=ps,
            record_type=AUDIT_IMPORT,
            name='Import Creation'
        )
        return ps


class FakePropertyViewFactory(BaseFake):
    """
    Factory Class for producing PropertyView instances.
    """

    def __init__(self, prprty=None, cycle=None, organization=None, user=None):
        super().__init__()
        self.prprty = prprty
        self.cycle = cycle
        self.organization = organization
        self.user = user
        self.property_factory = FakePropertyFactory(organization=organization)
        self.cycle_factory = FakeCycleFactory(organization=organization, user=user)
        self.state_factory = FakePropertyStateFactory(organization=organization)

    def get_property_view(self, prprty=None, cycle=None, state=None, organization=None, user=None,
                          **kwargs):
        # pylint:disable=too-many-arguments
        """Get property view instance."""
        organization = organization if organization else self.organization
        user = user if user else self.user
        if not prprty:
            prprty = self.prprty if self.prprty else self.property_factory.get_property(
                organization=organization)
        if not cycle:
            cycle = self.cycle if self.cycle else self.cycle_factory.get_cycle(
                organization=organization)
        property_view_details = {
            'property': prprty,
            'cycle': cycle,
            'state': state if state else self.state_factory.get_property_state(
                organization=organization, **kwargs)
        }
        return PropertyView.objects.create(**property_view_details)


class FakePropertyMeasureFactory(BaseFake):
    def __init__(self, organization, property_state=None):
        self.organization = organization

        if not property_state:
            self.property_state = FakePropertyStateFactory(
                organization=self.organization).get_property_state()
        else:
            self.property_state = property_state
        super().__init__()

    def assign_random_measures(self, number_of_measures=5, **kw):
        # remove any existing measures assigned to the property
        self.property_state.measures.all().delete()

        # assign a random number of measures to the PropertyState
        for n in range(number_of_measures):
            measure = Measure.objects.all().order_by('?')[0]
            property_measure_details = {
                'measure_id': measure.id,
                'property_measure_name': self.fake.text(),
                'property_state': self.property_state,
                'description': self.fake.text(),
                'implementation_status': PropertyMeasure.MEASURE_IN_PROGRESS,
                'application_scale': PropertyMeasure.SCALE_ENTIRE_SITE,
                'category_affected': PropertyMeasure.CATEGORY_AIR_DISTRIBUTION,
                'recommended': True,
                'cost_mv': self.fake.numerify(text='#####'),
                'cost_total_first': self.fake.numerify(text='#####'),
                'cost_installation': self.fake.numerify(text='#####'),
                'cost_material': self.fake.numerify(text='#####'),
                'cost_capital_replacement': self.fake.numerify(text='#####'),
                'cost_residual_value': self.fake.numerify(text='#####'),
            }
            PropertyMeasure.objects.create(**property_measure_details)

    def get_property_state(self, number_of_measures=5):
        """Return a measure"""
        self.assign_random_measures(number_of_measures)
        return self.property_state


class FakeGreenAssessmentFactory(BaseFake):
    """
    Factory Class for producing GreenAssessment instances.
    """

    def __init__(self, organization=None):
        self.organization = organization
        super().__init__()

    def get_details(self):
        """Generate details."""
        rtc = self.fake.random_element(
            elements=GreenAssessment.RECOGNITION_TYPE_CHOICES
        )
        color = titlecase(self.fake.safe_color_name())
        nelem = '' if rtc[1].startswith('Zero') else self.fake.random_element(
            elements=('Energy', 'Efficiency', 'Sustainability', 'Building')
        )
        award = '{} {}{}'.format(color, nelem, rtc[1])
        return {
            'name': award,
            'award_body': "{} {}".format(award, self.fake.company_suffix()),
            'recognition_type': rtc[0],
            'description': 'Fake Award',
            'is_numeric_score': True,
            'validity_duration': None,
            'organization': self.organization
        }

    def get_green_assessment(self, **kw):
        """Return a green assessment populated with pseudo random data."""
        green_assessment = self.get_details()
        validity_duration = kw.pop('validity_duration', None)
        if validity_duration:
            if isinstance(validity_duration, int):
                validity_duration = datetime.timedelta(validity_duration)
            if not (isinstance(validity_duration, datetime.timedelta)):
                raise TypeError('validity_duration must be an integer or timedelta')
            green_assessment['validity_duration'] = validity_duration
        green_assessment.update(kw)
        return GreenAssessment.objects.create(**green_assessment)


class FakeGreenAssessmentURLFactory(BaseFake):
    """
    Factory Class for producing GreenAssessmentURL instances.
    """

    def __init__(self):
        super().__init__()

    def get_url(self, property_assessment, url=None):
        """Generate Instance"""
        if not url:
            url = "{}{}".format(self.fake.url(), self.fake.slug())
        return GreenAssessmentURL.objects.create(
            property_assessment=property_assessment, url=url
        )


class FakeGreenAssessmentPropertyFactory(BaseFake):
    """
    Factory Class for producing GreenAssessmentProperty instances.
    """

    def __init__(self, organization=None, user=None):
        super().__init__()
        self.organization = organization
        self.user = user
        self.green_assessment_factory = FakeGreenAssessmentFactory()
        self.property_view_factory = FakePropertyViewFactory(
            organization=organization, user=user
        )
        self.url_factory = FakeGreenAssessmentURLFactory()

    def get_details(self, assessment, property_view, organization):
        """Get GreenAssessmentProperty details"""
        metric = self.fake.random_digit_not_null() if assessment.is_numeric_score else None
        rating = None if assessment.is_numeric_score else '{} stars'.format(
            self.fake.random.randint(1, 5))
        details = {
            'organization': organization,
            'view': property_view,
            'assessment': assessment,
            'date': self.fake.date_time_this_decade().date()
        }
        if metric:
            details['metric'] = metric
        elif rating:
            details['rating'] = rating
        return details

    def get_green_assessment_property(self, assessment=None, property_view=None, organization=None,
                                      user=None,
                                      urls=None, with_url=None, **kw):
        """
        Get a GreenAssessmentProperty instance.

        :param assessment: assessment instance
        :type assessment: GreenAssessment
        :param property_view: property_view instance
        :type property_view: PropertyView
        :param organization: organization instance
        :type organization: Organization
        :param user: user instance
        :type user: SEEDUser
        :param urls: list of urls (as string) to create as GreenAssessmentURLs
        :type urls: list of strings
        :param with_url: number of GreenAssessmentURLs to create
        :type with_url: int

        with_urls and urls are mutually exclusive.
        """
        # pylint:disable=too-many-arguments
        organization = organization if organization else self.organization
        user = user if user else self.user
        if not assessment:
            assessment = self.green_assessment_factory.get_green_assessment()
        if not property_view:
            property_view = self.property_view_factory.get_property_view(
                organization=organization, user=user
            )
        details = self.get_details(assessment, property_view, organization)
        details.update(kw)
        # remove the organization because it is not a valid field
        details.pop('organization', None)

        gap = GreenAssessmentProperty.objects.create(**details)
        if urls:
            for url in urls:
                self.url_factory.get_url(gap, url)
        elif with_url:
            # Add urls
            for _ in range(with_url):
                self.url_factory.get_url(gap)
        return gap


class FakeStatusLabelFactory(BaseFake):
    """
    Factory Class for producing StatusLabel instances.

    Since color choices are limited, we preconstruct a list of
    (color, name) tuples with values derived from COLOR_CHOICES
    and DEFAULT_LABELS, and return a label based on a random(ish)*
    choice from this unless name or color are overridden.

    * This is faker, its predictable based on seed passed to fake factory.
    """

    def __init__(self, organization=None):
        super().__init__()
        self.organization = organization
        self.colors = [color[0] for color in StatusLabel.COLOR_CHOICES]
        self.label_names = StatusLabel.DEFAULT_LABELS
        self.label_values = list(zip(self.colors, self.label_names))

    def get_statuslabel(self, organization=None, **kw):
        """Get statuslabel instance."""
        label_value = self.fake.random_element(elements=self.label_values)
        statuslabel_details = {
            'super_organization': self._get_attr('organization', organization),
            'name': label_value[1]
        }
        statuslabel_details.update(kw)
        label, created = StatusLabel.objects.get_or_create(**statuslabel_details)
        if created:
            # If a new label, then assign a color.
            label.color = label_value[0]

        return label


class FakeNoteFactory(BaseFake):
    """
    Facotry Class for producing Note instances.
    """

    def __init__(self, organization=None, user=None):
        self.organization = organization
        self.user = user
        super().__init__()

    def get_note(self, organization=None, user=None, **kw):
        """Get Note instance."""
        name = 'Nothing of importance'
        text = self.fake.text()
        note_details = {
            'organization_id': self._get_attr('organization', self.organization).pk,
            'note_type': Note.NOTE,
            'name': name,
            'text': text,
            'user': self._get_attr('user', self.user),
        }
        note_details.update(kw)
        note, _ = Note.objects.get_or_create(**note_details)
        return note

    def get_log_note(self, organization=None, user=None, **kw):
        name = 'Nothing of importance for log'
        text = 'Data changed'
        note_details = {
            'organization_id': self._get_attr('organization', self.organization).pk,
            'note_type': Note.LOG,
            'name': name,
            'text': text,
            'user': self._get_attr('user', self.user),
            'log_data': {
                'property_state': [
                    {
                        "field": "address_line_1",
                        "previous_value": "123 Main Street",
                        "new_value": "742 Evergreen Terrace"
                    }
                ]
            }
        }
        note_details.update(kw)
        note, _ = Note.objects.get_or_create(**note_details)
        return note


class FakeTaxLotFactory(BaseFake):
    """
    Factory Class for producing Taxlot instances.
    """

    def __init__(self, organization=None):
        super().__init__()
        self.organization = organization
        self.label_factory = FakeStatusLabelFactory(organization=organization)

    def get_taxlot(self, organization=None):
        """Get taxlot instance."""
        organization = self._get_attr('organization', organization)
        taxlot_details = {
            'organization': organization
        }
        taxlot = TaxLot.objects.create(**taxlot_details)
        return taxlot


class FakeTaxLotStateFactory(BaseFake):
    """
    Factory Class for producing TaxLotState instances.
    """

    def __init__(self, organization=None):
        super().__init__()
        self.organization = organization

    def get_details(self):
        """Get taxlot details."""
        taxlot_details = {
            'jurisdiction_tax_lot_id': self.fake.numerify(text='#####'),
            'block_number': self.fake.numerify(text='#####'),
            'address_line_1': self.address_line_1(),
            'address_line_2': '',
            'city': 'Boring',
            'state': 'Oregon',
            'postal_code': "970{}".format(self.fake.numerify(text='##')),
        }
        return taxlot_details

    def get_taxlot_state(self, organization=None, **kw):
        """Return a taxlot state populated with pseudo random data"""
        taxlot_details = {}
        if 'no_default_data' not in kw:
            taxlot_details = self.get_details()
        else:
            del kw['no_default_data']
        taxlot_details.update(kw)

        org = self._get_attr('organization', organization)
        tls = TaxLotState.objects.create(organization=org, **taxlot_details)
        TaxLotAuditLog.objects.create(
            organization=org, state=tls, record_type=AUDIT_IMPORT, name='Import Creation'
        )
        return tls


class FakeTaxLotPropertyFactory(BaseFake):
    """
    Factory Class for producing TaxlotView instances.
    """

    def __init__(self, prprty=None, cycle=None, organization=None, user=None):
        super().__init__()
        self.organization = organization
        self.user = user
        self.property_view_factory = FakePropertyViewFactory(
            prprty=prprty, cycle=cycle,
            organization=organization, user=user
        )
        self.taxlot_view_factory = FakeTaxLotViewFactory(
            organization=organization, user=user
        )
        self.cycle_factory = FakeCycleFactory(
            organization=organization, user=user
        )

    def get_taxlot_property(self, organization=None, user=None, **kwargs):
        """Get a fake taxlot property."""
        organization = self._get_attr('organization', organization)
        user = self._get_attr('user', user)
        cycle = kwargs.get(
            'cycle',
            self.cycle_factory.get_cycle(organization=organization, user=user)
        )
        property_view = kwargs.get('property_view')
        if not property_view:
            property_view = self.property_view_factory.get_property_view(
                prprty=kwargs.get('prprpty'), cycle=cycle,
                state=kwargs.get('property_state'),
                organization=organization, user=user
            )
        taxlot_view = kwargs.get('taxlot_view')
        if not taxlot_view:
            taxlot_view = self.taxlot_view_factory.get_taxlot_view(
                organization=organization, user=user,
                taxlot=kwargs.get('taxlot'), cycle=cycle,
                state=kwargs.get('taxlot_state')
            )
        return TaxLotProperty.objects.create(
            taxlot_view=taxlot_view, property_view=property_view, cycle=cycle
        )


class FakeTaxLotViewFactory(BaseFake):
    """
    Factory Class for producing TaxlotView instances.
    """

    def __init__(self, taxlot=None, cycle=None, organization=None, user=None):
        super().__init__()
        self.taxlot = taxlot
        self.cycle = cycle
        self.organization = organization
        self.user = user
        self.taxlot_factory = FakeTaxLotFactory(organization=organization)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=organization)
        self.cycle_factory = FakeCycleFactory(organization=organization, user=user)
        self.state_factory = FakeTaxLotStateFactory(organization=organization)

    def get_taxlot_view(self, taxlot=None, cycle=None, state=None, organization=None, user=None,
                        **kwargs):
        """Get a fake taxlot view."""
        organization = organization if organization else self.organization
        user = user if user else self.user
        if not taxlot:
            taxlot = self.taxlot if self.taxlot else self.taxlot_factory.get_taxlot(
                organization=organization)
        if not cycle:
            cycle = self.cycle if self.cycle else self.cycle_factory.get_cycle(
                organization=organization)
        property_view_details = {
            'taxlot': taxlot,
            'cycle': cycle,
            'state': state if state else self.state_factory.get_taxlot_state(
                organization=organization, **kwargs)
        }
        return TaxLotView.objects.create(**property_view_details)


class FakeColumnListSettingsFactory(BaseFake):
    """
    Factory Class for producing ColumnList Settings

    * This is faker, its predictable based on seed passed to fake factory.
    """

    def __init__(self, organization=None):
        super().__init__()
        self.organization = organization

    def get_columnlistsettings(self, organization=None,
                               inventory_type=VIEW_LIST_PROPERTY,
                               location=VIEW_LIST, **kw):
        """Get columnlistsettings instance."""
        if not organization:
            organization = self.organization

        cls_details = {
            'organization_id': organization.pk,
            'name': 'test column list setting',
            'settings_location': location,
            'inventory_type': inventory_type,
        }
        cls = ColumnListSetting.objects.create(**cls_details)

        columns = []
        if 'columns' in kw:
            # add the columns to the list of items
            for c in kw.pop('columns'):
                columns.append(Column.objects.get(organization=organization, column_name=c, table_name='PropertyState'))
        else:
            # use all the columns
            for c in Column.objects.filter(organization=organization):
                columns.append(c)

        # associate all the columns
        for idx, c in enumerate(columns):
            ColumnListSettingColumn.objects.create(column=c, column_list_setting=cls, order=idx)

        return cls


def mock_file_factory(name, size=None, url=None, path=None):
    """
    This creates a mock instance of a FieldFile from
    django.db.models.fields.files.
    This is used to represent a file stored in Django and is linked file storage
    so it handles uploading and saving to disk.
    The mock allow you to set the file name etc without having to save a file to disk.
    """
    # pylint: disable=protected-access
    mock_file = mock.MagicMock(spec=FieldFile)
    mock_file._committed = True
    mock_file.file_name = name
    mock_file.name = name
    mock_file.base_name = os.path.splitext(name)[0]
    mock_file.__unicode__.return_value = name

    def __eq__(other):
        if hasattr(other, 'name'):
            return name == other.name
        else:
            return name == other

    mock_file.__eq__.side_effect = __eq__

    def __ne__(other):
        return not __eq__(other)

    mock_file.__ne__.side_effect = __ne__
    mock_file._get_size.return_value = size
    mock_size = mock.PropertyMock(return_value=size)
    type(mock_file).size = mock_size
    mock_file._get_path.return_value = path
    mock_path = mock.PropertyMock(return_value=path)
    type(mock_file).path = mock_path
    mock_file._get_url.return_value = url
    mock_url = mock.PropertyMock(return_value=url)
    type(mock_file).url = mock_url
    mock_file._get_closed.return_value = True
    mock_closed = mock.PropertyMock(return_value=True)
    type(mock_file).closed = mock_closed
    return mock_file


def mock_queryset_factory(model, flatten=False, **kwargs):
    """
    Supplied a model and a list of key values pairs, where key is a
    field name on the model and value is a list of values to populate
    that field, returns a list of namedtuples to use as mock model instances.
    ..note::
        You are responsible for ensuring lists are the same length.
        The factory will attempt to set id/auto_field if not supplied,
        with a value corresponding to the list index + 1.
        If flatten == True append _id to the field_name in kwargs
    Usage:
    mock_queryset = mock_queryset_factory(
        Model, field1=[...], field2=[...]
    )
    :param: model: Model to base queryset on
    :flatten: append _id to  ForeignKey field names
    :kwargs: field_name: list of values for model.field...
    :return:
        [namedtuple('ModelName', [field1, field2])...]
    """
    # pylint: disable=protected-access, invalid-name
    auto_populate = None
    fields = list(model._meta.fields)
    auto_field = model._meta.auto_field
    if auto_field.name not in kwargs:
        auto_populate = auto_field.name
    field_names = [
        "{}_id".format(field.name)
        if field.get_internal_type() == 'ForeignKey' and flatten
        else field.name for field in fields
    ]
    Instance = namedtuple(model.__name__, field_names)
    count_name = field_names[0] if field_names[0] != auto_populate \
        else field_names[1]
    queryset = []
    for i in range(len(kwargs[count_name])):
        values = [
            kwargs[field][i] if field != auto_populate else i
            for field in field_names
        ]
        queryset.append(Instance(*values))
    return queryset


def mock_as_view(view, request, *args, **kwargs):
    """Mimic as_view() returned callable, but returns view instance.

    args and kwargs are the same you would pass to ``reverse()``
    Borrowed from: http://tech.novapost.fr/django-unit-test-your-views-en.html
    """
    view.request = request
    view.args = args
    view.kwargs = kwargs
    return view
