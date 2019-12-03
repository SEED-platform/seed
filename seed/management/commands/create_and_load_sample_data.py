# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import datetime
import itertools
import logging
from random import randint

from django.core.management.base import BaseCommand

import seed.models
from seed.lib.superperms.orgs.models import Organization
from seed.test_helpers.fake import FakePropertyStateFactory, FakeTaxLotStateFactory, BaseFake

logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger(__name__)

BUILDING_USE = ('Hospital', 'Hotel', 'Office', 'University', 'Retail')

USE_CLASS = ('A', 'B', 'C', 'D', 'E')

COMPLIANCE = ('Y', 'N')

# Just a list of counties to pick from.
COUNTIES = ("Los Angeles County", "Orange County", "San Diego County", "Riverside County",
            "San Bernardino County", "Santa Clara County", "Alameda County", "Sacramento County",
            "Contra Costa County", "Fresno County", "Ventura County", "San Francisco County",
            "Kern County", "San Mateo County", "San Joaquin County", "Stanislaus County",
            "Sonoma County", "Tulare County", "Solano County", "Monterey County",
            "Santa Barbara County",
            "Placer County", "San Luis Obispo County", "Santa Cruz County", "Merced County",
            "Marin County", "Butte County", "Yolo County", "El Dorado County", "Shasta County",
            "Imperial County", "Kings County", "Madera County", "Napa County", "Humboldt County",
            "Nevada County", "Sutter County", "Mendocino County", "Yuba County", "Lake County",
            "Tehama County", "Tuolumne County", "San Benito County", "laveras County",
            "Siskiyou County",
            "Amador County", "Lassen County", "Del Norte County", "Glenn County", "Plumas County",
            "Colusa County", "Mariposa County", "Inyo County", "Trinity County", "Mono County",
            "Modoc County", "Sierra County", "Alpine County")


# Due to the way extra data was being handled regarding record creation
# it seemed most expedient to just define a temporary class
# to hold both normal and extra data for later.  This is because
# the creation code expects extra_data to be kept elsewhere while the
# record is initially created and adds it after creation.
class SampleDataRecord(object):
    """
    Just a holder for state data and extra data.
    """

    def __init__(self, data, extra_data):
        self.data = data
        self.extra_data = extra_data


class FakePropertyStateExtraDataFactory(BaseFake):
    """
    Factory Class for producing extra data dict for PropertyState
    """

    def __init__(self):
        super().__init__()

    def property_state_extra_data_details(self, id, organization):
        """
        Creates randomized extra data for properties.
        :param id: just used to populate one of the fields so it is clear
                    which extra data fields are associated to which records
        :param org: used to populate the "Organization" field.
        :return: a dict of pseudo random data for use with properties
        """

        property_extra_data = {
            "CoStar Property ID": self.fake.numerify(text='#######'),
            "Organization": organization.name,
            "Compliance Required": self.fake.random_element(elements=COMPLIANCE),
            "County": self.fake.random_element(elements=COUNTIES),
            "Date / Last Personal Correspondence": self.fake.date(pattern='%m/%d/%Y'),
            "property_extra_data_field_1": "property_extra_data_field_" + str(id),
            "Does Not Need to Comply": self.fake.random_element(elements=COMPLIANCE)
        }

        property_extra_data = {k: str(v) for k, v in property_extra_data.items()}

        return property_extra_data

    def property_state_extra_data(self, id, organization, **kw):
        """
        Creates randomized extra data for properties.
        :param id: just used to populate one of the fields so it is clear
                    which extra data fields are associated to which records
        :param org: used to populate the "Organization" field.
        :return: a dict of pseudo random data for use with properties updated with keyword args from the caller
        """
        ps = self.property_state_extra_data_details(id, organization)
        ps.update(kw)
        return ps


