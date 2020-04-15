# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import csv
import json
import os

import geojson
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Parse example geojson data and extract to CSV for a test file'

    def add_arguments(self, parser):
        parser.add_argument('--path',
                            default='~',
                            help='Path to local geojson files for parsing',
                            action='store',
                            dest='path')

    def convert_list_to_wkt(self, geom):
        """
        The structure on the coordinates is list of list of list... so grab the first two levels
        for now until there is a clearer pattern to this.

        :param geom:
        :return:
        """
        if geom['type'] == "Polygon":
            coords = [f"{l[0]} {l[1]}" for l in geom['coordinates'][0]]
            return f"POLYGON (( {', '.join(coords)} ))"
        else:
            raise Exception(f"Unknown type of Geomoetry in GeoJSON of {geom['type']}")

    def handle(self, *args, **options):
        self.stdout.write('Parsing geojson files in %s' % (options['path']), ending='\n')

        # one-to-one
        # taxlot
        #   - 2632.00000000000 / 849W93VG+WGX-38-39-39-38
        #   1 building footprint / ubids
        #       - 13159.00000000000 / 849W93VG+WFQ-25-23-26-22

        # one taxlot to many properties
        # taxlots
        #   - 2664.0000 / 849W93VH+682-63-65-63-70
        #   4 building footprints / ubids
        #       - 9572.00000000000 / 849W93VG+GR7-15-24-15-21
        #       - 12480.00000000000 / 849W93VH+4RJ-17-21-18-19
        #       - 13322.00000000000 / 849W93VH+77C-20-14-22-14
        #       - 13332.00000000000 / 849W93RH+VFV-14-15-15-13

        # many taxlots to one property
        # taxlots
        #   - 241.00000000000 / 849W93RP+W2M-26-27-27-27
        #   - 242.00000000000 / 849W93RM+MQR-23-23-23-23
        #   1 building footprint / ubid
        #       - 12388.00000000000 / 849W93RM+VR8-29-28-29-28

        # property with bridge
        # taxlots
        #   - 2299.00000000000 / 849W93WF+F9G-36-27-38-28
        #   - 2486.00000000000 / 849W93WF+93G-29-27-31-23
        #   1 building footprints
        #       - 10072.00000000000 / 849W93WF+F4C-14-23-17-23

        # property with courtyard (one taxlot - 3 properties)
        # taxlot
        #   - 306.00000000000 / 849W93MH+W8Q-33-30-34-29
        #   footprint:
        #     - 14227.00000000000 / 849W93MH+Q75-12-12-12-10
        #     - 15156.00000000000 / 849W93PH+27J-14-14-14-15
        #     - 15179.00000000000 / 849W93MH+WF6-12-11-11-12 (courtyard building)

        # list of taxlot properties to save out of the file
        taxlot_mapping = {
            'PARCELID': 'Parcel ID',
            'APN': 'Jurisdiction Tax Lot ID',
            'LOTNUM': 'Lot Number',
            'NOOFADDR': 'Number of Addresses',
            'NOOFFLOORS': 'Number of Floors',
            'ASSESSEE': 'Assessee',
            'MAILINGADD': 'Owner Address',
            'MAILINGCIT': 'Owner City and State',
            'MAILINGZIP': 'Owner Postal Code',
            'Concaten_1': 'Address Concatenated',
            'CITY': 'City',
            'STATE': 'State',
            'ZIP': 'Postal Code',
            'UBID': 'ULID',
        }

        property_mapping = {
            'APN': 'Jurisdiction Tax Lot ID',
            'UBID': 'UBID',
        }

        data = [
            {
                'taxlots': [
                    {'id': 2664, },
                ],
                'footprints': [
                    {'id': 9572, },
                    {'id': 12480, },
                    {'id': 13322, },
                    {'id': 13332, },
                ]
            },
            {
                'taxlots': [
                    {'id': 2632, },
                ],
                'footprints': [
                    {'id': 13159, },
                ]
            },
            {
                'taxlots': [
                    {'id': 241, },
                    {'id': 242, }
                ],
                'footprints': [
                    {'id': 12388, },
                ]
            },
            {
                'taxlots': [
                    {'id': 2299, },
                    {'id': 2486, }
                ],
                'footprints': [
                    {'id': 10072, },
                ]
            },
        ]

        # add in empty properties for later use
        for datum in data:
            for taxlot in datum['taxlots']:
                taxlot['properties'] = {}
            for footprint in datum['footprints']:
                footprint['properties'] = {}

        parcels = None
        properties = None
        parcel_filename = '%s/CoveredParcels_GeoJSON.json' % options['path']
        property_filename = '%s/CoveredBuildings_GeoJSON.json' % options['path']
        if os.path.exists(parcel_filename):
            with open(parcel_filename, 'rb') as f:
                parcels = geojson.loads(f.read())

        if os.path.exists(property_filename):
            with open(property_filename, 'rb') as f:
                properties = geojson.loads(f.read())

        for datum in data:
            for taxlot in datum['taxlots']:
                for feature in parcels.features:
                    if int(float(feature.properties['OBJECTID'])) == taxlot['id']:
                        taxlot['properties']['Object ID'] = taxlot['id']
                        for k, v in taxlot_mapping.items():
                            taxlot['properties'][v] = feature.properties[k]
                        # add in the polygons
                        taxlot['properties']['coordinates'] = self.convert_list_to_wkt(
                            feature.geometry)

            for footprint in datum['footprints']:
                for feature in properties.features:
                    if int(float(feature.properties['OBJECTID'])) == footprint['id']:
                        footprint['properties']['Object ID'] = footprint['id']
                        for k, v in property_mapping.items():
                            footprint['properties'][v] = feature.properties[k]
                        # add in the polygons
                        footprint['properties']['coordinates'] = self.convert_list_to_wkt(
                            feature.geometry)

        print(json.dumps(data, indent=2))

        # save the data to CSV files
        with open('seed/tests/data/san-jose-test-taxlots.csv', 'w') as f:
            writer = csv.writer(f)
            # write the header, which are all the mapping fields with taxlot / property appended
            row = []
            row.append('Tax Lot Object ID')
            for value in taxlot_mapping.values():
                row.append(value)
            row.append('Tax Lot Coordinates')
            writer.writerow(row)

            for datum in data:
                for taxlot in datum['taxlots']:
                    row = []
                    row.append(taxlot['properties']['Object ID'])
                    for value in taxlot_mapping.values():
                        row.append(taxlot['properties'][value])
                    row.append(taxlot['properties']['coordinates'])
                    writer.writerow(row)

        # save the data to CSV files
        with open('seed/tests/data/san-jose-test-properties.csv', 'w') as f:
            writer = csv.writer(f)
            # write the header, which are all the mapping fields with taxlot / property appended
            row = []
            row.append('Property Object ID')
            for value in property_mapping.values():
                row.append(value)
            row.append('Property Coordinates')
            writer.writerow(row)

            for datum in data:
                for footprint in datum['footprints']:
                    row = []
                    row.append(footprint['properties']['Object ID'])
                    for value in property_mapping.values():
                        row.append(footprint['properties'][value])
                    row.append(footprint['properties']['coordinates'])
                    writer.writerow(row)
