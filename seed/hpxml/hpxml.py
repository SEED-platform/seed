# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author noel.merket@nrel.gov
"""

import functools
import logging
import os
from builtins import str
from copy import deepcopy
from io import BytesIO

import probablepeople as pp
import usaddress as usadd
from lxml import etree, objectify
from past.builtins import basestring
from quantityfield.units import ureg

_log = logging.getLogger(__name__)

here = os.path.dirname(os.path.abspath(__file__))
hpxml_parser = objectify.makeparser(
    schema=etree.XMLSchema(etree.parse(os.path.join(here, 'schemas', 'HPXML.xsd'))))


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
        if self.tree is None:
            return None
        else:
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
        if not property_state:
            f = BytesIO()
            self.tree.write(f, encoding='utf-8', pretty_print=True, xml_declaration=True)
            return f.getvalue()

        if self.tree is None:
            tree = objectify.parse(os.path.join(here, 'schemas', 'blank.xml'), parser=hpxml_parser)
            root = tree.getroot()
        else:
            root = deepcopy(self.root)

        bldg = self._get_building(property_state.extra_data.get('hpxml_building_id'),
                                  start_from=root)

        for pskey, xml_loc in self.HPXML_STRUCT.items():
            value = getattr(property_state, pskey)
            el = self.xpath(xml_loc['path'], start_from=bldg, only_one=True)
            if pskey == 'energy_score':
                continue
            if value is None and self.tree is None:
                el.getparent().remove(el)
            if value is None or el is None:
                continue

            # set the value to magnitude if it is a quantity
            if isinstance(value, ureg.Quantity):
                value = value.magnitude
            setattr(el.getparent(), el.tag[el.tag.index('}') + 1:],
                    str(value) if not isinstance(value, basestring) else value)

        E = objectify.ElementMaker(annotate=False, namespace=self.NS, nsmap={None: self.NS})

        # Owner Information
        owner = self.xpath((
            '//h:Customer/h:CustomerDetails/h:Person'
            '[not(h:IndividualType) or h:IndividualType = "owner-occupant" or h:IndividualType = "owner-non-occupant"]'
        ), start_from=root)

        if len(owner) > 0:
            owner = owner[0]
        else:
            customer = E.Customer(
                E.CustomerDetails(
                    E.Person(
                        E.SystemIdentifier(id='person1'),
                        E.Name()
                    )
                )
            )
            root.Building.addprevious(customer)
            owner = customer.CustomerDetails.Person

        # Owner Name
        if property_state.owner is not None:
            try:
                owner_name, name_type = pp.tag(property_state.owner, type='person')
            except pp.RepeatedLabelError:
                pass
            else:
                if name_type.lower() == 'person':
                    owner.Name.clear()
                    if 'PrefixMarital' in owner_name or 'PrefixOther' in owner_name:
                        owner.Name.append(
                            E.PrefixName(
                                ' '.join([owner_name.get('Prefix' + x, '') for x in
                                          ('Marital', 'Other')]).strip()
                            )
                        )
                    if 'GivenName' in owner_name:
                        owner.Name.append(E.FirstName(owner_name['GivenName']))
                    elif 'FirstInitial' in owner_name:
                        owner.Name.append(E.FirstName(owner_name['FirstInitial']))
                    else:
                        owner.Name.append(E.FirstName())
                    if 'MiddleName' in owner_name:
                        owner.Name.append(E.MiddleName(owner_name['MiddleName']))
                    elif 'MiddleInitial' in owner_name:
                        owner.Name.append(E.MiddleName(owner_name['MiddleInitial']))
                    if 'Surname' in owner_name:
                        owner.Name.append(E.LastName(owner_name['Surname']))
                    elif 'LastInitial' in owner_name:
                        owner.Name.append(E.LastName(owner_name['LastInitial']))
                    else:
                        owner.Name.append(E.LastName())
                    if 'SuffixGenerational' in owner_name or 'SuffixOther' in owner_name:
                        owner.Name.append(
                            E.SuffixName(
                                ' '.join([owner_name.get('Suffix' + x, '') for x in
                                          ('Generational', 'Other')]).strip()
                            )
                        )

        # Owner Email
        if property_state.owner_email is not None:
            new_email = E.Email(E.EmailAddress(property_state.owner_email),
                                E.PreferredContactMethod(True))
            if hasattr(owner, 'Email'):
                if property_state.owner_email not in owner.Email:
                    owner.append(new_email)
            else:
                owner.append(new_email)

        # Owner Telephone
        if property_state.owner_telephone is not None:
            insert_phone_number = False
            if hasattr(owner, 'Telephone'):
                if property_state.owner_telephone not in owner.Telephone:
                    insert_phone_number = True
            else:
                insert_phone_number = True
            if insert_phone_number:
                new_phone = E.Telephone(
                    E.TelephoneNumber(property_state.owner_telephone),
                    E.PreferredContactMethod(True)
                )
                inserted_phone_number = False
                for elname in ('Email', 'extension'):
                    if hasattr(owner, elname):
                        getattr(owner, elname).addprevious(new_phone)
                        inserted_phone_number = True
                        break
                if not inserted_phone_number:
                    owner.append(new_phone)

        # Owner Address
        try:
            address = owner.getparent().MailingAddress
        except AttributeError:
            owner.getparent().Person[-1].addnext(E.MailingAddress())
            address = owner.getparent().MailingAddress
        address.clear()
        if property_state.owner_address is not None:
            address.append(E.Address1(property_state.owner_address))
        if property_state.owner_city_state is not None:
            city_state, _ = usadd.tag(property_state.owner_city_state)
            address.append(E.CityMunicipality(city_state.get('PlaceName', '')))
            address.append(E.StateCode(city_state.get('StateName', '')))
        if property_state.owner_postal_code is not None:
            address.append(E.ZipCode(property_state.owner_postal_code))

        # Building Certification / Program Certificate
        program_certificate_options = [
            'Home Performance with Energy Star',
            'LEED Certified',
            'LEED Silver',
            'LEED Gold',
            'LEED Platinum',
            'other'
        ]
        if property_state.building_certification is not None:
            try:
                root.Project
            except AttributeError:
                root.Building[-1].addnext(
                    E.Project(
                        E.BuildingID(id=bldg.BuildingID.get('id')),
                        E.ProjectDetails(
                            E.ProjectSystemIdentifiers(id=bldg.BuildingID.get('id'))
                        )
                    )
                )
            new_prog_cert = E.ProgramCertificate(
                property_state.building_certification
                if property_state.building_certification in program_certificate_options
                else 'other'
            )
            try:
                root.Project.ProjectDetails.ProgramCertificate
            except AttributeError:
                for elname in ('YearCertified', 'CertifyingOrganizationURL',
                               'CertifyingOrganization', 'ProgramSponsor',
                               'ContractorSystemIdentifiers', 'ProgramName',
                               'ProjectSystemIdentifiers'):
                    if hasattr(root.Project.ProjectDetails, elname):
                        getattr(root.Project.ProjectDetails, elname).addnext(
                            new_prog_cert
                        )
                        break
            else:
                if property_state.building_certification not in root.Project.ProjectDetails.ProgramCertificate:
                    root.Project.ProjectDetails.ProgramCertificate[-1].addnext(new_prog_cert)

        # Energy Score
        energy_score_type_options = [
            'US DOE Home Energy Score',
            'RESNET HERS'
        ]
        bldg_const = bldg.BuildingDetails.BuildingSummary.BuildingConstruction
        if property_state.energy_score:
            energy_score_type = property_state.extra_data.get('energy_score_type')
            try:
                found_energy_score = False
                for energy_score_el in bldg_const.EnergyScore:
                    if energy_score_type in (energy_score_el.ScoreType,
                                             getattr(energy_score_el, 'OtherScoreType', None)):
                        found_energy_score = True
                        break
                if not found_energy_score:
                    energy_score_el = E.EnergyScore()
                    bldg_const.EnergyScore[-1].addnext(energy_score_el)
            except AttributeError:
                energy_score_el = E.EnergyScore()
                try:
                    bldg_const.extension.addprevious(energy_score_el)
                except AttributeError:
                    bldg_const.append(energy_score_el)
            if energy_score_type in energy_score_type_options:
                energy_score_el.ScoreType = energy_score_type
            else:
                energy_score_el.ScoreType = 'other'
                energy_score_el.OtherScoreType = energy_score_type
            energy_score_el.Score = property_state.energy_score

        # Serialize
        tree = etree.ElementTree(root)
        objectify.deannotate(tree, cleanup_namespaces=True)
        f = BytesIO()
        tree.write(f, encoding='utf-8', pretty_print=True, xml_declaration=True)
        return f.getvalue()

    def _get_building(self, building_id=None, **kw):
        if building_id is not None:
            bldg = self.xpath('//h:Building[h:BuildingID/@id=$bldg_id]', bldg_id=building_id, **kw)[
                0]
        else:
            event_type_precedence = [
                'job completion testing/final inspection',
                'quality assurance/monitoring',
                'audit',
                'construction-period testing/daily test out'
            ]
            bldg = None
            for event_type in event_type_precedence:
                bldgs = self.xpath('//h:Building[h:ProjectStatus/h:EventType=$event_type]',
                                   event_type=event_type, **kw)
                if len(bldgs) > 0:
                    bldg = bldgs[0]
                    break
            if bldg is None:
                bldg = self.xpath('//h:Building[1]', **kw)
        return bldg

    def process(self, building_id=None):
        """
        Process an hpxml file into PropertyState fields
        :param building_id: @id of the building to process, otherwise one will be selected
        :return: [dict, list, list], [results, list of errors, list of messages]
        """
        bldg = self._get_building(building_id)
        res = {
            'hpxml_building_id': bldg.BuildingID.get('id')
        }
        xpath = functools.partial(self.xpath, start_from=bldg, only_one=True)

        # Building information from HPXML_STRUCT
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
                '|'.join(['h:MailingAddress/h:{}/text()'.format(i) for i in
                          ('CityMunicipality', 'StateCode')]),
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

        # Energy Score Type
        try:
            energy_score = bldg.BuildingDetails.BuildingSummary.BuildingConstruction.EnergyScore
        except AttributeError:
            pass
        else:
            score_type = energy_score.ScoreType.text
            if score_type == 'other':
                try:
                    score_type = energy_score.OtherScoreType.text
                except AttributeError:
                    pass
                res['energy_score_type'] = score_type
            else:
                res['energy_score_type'] = score_type

        return res, {'errors': [], 'warnings': []}