class CreateSampleDataFakePropertyStateFactory(FakePropertyStateFactory):
    """
    Factory Class for producing PropertyState dict
    """

    def __init__(self, organization, year_ending, case_description, extra_data_factory):
        """
        :param organization: The organization that will own the created records
        :param year_ending: datetime, used to populate the "year_ending" field
        :param case_description: string, used to populate the "property_notes" field
                                 Useful for sorting by case in the web client.
        :param extra_data_factory: FakePropertyStateExtraDataFactory,
                used to generate randomized extra data.
        """

        super().__init__()

        self.organization = organization
        self.year_ending = year_ending
        self.case_description = case_description
        self.extra_data_factory = extra_data_factory

    def _generate_jurisdiction_property_id(self):
        """
        Generates something that resembles a jurisdiction_property_id.
        This is a somewhat vaguely defined identifier with the following rules:

        1:  There is at most two groups of characters separated by an optional dash
        2:  Each group of characters must have at least one digit.
        3:  Each group can be at most 3 digits plus one optional trailing letter.

        :return: a string of between 2 and 9 characters which follow some rules about
                 what these identifiers look like in some cases
        """
        append_choices = ("a", "b", "c")
        first_number = str(randint(1, 999))
        second_number = str(randint(1, 999))
        res = None

        if randint(0, 1):
            first_number += self.fake.random_element(elements=append_choices)
        if randint(0, 1):
            second_number += self.fake.random_element(elements=append_choices)
        if randint(0, 1):
            res = first_number + "-" + second_number
        else:
            res = first_number + second_number

        return res

    def property_state_details(self):
        """
        :return: a dict of pseudo random property data
        """
        owner = self.owner()
        property = self.get_details()

        pm_property_id = self.fake.numerify(text='#######')
        extra_data = self.extra_data_factory.property_state_extra_data(
            pm_property_id, self.organization)

        # This field was not in case A, B, or C for the original examples so removing it from the
        # dict.  Case D handles this itself.
        fields_to_remove = ["pm_parent_property_id"]
        for field in fields_to_remove:
            del property[field]

        # Add in fields that were in the original examples but are not in the base factory.
        data_not_in_base = {
            "pm_property_id": pm_property_id,
            "property_name": owner.name + "'s " + self.fake.random_element(elements=BUILDING_USE),
            "use_description": self.fake.random_element(elements=BUILDING_USE),
            "energy_score": self.fake.numerify(text='##'),
            "site_eui": self.fake.numerify(text='###.#'),
            "year_ending": self.year_ending,
            "gross_floor_area": self.fake.numerify(text='#######'),
            "property_notes": self.case_description,
            "home_energy_score_id": randint(88888, 111111),
            "jurisdiction_property_id": self._generate_jurisdiction_property_id()}

        property.update(data_not_in_base)

        property_record = SampleDataRecord(property, extra_data)
        return property_record

    def property_state(self, **kw):
        """
        :return: a dict populated with pseudo random data updated with keyword args from caller
        """
        ps = self.property_state_details()
        ps.data.update(kw)
        return ps


class FakeTaxLotExtraDataFactory(BaseFake):
    """
    Factory Class for producing taxlot extra data dict
    """

    def __init__(self):
        super().__init__()

    def tax_lot_extra_data_details(self, id, year_ending):
        """
        :param id: just used to populate one of the fields so it is clear
                    which extra data fields are associated to which records
        :param year_ending: int, used as the value for the "Tax Year"
        :return: a dict of pseudo random data for use with taxlots
        """
        owner = self.owner()

        tl = {"Owner City": self.fake.city(),
              "Tax Year": year_ending,
              "Parcel Gross Area": self.fake.numerify(text='####-###'),
              "Use Class": self.fake.random_element(elements=USE_CLASS),
              "Ward": self.fake.numerify(text='#'),
              "X Coordinate": self.fake.latitude(),
              "Y Coordinate": self.fake.longitude(),
              "Owner Name": owner.name,
              "Owner Address": self.address_line_1(),
              "Owner State": self.fake.state_abbr(),
              "Owner Zip": self.fake.zipcode(),
              "Tax Class": self.fake.random_element(elements=USE_CLASS) + self.fake.numerify(
                  text='#'),
              "taxlot_extra_data_field_1": "taxlot_extra_data_field_" + str(id),
              "City Code": self.fake.numerify(text='####-###')}

        tl = {k: str(v) for k, v in tl.items()}

        return tl

    def tax_lot_extra_data(self, id, year_ending, **kw):
        """
        :param id: just used to populate one of the extra data fields so it is clear
                    which extra data fields are associated to which records
        :return: a tax state dict populated with pseudo random data updated with keyword arguments
        """
        tl = self.tax_lot_extra_data_details(id, year_ending)
        tl.update(kw)
        return tl


