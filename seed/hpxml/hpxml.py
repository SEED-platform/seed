# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author noel.merket@nrel.gov
"""

import logging
import os
import functools

from lxml import etree, objectify

_log = logging.getLogger(__name__)

here = os.path.dirname(os.path.abspath(__file__))
hpxml_parser = objectify.makeparser(schema=etree.XMLSchema(etree.parse(os.path.join(here, 'schemas', 'HPXML.xsd'))))


class HPXMLError(Exception):
    pass


class HPXML(object):

    NS = 'http://hpxmlonline.com/2014/6'

    HPXML_STRUCT = {
        'address_line_1': {
            'path': 'h:Site/h:Address/h:Address1',
        },
        'address_line_2': {
            'path': 'h:Site/h:Address/h:Address2',
        },
        'city': {
            'path': 'h:Site/h:Address/h:CityMunicipality',
        },
        'state': {
            'path': 'h:Site/h:Address/h:StateCode',
        },
        'postal_code': {
            'path': 'h:Site/h:Address/h:ZipCode',
        },
        'gross_floor_area': {
            'path': 'h:BuildingDetails/h:BuildingSummary/h:BuildingConstruction/h:GrossFloorArea',
            'conv': float
        },
        'year_built': {
            'path': 'h:BuildingDetails/h:BuildingSummary/h:BuildingConstruction/h:YearBuilt',
            'conv': int
        },
        'conditioned_floor_area': {
            'path': 'h:BuildingDetails/h:BuildingSummary/h:BuildingConstruction/h:ConditionedFloorArea',
            'conv': float
        },
        'occupied_floor_area': {
            'path': 'h:BuildingDetails/h:BuildingSummary/h:BuildingConstruction/h:FinishedFloorArea',
            'conv': float
        },
        'energy_score': {
            'path': 'h:BuildingDetails/h:BuildingSummary/h:BuildingConstruction/h:EnergyScore/h:Score',
            'conv': int
        }
    }

    def __init__(self):
        self.filename = None
        self.tree = None

    @property
    def root(self):
        return self.tree.getroot()

    def xpath(self, xpathexpr, start_from=None, only_one=False, **kw):
        if start_from is None:
            obj = self.root
        else:
            obj = start_from

        resp = obj.xpath(xpathexpr, namespaces={'h': self.NS}, **kw)
        if only_one:
            if not resp:
                return None
            else:
                return resp[0]
        else:
            return resp

    def import_file(self, filename):
        self.filename = filename
        self.tree = objectify.parse(self.filename, parser=hpxml_parser)

        return True

    def export(self, property_state):
        """
        Export HPXML file from an existing HPXML file (from import) merging in the data from property_state
        :param property_state:  object, PropertyState to merge into HPXMLs
        :return: string, as XML
        """
        pass

    def _get_building(self, building_id=None):
        if building_id is not None:
            bldg = self.xpath('//h:Building[h:BuildingID/@id=$bldg_id]', bldg_id=building_id)[0]
        else:
            event_type_precedence = [
                'job completion testing/final inspection',
                'quality assurance/monitoring',
                'audit',
                'construction-period testing/daily test out'
            ]
            bldg = None
            for event_type in event_type_precedence:
                bldgs = self.xpath('//h:Building[h:ProjectStatus/h:EventType=$event_type]', event_type=event_type)
                if len(bldgs) > 0:
                    bldg = bldgs[0]
                    break
            if bldg is None:
                bldg = self.xpath('//h:Building[1]')
        return bldg

    def process(self, building_id=None):
        """
        Process an hpxml file into PropertyState fields
        :param building_id: @id of the building to process, otherwise one will be selected
        :return: [dict, list, list], [results, list of errors, list of messages]
        """
        bldg = self._get_building(building_id)
        building_id = bldg.BuildingID.get('id')
        xpath = functools.partial(self.xpath, start_from=bldg, only_one=True)

        # Building information from HPXML_STRUCT
        res = {}
        for pskey, xml_loc in self.HPXML_STRUCT.items():
            value = xpath(xml_loc['path'])
            if value is None:
                continue
            value = '' if value.text is None else value.text
            if 'conv' in xml_loc:
                value = xml_loc['conv'](value)
            res[pskey] = value

        # Owner information
        owner = self.xpath((
            '//h:Customer/h:CustomerDetails/h:Person'
            '[not(h:IndividualType) or h:IndividualType = "owner-occupant" or h:IndividualType = "owner-non-occupant"]'
        ))
        if len(owner) > 0:
            owner = owner[0]
            owner_name = ' '.join(self.xpath('h:Name/*/text()', start_from=owner))
            if owner_name:
                res['owner'] = owner_name
            try:
                res['owner_email'] = owner.Email.EmailAddress.text
            except AttributeError:
                pass
            try:
                res['owner_telephone'] = owner.Person.Telephone.TelephoneNumber.text
            except AttributeError:
                pass
            res['owner_address'] = ' '.join(self.xpath(
                '|'.join(['h:MailingAddress/h:Address{}/text()'.format(i) for i in (1, 2)]),
                start_from=owner.getparent(),
            ))
            if not res['owner_address']:
                del res['owner_address']
            res['owner_city_state'] = ', '.join(self.xpath(
                '|'.join(['h:MailingAddress/h:{}/text()'.format(i) for i in ('CityMunicipality', 'StateCode')]),
                start_from=owner.getparent(),
            ))
            if not res['owner_city_state']:
                del res['owner_city_state']
            try:
                res['owner_postal_code'] = owner.getparent().MailingAddress.ZipCode.text
            except AttributeError:
                pass

        # Building Certification / Program Certificate
        try:
            res['building_certification'] = self.root.Project.ProjectDetails.ProgramCertificate.text
        except AttributeError:
            pass

        return res



