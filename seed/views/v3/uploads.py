import csv
import datetime
import logging
import os

from drf_yasg.utils import swagger_auto_schema, no_body
from past.builtins import basestring
import pint
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import xlrd

from seed.data_importer.models import (
    ImportFile,
    ImportRecord
)
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    SEED_DATA_SOURCES,
    PORTFOLIO_RAW)
from seed.utils.api import api_endpoint_class, OrgMixin
from seed.utils.api_schema import AutoSchemaHelper

_log = logging.getLogger(__name__)


def get_upload_path(filename):
    path = os.path.join(settings.MEDIA_ROOT, "uploads", filename)

    # Get a unique filename using the get_available_name method in FileSystemStorage
    s = FileSystemStorage()
    return s.get_available_name(path)


class UploadViewSet(viewsets.ViewSet, OrgMixin):
    """
    Endpoint to upload data files to, if uploading to local file storage.
    Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``

    Returns::

        {
            'import_record': True,
            'import_file_id': The ID of the newly-uploaded ImportFile
        }

    """
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        request_body=no_body,
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.upload_file_field(
                name='file',
                required=True,
                description='File to Upload'
            ),
            AutoSchemaHelper.form_integer_field(
                name='import_record',
                required=True,
                description='the dataset ID you want to associate this file with.'
            ),
            AutoSchemaHelper.form_string_field(
                name='source_type',
                required=True,
                description='the type of file (e.g. "Portfolio Raw" or "Assessed Raw")'
            ),
            AutoSchemaHelper.form_string_field(
                name='source_program_version',
                required=False,
                description='the version of the file as related to the source_type'
            ),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def create(self, request):
        """
        Upload a new file to an import_record. This is a multipart/form upload.
        """

        if len(request.FILES) == 0:
            return JsonResponse({
                'success': False,
                'message': "Must pass file in as a Multipart/Form post"
            })

        # Fineuploader requires the field to be qqfile it appears... so why not support both? ugh.
        if 'qqfile' in request.data:
            the_file = request.data['qqfile']
        else:
            the_file = request.data['file']
        filename = the_file.name
        path = get_upload_path(filename)

        # verify the directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        extension = the_file.name.split(".")[-1]
        if extension == "xlsx" or extension == "xls":
            workbook = xlrd.open_workbook(file_contents=the_file.read())
            all_sheets_empty = True
            for sheet_name in workbook.sheet_names():
                try:
                    sheet = workbook.sheet_by_name(sheet_name)
                    if sheet.nrows > 0:
                        all_sheets_empty = False
                        break
                except xlrd.biffh.XLRDError:
                    pass

            if all_sheets_empty:
                return JsonResponse({
                    'success': False,
                    'message': "Import %s was empty" % the_file.name
                })

        # save the file
        with open(path, 'wb+') as temp_file:
            for chunk in the_file.chunks():
                temp_file.write(chunk)
        org_id = self.get_organization(request)
        import_record_pk = request.POST.get('import_record', request.GET.get('import_record'))
        try:
            record = ImportRecord.objects.get(
                pk=import_record_pk,
                super_organization_id=org_id
            )
        except ImportRecord.DoesNotExist:
            # clean up the uploaded file
            os.unlink(path)
            return JsonResponse({
                'success': False,
                'message': "Import Record %s not found" % import_record_pk
            })

        source_type = request.POST.get('source_type', request.GET.get('source_type'))

        # Add Program & Version fields (empty string if not given)
        kw_fields = {field: request.POST.get(field, request.GET.get(field, ''))
                     for field in ['source_program', 'source_program_version']}

        f = ImportFile.objects.create(import_record=record,
                                      uploaded_filename=filename,
                                      file=path,
                                      source_type=source_type,
                                      **kw_fields)

        return JsonResponse({'success': True, "import_file_id": f.pk})

    @staticmethod
    def _get_pint_var_from_pm_value_object(pm_value):
        units = pint.UnitRegistry()
        if '@uom' in pm_value and '#text' in pm_value:
            # this is the correct expected path for unit-based attributes
            string_value = pm_value['#text']
            try:
                float_value = float(string_value)
            except ValueError:
                return {'success': False,
                        'message': 'Could not cast value to float: \"%s\"' % string_value}
            original_unit_string = pm_value['@uom']
            if original_unit_string == 'kBtu':
                pint_val = float_value * units.kBTU
            elif original_unit_string == 'kBtu/ft²':
                pint_val = float_value * units.kBTU / units.sq_ft
            elif original_unit_string == 'Metric Tons CO2e':
                pint_val = float_value * units.metric_ton
            elif original_unit_string == 'kgCO2e/ft²':
                pint_val = float_value * units.kilogram / units.sq_ft
            else:
                return {'success': False,
                        'message': 'Unsupported units string: \"%s\"' % original_unit_string}
            return {'success': True, 'pint_value': pint_val}

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field()
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'import_record_id': 'integer',
                'properties': [{
                    'address_1': 'string',
                    'city': 'string',
                    'state_province': 'string',
                    'postal_code': 'string',
                    'county': 'string',
                    'country': 'string',
                    'property_name': 'string',
                    'property_id': 'integer',
                    'year_built': 'integer',
                }],
            },
            required=['import_record_id', 'properties'],
            description='An object containing meta data for a property'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['POST'], parser_classes=(JSONParser,))
    def create_from_pm_import(self, request):
        """
        Create an import_record from a PM import request.
        TODO: The properties key here is going to be an enormous amount of XML data at times, need to change this
        This allows the PM import workflow to be treated essentially the same as a standard file upload
        The process comprises the following steps:

        * Get a unique file name for this portfolio manager import
        """

        doing_pint = False

        if 'properties' not in request.data:
            return JsonResponse({
                'success': False,
                'message': "Must pass properties in the request body."
            }, status=status.HTTP_400_BAD_REQUEST)

        # base file name (will be appended with a random string to ensure uniqueness if multiple on the same day)
        today_date = datetime.datetime.today().strftime('%Y-%m-%d')
        file_name = "pm_import_%s.csv" % today_date

        # create a folder to keep pm_import files
        path = os.path.join(settings.MEDIA_ROOT, "uploads", "pm_imports", file_name)

        # Get a unique filename using the get_available_name method in FileSystemStorage
        s = FileSystemStorage()
        path = s.get_available_name(path)

        # verify the directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        # This list should cover the core keys coming from PM, ensuring that they map easily
        # We will also look for keys not in this list and just map them to themselves
        # pm_key_to_column_heading_map = {
        #     'address_1': 'Address',
        #     'city': 'City',
        #     'state_province': 'State',
        #     'postal_code': 'Zip',
        #     'county': 'County',
        #     'country': 'Country',
        #     'property_name': 'Property Name',
        #     'property_id': 'Property ID',
        #     'year_built': 'Year Built',
        # }
        # so now it looks like we *don't* need to override these, but instead we should leave all the headers as-is
        # I'm going to leave this in here for right now, but if it turns out that we don't need it after testing,
        # then I'll remove it entirely
        pm_key_to_column_heading_map = {}

        # We will also create a list of values that are used in PM export to indicate a value wasn't available
        # When we import them into SEED here we will be sure to not write those values
        pm_flagged_bad_string_values = [
            'Not Available',
            'Unable to Check (not enough data)',
            'No Current Year Ending Date',
        ]

        # We will make a pass through the first property to get the list of unexpected keys
        for pm_property in request.data['properties']:
            for pm_key_name, _ in pm_property.items():
                if pm_key_name not in pm_key_to_column_heading_map:
                    pm_key_to_column_heading_map[pm_key_name] = pm_key_name
            break

        # Create the header row of the csv file first
        rows = []
        header_row = []
        for _, csv_header in pm_key_to_column_heading_map.items():
            header_row.append(csv_header)
        rows.append(header_row)

        num_properties = len(request.data['properties'])
        property_num = 0
        last_time = datetime.datetime.now()

        _log.debug("About to try to import %s properties from ESPM" % num_properties)
        _log.debug("Starting at %s" % last_time)

        # Create a single row for each building
        for pm_property in request.data['properties']:

            # report some helpful info every 20 properties
            property_num += 1
            if property_num % 20 == 0:
                new_time = datetime.datetime.now()
                _log.debug("On property number %s; current time: %s" % (property_num, new_time))

            this_row = []

            # Loop through all known PM variables
            for pm_variable, _ in pm_key_to_column_heading_map.items():

                # Initialize this to False for each pm_variable we will search through
                added = False

                # Check if this PM export has this variable in it
                if pm_variable in pm_property:

                    # If so, create a convenience variable to store it
                    this_pm_variable = pm_property[pm_variable]

                    # Next we need to check type.  If it is a string, we will add it here to avoid parsing numerics
                    # However, we need to be sure to not add the flagged bad strings.
                    # However, a flagged value *could* be a value property name, and we would want to allow that
                    if isinstance(this_pm_variable, basestring):
                        if pm_variable == 'property_name':
                            this_row.append(this_pm_variable)
                            added = True
                        elif pm_variable == 'property_notes':
                            sanitized_string = this_pm_variable.replace('\n', ' ')
                            this_row.append(sanitized_string)
                            added = True
                        elif this_pm_variable not in pm_flagged_bad_string_values:
                            this_row.append(this_pm_variable)
                            added = True

                    # If it isn't a string, it should be a dictionary, storing numeric data and units, etc.
                    else:
                        # As long as it is a valid dictionary, try to get a meaningful value out of it
                        if this_pm_variable and '#text' in this_pm_variable and this_pm_variable['#text'] != 'Not Available':
                            # Coerce the value into a proper set of Pint units for us
                            if doing_pint:
                                new_var = UploadViewSet._get_pint_var_from_pm_value_object(this_pm_variable)
                                if new_var['success']:
                                    pint_value = new_var['pint_value']
                                    this_row.append(pint_value.magnitude)
                                    added = True
                                    # TODO: What to do with the pint_value.units here?
                            else:
                                this_row.append(float(this_pm_variable['#text']))
                                added = True

                # And finally, if we haven't set the added flag, give the csv column a blank value
                if not added:
                    this_row.append('')

            # Then add this property row of data
            rows.append(this_row)

        # Then write the actual data out as csv
        with open(path, 'w', encoding='utf-8') as csv_file:
            pm_csv_writer = csv.writer(csv_file)
            for row_num, row in enumerate(rows):
                pm_csv_writer.writerow(row)

        # Look up the import record (data set)
        org_id = request.data['organization_id']
        import_record_pk = request.data['import_record_id']
        try:
            record = ImportRecord.objects.get(
                pk=import_record_pk,
                super_organization_id=org_id
            )
        except ImportRecord.DoesNotExist:
            # clean up the uploaded file
            os.unlink(path)
            return JsonResponse({
                'success': False,
                'message': "Import Record %s not found" % import_record_pk
            })

        # Create a new import file object in the database
        f = ImportFile.objects.create(import_record=record,
                                      uploaded_filename=file_name,
                                      file=path,
                                      source_type=SEED_DATA_SOURCES[PORTFOLIO_RAW],
                                      **{'source_program': 'PortfolioManager',
                                         'source_program_version': '1.0'})

        # Return the newly created import file ID
        return JsonResponse({'success': True, 'import_file_id': f.pk})