class CreateSampleDataFakeTaxLotFactory(FakeTaxLotStateFactory):
    """
    Factory Class for producing randomized taxlot data.
    """

    def __init__(self, extra_data_factory):
        """
        :param extra_data_factory: FakeTaxLotStateExtraDataFactory,
                used to generate randomized extra data.
        """
        super().__init__()
        self.extra_data_factory = extra_data_factory

    def tax_lot_details(self):
        """
        :return: A dict containing randomized taxlot data
        """
        tl = self.get_details()
        jurisdiction_tax_lot_id = self.fake.numerify(text='########')

        # Add in fields that were in the original examples but are not in the base factory.
        data_not_in_base = {
            "jurisdiction_tax_lot_id": jurisdiction_tax_lot_id,
            "address_line_1": self.address_line_1(),
            "city": self.fake.city()
        }

        tl.update(data_not_in_base)
        extra_data = self.extra_data_factory.tax_lot_extra_data(
            jurisdiction_tax_lot_id,
            self.fake.random_int(min=2010, max=2015)
        )

        tax_lot_record = SampleDataRecord(tl, extra_data)
        return tax_lot_record

    def tax_lot(self, **kw):
        """
        :return: A dict containing randomized taxlot data updated with keyword arguments passed by caller
        """
        tl = self.tax_lot_details()
        tl.data.update(kw)
        return tl


def get_cycle(org, year=2015):
    """
    Gets (or creates if it does not exist) a year-long cycle for an organization.
    :param org: the organization associated with the cycle
    :param year: int, the year for the cycle
    :return: cycle starting on datetime(year, 1, 1, 0, 0, 0) and ending on
                datetime(year, 12, 31, 23, 59, 59)
    """
    cycle, _ = seed.models.Cycle.objects.get_or_create(
        name="{y} Annual".format(y=year),
        organization=org,
        start=datetime.datetime(year, 1, 1),
        end=datetime.datetime(year + 1, 1, 1) - datetime.timedelta(seconds=1)
    )
    return cycle


def update_taxlot_noise(taxlot):
    """
    Updates the "noise" in a taxlot state.  The noise is just some value
    that changes with every new taxlot regradless of anything else
    :param taxlot: SampleDataRecord with taxlot data.
    :return: The same taxlot with the confidence updated to a random number
    """
    # The issue is that nothing is changing in the non-extra_data fields
    # in the TaxLotState between years so when the code creates the second
    # year from the same input as the first it finds the first instead of
    # creating a new one.  Correct solution is probably to rework the
    # create_cases function but this is much faster and should work
    # just fine for creating sample data
    return taxlot


def create_cases(org, cycle, tax_lots, properties):
    """
    Handles the logic for creating the A, B, and C cases.
    Makes records out of the cartesian product of tax_lots and properties.
    :param org: the organization that will own the new records
    :param cycle: the cycle the new records will belong to.
        Currently this is a single cycle so all created records will
        belong to the same cycle.  That is, cases where property data is
        from one cycle and tax data is from another is not supported.
    :param taxlots : list of taxlot data in dict form.
    :param properties: list of taxlot data in dict form
    """

    created_property_views = []
    created_taxlot_views = []

    for (tl_rec, prop_rec) in itertools.product(tax_lots, properties):
        tl_def = tl_rec.data
        prop_def = prop_rec.data
        tl_extra_data = tl_rec.extra_data
        prop_extra_data = prop_rec.extra_data

        def del_datetimes(d):
            res = {}
            for k, v in d.items():
                if isinstance(v, datetime.date) or isinstance(v, datetime.datetime):
                    continue
                res[k] = str(v)
            return res

        tl_def = del_datetimes(tl_def)
        prop_def = del_datetimes(prop_def)
        tl_extra_data = del_datetimes(tl_extra_data)
        prop_extra_data = del_datetimes(prop_extra_data)

        # states don't have an org and since this script was doing all buildings twice
        # (once for individual, once for _caseALL).  So if the get_or_create returns
        # an existing one then it still is unknown if it is something that already exists.
        # Check the view model to see if there is something with this state and this org.
        # If it does not exist thencreate one.  If it does exist than that is correct (hopefully)
        #
        # FIXME.  In the instance where this script is creating both individual cases and _caseALL this
        # throws an error for some taxlots that multiple are returned.  Since TaxLotState does not depend
        # on an org I think this might have to go something like filter the view for this org and a state that
        # has fields that match **state_def.  However per Robin we are OK just restricting things to
        # the _caseALLL case for now so this is not currently a problem.
        def _create_state(view_model, state_model, org, state_def):
            state, created = state_model.objects.get_or_create(**state_def)
            if not created and not view_model.objects.filter(state=state).filter(
                    cycle__organization=org).exists():
                state = state_model.objects.create(**state_def)
                created = True
            return state, created

        prop_state, property_state_created = _create_state(seed.models.PropertyView,
                                                           seed.models.PropertyState,
                                                           org,
                                                           prop_def)

        for k, v in prop_extra_data.items():
            prop_state.extra_data[k] = v

        prop_state.save()

        taxlot_state, taxlot_state_created = _create_state(seed.models.TaxLotView,
                                                           seed.models.TaxLotState,
                                                           org,
                                                           tl_def)

        for k, v in tl_extra_data.items():
            taxlot_state.extra_data[k] = v

        taxlot_state.save()

        # Moved the property and taxlot items below the state items because they only depend on an org
        # So if they are just left at the top as get_or_create(organization=org) then there will only
        # be one property created per org.  Instead for creating this data if the state was created
        # then a property/taxlot needs to be created too.
        if property_state_created:
            property = seed.models.Property.objects.create(organization=org)
        else:
            # else the propery_state already existed so there should also be a PropertyView
            # with this with this property_state.  Find and use that property.
            property = seed.models.PropertyView.objects.filter(state=prop_state).filter(
                property__organization=org)[0].property

        if taxlot_state_created:
            taxlot = seed.models.TaxLot.objects.create(organization=org)
        else:
            # else the taxlot_state already existed so there should also be a TaxlotView
            # with this with this taxlot_state.  Find and use that taxlot.
            taxlot = seed.models.TaxLotView.objects.filter(state=taxlot_state).filter(
                taxlot__organization=org)[0].taxlot

        taxlot_view, created = seed.models.TaxLotView.objects.get_or_create(taxlot=taxlot,
                                                                            cycle=cycle,
                                                                            state=taxlot_state)
        if created:
            created_taxlot_views.append(taxlot_view)

        prop_view, created = seed.models.PropertyView.objects.get_or_create(property=property,
                                                                            cycle=cycle,
                                                                            state=prop_state)
        if created:
            created_property_views.append(prop_view)

        tlp, created = seed.models.TaxLotProperty.objects.get_or_create(property_view=prop_view,
                                                                        taxlot_view=taxlot_view,
                                                                        cycle=cycle)

    return created_taxlot_views, created_property_views


def update_taxlot_views(views, number_of_updates):
    """
    Changes some data in the underlying state and then updates the view to create an audit log

    :param viws: list of TaxLotViews to be updated
    :param number_of_updates: int, number of times to update (the number of audit records to be created)
    """
    for i in range(number_of_updates):
        for taxlot_view in views:
            state = taxlot_view.state
            state.pk = None  # set state to None to get a new copy on save
            state.save()
            taxlot_view.update_state(state)


def update_property_views(views, number_of_updates):
    """
    Changes some data in the underlying state and then updates the view to create an audit log

    :param viws: list of PropertyViews to be updated
    :param number_of_updates: int, number of times to update (the number of audit records to be created)
    """
    for i in range(number_of_updates):
        for property_view in views:
            state = property_view.state
            state.site_eui = str(float(randint(0, 1000)) + float(randint(0, 9)) / 10)
            state.pk = None  # set state to None to get a new copy on save
            state.save()
            property_view.update_state(state)


def create_cases_with_multi_records_per_cycle(org, cycle, taxlots, properties, number_records=1):
    """
    Creating the A, B, or C cases multiple times per cycle creates an audit log.
    Makes records out of the cartesian product of tax_lots and properties.
    :param org: the organization that will own the new records
    :param cycle: the cycle the new records will belong to.
        Currently this is a single cycle so all created records will
        belong to the same cycle.  That is, cases where property data is
        from one cycle and tax data is from another is not supported.
    :param taxlots : list of taxlot data in dict form.
    :param properties: list of taxlot data in dict form
    :param number_records: number of times to loop through creating the cases
    """

    taxlot_views, property_views = create_cases(org, cycle, taxlots, properties)
    update_taxlot_views(taxlot_views, number_records)
    update_property_views(property_views, number_records)

    return taxlots, properties


# For all cases make it so the city is the same within a case.  Not strictly required but
# it is more realistic
def create_case_A(org, cycle, taxlot_factory, property_factory, number_records_per_cycle=1):
    """
    Creates one instance of Case A (one building, one taxlot) for the given org in the given cycle
    :param org: Organization, the organization that will own the created cases
    :param cycle: Cycle, the cycle the created records will be associated with
    :param taxlot_factory: CreateSampleDataFakeTaxLotFactory, used to generate the randomized taxlot data
    :param property_factory: CreateSampleDataFakePropertyFactory, used to generate the randomized property data
    :param number_records_per_cycle: int, number of records to create each cycle for each created propertystate and taxlot
    :return: two lists of SampleDataRecords.  First is a list of taxlots and second is a list of properties
    """
    taxlot = taxlot_factory.tax_lot()
    taxlots = [taxlot]
    properties = [property_factory.property_state(address_line_1=taxlot.data["address"],
                                                  city=taxlot.data["city"])]

    taxlots, properties = create_cases_with_multi_records_per_cycle(org, cycle, taxlots, properties,
                                                                    number_records_per_cycle)

    return taxlots, properties


def create_case_B(org, cycle, taxlot_factory, property_factory, number_properties=3,
                  number_records_per_cycle=1):
    """
    Creates one instance of Case B (n buildings, one taxlot) for the given org in the given cycle
    :param org: Organization, the organization that will own the created cases
    :param cycle: Cycle, the cycle the created records will be associated with
    :param taxlot_factory: CreateSampleDataFakeTaxLotFactory, used to generate the randomized taxlot data
    :param property_factory: CreateSampleDataFakePropertyFactory, used to generate the randomized property data
    :return: two lists of SampleDataRecords.  First is a list of taxlots and second is a list of properties
    """
    taxlots = [taxlot_factory.tax_lot()]

    properties = []
    for i in range(number_properties):
        properties.append(property_factory.property_state(city=taxlots[0].data["city"]))

    taxlots, properties = create_cases_with_multi_records_per_cycle(org, cycle, taxlots, properties,
                                                                    number_records_per_cycle)

    return taxlots, properties


def create_case_C(org, cycle, taxlot_factory, property_factory, number_taxlots=3,
                  number_records_per_cycle=1):
    """
    Creates one instance of Case C (one building, n taxlot) for the given org in the given cycle
    :param org: Organization, the organization that will own the created cases
    :param cycle: Cycle, the cycle the created records will be associated with
    :param taxlot_factory: CreateSampleDataFakeTaxLotFactory, used to generate the randomized taxlot data
    :param property_factory: CreateSampleDataFakePropertyFactory, used to generate the randomized property data
    :return: two lists of SampleDataRecords.  First is a list of taxlots and second is a list of properties
    """
    properties = [property_factory.property_state()]

    taxlots = []
    for i in range(number_taxlots):
        taxlots.append(taxlot_factory.tax_lot(city=properties[0].data["city"]))

    taxlots, properties = create_cases_with_multi_records_per_cycle(org, cycle, taxlots, properties,
                                                                    number_records_per_cycle)

    return taxlots, properties


def _create_case_D(org, cycle, taxlots, properties, campus, number_records_per_cycle_per_state=1):
    """
    Creates one instance of Case D (n buildings, m taxlots, one campus) for the given org in the given cycle
    :param org: Organization, the organization that will own the created cases
    :param cycle: Cycle, the cycle the created records will be associated with
    :param taxlots: list of SampleDataRecords containing taxlot data
    :param properties: list of SampleDataRecords containing property data
    :param campus: SampleDataRecord of property data
    :return: None
    """

    def add_extra_data(state, extra_data):
        if not extra_data:
            return state

        for k in extra_data:
            state.extra_data[k] = extra_data[k]
        state.save()
        return state

    def _create_states_with_extra_data(model, records):
        states = []
        for rec in records:
            state = model.objects.get_or_create(**rec.data)[0]
            state = add_extra_data(state, rec.extra_data)
            states.append(state)
        return states

    taxlots = list(map(update_taxlot_noise, taxlots))
    properties = list(map(update_property_noise, properties))
    campus = update_property_noise(campus)

    campus_property = seed.models.Property.objects.create(organization=org, campus=True)
    property_objs = [
        seed.models.Property.objects.create(organization=org, parent_property=campus_property) for p
        in properties]

    property_objs.insert(0, campus_property)
    taxlot_objs = [seed.models.TaxLot.objects.create(organization=org) for t in taxlots]

    property_states = _create_states_with_extra_data(seed.models.PropertyState,
                                                     [campus] + properties)
    property_views = [seed.models.PropertyView.objects.get_or_create(property=property, cycle=cycle,
                                                                     state=prop_state)[0] for
                      (property, prop_state) in list(zip(property_objs, property_states))]

    taxlot_states = _create_states_with_extra_data(seed.models.TaxLotState, taxlots)
    taxlot_views = [seed.models.TaxLotView.objects.get_or_create(taxlot=taxlot, cycle=cycle,
                                                                 state=taxlot_state)[0] for
                    (taxlot, taxlot_state) in list(zip(taxlot_objs, taxlot_states))]

    seed.models.TaxLotProperty.objects.get_or_create(property_view=property_views[0],
                                                     taxlot_view=taxlot_views[0], cycle=cycle)
    seed.models.TaxLotProperty.objects.get_or_create(property_view=property_views[1],
                                                     taxlot_view=taxlot_views[0], cycle=cycle)
    seed.models.TaxLotProperty.objects.get_or_create(property_view=property_views[2],
                                                     taxlot_view=taxlot_views[0], cycle=cycle)
    seed.models.TaxLotProperty.objects.get_or_create(property_view=property_views[3],
                                                     taxlot_view=taxlot_views[0], cycle=cycle)

    seed.models.TaxLotProperty.objects.get_or_create(property_view=property_views[4],
                                                     taxlot_view=taxlot_views[1], cycle=cycle)
    seed.models.TaxLotProperty.objects.get_or_create(property_view=property_views[4],
                                                     taxlot_view=taxlot_views[2], cycle=cycle)

    seed.models.TaxLotProperty.objects.get_or_create(property_view=property_views[5],
                                                     taxlot_view=taxlot_views[1], cycle=cycle)
    seed.models.TaxLotProperty.objects.get_or_create(property_view=property_views[5],
                                                     taxlot_view=taxlot_views[2], cycle=cycle)

    # create audit log information
    update_taxlot_views(taxlot_views, number_records_per_cycle_per_state)
    update_property_views(property_views, number_records_per_cycle_per_state)

    return taxlots, properties, campus


def create_case_D(org, cycle, taxlot_factory, property_factory, number_records_per_cycle_per_state=1):
    """
    Creates one instance of Case D (n buildings, m taxlots, one campus) for the given org in the given cycle
    :param org: Organization, the organization that will own the created cases
    :param cycle: Cycle, the cycle the created records will be associated with
    :param taxlot_factory: CreateSampleDataFakeTaxLotFactory, used to generate the randomized taxlot data
    :param property_factory: CreateSampleDataFakePropertyFactory, used to generate the randomized property data
    :return: three lists.  First two are lists of SampleDataRecords.  Third is the SampleDataRecord for the campus.
    """

    campus = property_factory.property_state()
    city = campus.data["city"]
    campus.data["pm_parent_property_id"] = campus.data["pm_property_id"]

    campus_property_id = campus.data["pm_parent_property_id"]

    taxlots = []
    for i in range(3):
        taxlots.append(taxlot_factory.tax_lot(city=city))

    properties = []
    for i in range(5):
        properties.append(
            property_factory.property_state(pm_parent_property_id=campus_property_id, city=city))

    taxlots, properties, campus = _create_case_D(
        org, cycle, taxlots, properties, campus, number_records_per_cycle_per_state
    )

    return taxlots, properties, campus


def update_taxlot_year(taxlot, year):
    """
    Updates existing taxlot data with information for a new year.  Includes both changing the
    actual year and changing some other values.
    :param taxlot: SampleDataRecord with taxlot data.
    :param year: int, the year to change to
    :return: SampleDataRecord with the applicable fields changed.
    """

    taxlot.extra_data['Tax Year'] = str(year)

    # change something else in extra_data aside from the year:
    taxlot.extra_data['taxlot_extra_data_field_1'] = taxlot.extra_data[
        'taxlot_extra_data_field_1'] + '_' + str(year)

    # update the noise
    taxlot = update_taxlot_noise(taxlot)

    return taxlot


def update_property_noise(property):
    """
    Updates the "noise" in a property state.  The noise is just some value
    that changes with every new property regradless of anything else
    :param property: SampleDataRecord with property data.
    :return: The same property with the site_eui updated to a random number
    """
    # randomize "site_eui"
    property.data["site_eui"] = str(float(randint(0, 1000)) + float(randint(0, 9)) / 10)
    return property


def update_property_year(property, year):
    """
    Updates existing property data with information for a new year.  Includes both changing the
    actual year and changing some other values.
    :param taxlot: SampleDataRecord with property data.
    :param year: int, the year to change to
    :return: SampleDataRecord with the applicable fields changed.
    """

    property.data['year_ending'] = property.data['year_ending'].replace(year=year)

    # change something in extra_data so something there changes too
    property.extra_data['property_extra_data_field_1'] = property.extra_data[
        'property_extra_data_field_1'] + '_' + str(year)

    property = update_property_noise(property)

    return property


def create_additional_years(org, years, pairs_taxlots_and_properties, case,
                            number_records_per_cycle_per_state=1):
    """
    Creates additional years of records from existing SampleDataRecords for all cases except D.
    :param org: Organization, the org that will own the new records
    :param years: list of ints.  The years to create the new records for
    :param pairs_taxlots_and_properties: list of pairs of lists of SampleDataRecords
        First item in the pair is a list of SampleDataRecords with taxlot data, second
        is a list of SampleDataRecords with property data.
        E.G Simplest case is A which is 1-1 which means each entry in pairs_taxlots_and_properties
        will look like [[taxlot_1], [property_1]].  An entry in one property to many taxlots
        might look like [[propert_1], [taxlot_1, taxlot_2, taxlot_3]], etc...
    :param case: string, description of the case being created
    """

    # Simplest case is A which is 1-1 which means each entry in pairs_taxlots_and_properties
    # will look like [[taxlot_1], [property_1]].  An entry in one property to many taxlots
    # might look like [[propert_1], [taxlot_1, taxlot_2, taxlot_3]], etc...
    for year in years:
        print('Creating additional year for case {c}:\t{y}'.format(c=case, y=year))
        cycle = get_cycle(org, year)

        update_taxlot_f = lambda x: update_taxlot_year(x, year)
        update_property_f = lambda x: update_property_year(x, year)

        for idx, [taxlots, properties] in enumerate(pairs_taxlots_and_properties):
            taxlots = list(map(update_taxlot_f, taxlots))
            properties = list(map(update_property_f, properties))
            print('Creating {i}'.format(i=idx))
            taxlots, properties = create_cases_with_multi_records_per_cycle(
                org, cycle, taxlots, properties, number_records_per_cycle_per_state
            )


def create_additional_years_D(org, years, tuples_taxlots_properties_campus, number_records_per_cycle_per_state=1):
    """
    Creates additional years of records from existing SampleDataRecords for case D.
    :param org: Organization, the org that will own the new records
    :param years: list of ints.  The years to create the new records for
    :param tuples_taxlots_properties_campus: list of tuples of
        [lists of SampleDataRecords, list of SampleDataRecords, SampleDataRecord]
        First item in the tuple is a list of SampleDataRecords with taxlot data, second
        is a list of SampleDataRecords with property data, third is a single SampleDataRecord
        with property data which will be used as the campus.  Currently expects exactly 3
        taxlots and 5 properties.  Will error with less and unknown behavior with more.
    """
    for year in years:
        print("Creating additional year for case D:\t{y}".format(y=year))
        cycle = get_cycle(org, year)

        update_taxlot_f = lambda x: update_taxlot_year(x, year)
        update_property_f = lambda x: update_property_year(x, year)

        for i in range(number_records_per_cycle_per_state):
            for idx, [taxlots, properties, campus] in enumerate(tuples_taxlots_properties_campus):
                taxlots = list(map(update_taxlot_f, taxlots))
                properties = list(map(update_property_f, properties))
                campus = update_property_f(campus)
                print("Creating {i}".format(i=idx))
                _create_case_D(org, cycle, taxlots, properties, campus)


def create_sample_data(years, a_ct=0, b_ct=0, c_ct=0, d_ct=0, number_records_per_cycle_per_state=1):
    """
    Creates sample data for the specified years and number of cases
    :param years: list of ints, the years to create the sample records for
    :param a_ct: int, the number of A cases to create.
    :param b_ct: int, the number of B cases to create.
    :param c_ct: int, the number of C cases to create.
    :param d_ct: int, the number of D cases to create.
    """
    year = years[0]
    extra_years = years[1:] if len(years) > 1 else None
    org, _ = Organization.objects.get_or_create(name="SampleDataDemo_caseALL")
    cycle = get_cycle(org, year)
    year_ending = datetime.datetime(year, 1, 1)

    taxlot_extra_data_factory = FakeTaxLotExtraDataFactory()
    taxlot_factory = CreateSampleDataFakeTaxLotFactory(taxlot_extra_data_factory)
    property_extra_data_factory = FakePropertyStateExtraDataFactory()
    property_factory = CreateSampleDataFakePropertyStateFactory(
        org, year_ending, "Case A-1: 1 Property, 1 Tax Lot", property_extra_data_factory
    )

    pairs_taxlots_and_properties_A = []
    pairs_taxlots_and_properties_B = []
    pairs_taxlots_and_properties_C = []
    tuples_taxlots_properties_campus_D = []

    for i in range(a_ct):
        print("Creating Case A {i}".format(i=i))
        pairs_taxlots_and_properties_A.append(
            create_case_A(org, cycle, taxlot_factory, property_factory,
                          number_records_per_cycle_per_state))

    create_additional_years(org, extra_years, pairs_taxlots_and_properties_A, "A",
                            number_records_per_cycle_per_state)

    for i in range(b_ct):
        print("Creating Case B {i}".format(i=i))
        property_factory.case_description = "Case B-1: Multiple (3) Properties, 1 Tax Lot"
        pairs_taxlots_and_properties_B.append(
            create_case_B(org, cycle, taxlot_factory, property_factory, number_records_per_cycle_per_state)
        )

    create_additional_years(org, extra_years, pairs_taxlots_and_properties_B, "B", number_records_per_cycle_per_state)

    for i in range(c_ct):
        print("Creating Case C {i}".format(i=i))
        property_factory.case_description = "Case C: 1 Property, Multiple (3) Tax Lots"
        pairs_taxlots_and_properties_C.append(
            create_case_C(org, cycle, taxlot_factory, property_factory, number_records_per_cycle_per_state))

    create_additional_years(org, extra_years, pairs_taxlots_and_properties_C, "C", number_records_per_cycle_per_state)

    for i in range(d_ct):
        print("Creating Case D {i}".format(i=i))
        property_factory.case_description = "Case D: Campus with Multiple associated buildings"
        tuples_taxlots_properties_campus_D.append(
            create_case_D(org, cycle, taxlot_factory, property_factory, number_records_per_cycle_per_state))

    create_additional_years_D(org, extra_years, tuples_taxlots_properties_campus_D, number_records_per_cycle_per_state)


class Command(BaseCommand):
    """
    Management command for creating arbitrary numbers of each of the four sample cases
    in a user-specified list of years.
    """

    def add_arguments(self, parser):
        parser.add_argument('--A', dest='case_A_count', default=10,
                            help='Number of A (1 building, 1 taxlot) cases.')
        parser.add_argument('--B', dest='case_B_count', default=1,
                            help='Number of B (many buildings, 1 taxlot) cases.')
        parser.add_argument('--C', dest='case_C_count', default=1,
                            help='Number of C (1 building, many taxlots) cases.')
        parser.add_argument('--D', dest='case_D_count', default=1,
                            help='Number of D (1 campus, many buildings, many taxlots) cases.')
        parser.add_argument('--Y', dest='years', default='2015,2016',
                            help='comma separated list of years to create data for.')
        parser.add_argument('--audit-depth', dest='number_records_per_cycle_per_state', default=1,
                            help='number of records to create within each year for audit history.  Same as the number of records created per state per cycle.')
        return

    def handle(self, *args, **options):
        years = options.get('years', '2015')
        years = years.split(',')
        years = [int(x) for x in years]
        create_sample_data(
            years,
            int(options.get('case_A_count', 0)),
            int(options.get('case_B_count', 0)),
            int(options.get('case_C_count', 0)),
            int(options.get('case_D_count', 0)),
            int(options.get('number_records_per_cycle_per_state', 0))
        )
        return
