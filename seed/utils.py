"""
:copyright: (c) 2014 Building Energy Inc
"""
# system imports
import copy
import datetime
import re
from importlib import import_module

from superperms.orgs.models import (
    Organization as SuperOrganization,
    OrganizationUser as SuperOrganizationUser
)
from seed import models
from seed.models import (
    ASSESSED_RAW, BuildingSnapshot, ProjectBuilding, StatusLabel, Project
)
from . import search
from django.conf import settings

EXCLUDE_FIELDS = [
    'best_guess_canonical_building',
    'best_guess_confidence',
    'canonical_building',
    'canonical_for_ds',
    'children',
    'confidence',
    'created',
    'extra_data',
    'id',
    'import_file',
    'last_modified_by',
    'match_type',
    'modified',
    'parents',
    'pk',
    'seed_org',
    'source_type',
    'super_organization',
]

META_FIELDS = [
    'best_guess_canonical_building',
    'best_guess_confidence',
    'canonical_for_ds',
    'confidence',
    'match_type',
    'source_type',
]


def create_organization(user, org_name='', *args, **kwargs):
    """Helper script to create a user/org relationship from scratch.

    :param user: user inst.
    :param org_name: str, name of Organization we'd like to create.
    :param (optional) kwargs: 'role', int; 'status', str.

    """
    org = SuperOrganization.objects.create(
        name=org_name
    )
    org_user, user_added = SuperOrganizationUser.objects.get_or_create(
        user=user, organization=org
    )

    return org, org_user, user_added


def get_mappable_columns(exclude_fields=None):
    """Get a list of all the columns we're able to map to."""
    return get_mappable_types(exclude_fields).keys()


def get_mappable_types(exclude_fields=None):
    """Like get_mappable_columns, but with type information."""
    if not exclude_fields:
        exclude_fields = EXCLUDE_FIELDS

    results = {}
    for f in BuildingSnapshot._meta.fields:
        if f.name not in exclude_fields and '_source' not in f.name:
            results[f.name] = f.get_internal_type()

    # Normalize the types for when we communicate with JS.
    for field in results:
        results[field] = results[field].lower().replace(
            'field', ''
        ).replace(
            'integer', 'float'
        ).replace(
            'time', ''
        ).replace(
            'text', ''
        ).replace(
            'char', ''
        )

    return results


def get_buildings_for_user(user):
    building_snapshots = BuildingSnapshot.objects.filter(
        super_organization__in=user.orgs.all()
    )

    buildings = []
    for b in building_snapshots[:10]:
        b_temp = copy.copy(b.__dict__)
        del(b_temp['_state'])
        buildings.append(b_temp)

    return buildings


def get_buildings_for_user_count(user):
    """returns the number of buildings in a user's orgs"""
    building_snapshots = BuildingSnapshot.objects.filter(
        super_organization__in=user.orgs.all(),
        canonicalbuilding__active=True,
    ).distinct('pk')

    return building_snapshots.count()


def get_search_query(user, params):
    other_search_params = params.get('filter_params', {})
    q = other_search_params.get('q', '')
    order_by = params.get('order_by', 'pk')
    sort_reverse = params.get('sort_reverse', False)

    if order_by:
        if sort_reverse:
            order_by = "-%s" % order_by
        building_snapshots = BuildingSnapshot.objects.order_by(
            order_by
        ).filter(
            super_organization__in=user.orgs.all(),
            canonicalbuilding__active=True,
        )
    else:
        building_snapshots = BuildingSnapshot.objects.filter(
            super_organization__in=user.orgs.all(),
            canonicalbuilding__active=True,
        )

    buildings_queryset = search.search_buildings(
        q, queryset=building_snapshots)
    buildings_queryset = search.filter_other_params(
        buildings_queryset, other_search_params)

    return buildings_queryset


def get_columns(is_project):
    """gets default columns, to be overridden in future

        title: HTML presented title of column
        sort_column: semantic name used by js and for searching DB
        class: HTML CSS class for row td elements
        title_class: HTML CSS class for column td elements
        type: 'string' or 'number', if number will get min and max input fields
        min, max: the django filter key e.g. gross_floor_area__gte
        field_type: assessor, pm, or compliance (currently not used)
        sortable: determines if the column is sortable
        checked: initial state of "edit columns" modal
        static: True if option can be toggle (ID is false because it is
            always needed to link to the building detail page)
        link: signifies that the cell's data should link to a building detail
            page

    """

    assessor_fields = ASSESSOR_FIELDS[:]

    if is_project:
        assessor_fields.insert(1, {
            "title": "Status",
            "sort_column": "project_building_snapshots__status_label__name",
            "class": "",
            "title_class": "",
            "type": "string",
            "field_type": "assessor",
            "sortable": True,
            "checked": True,
            "static": True
        })
    columns = {
        'fields': assessor_fields,
    }

    return columns


def get_compliance_projects(building, organization):
    """return an JSON friendly list of the building's compliance projects

    :param building: the BuildingSnapshot inst.
    :param organization: the Organization inst.
    :returns: list of compliance projects
    """
    compliance_projects = []
    for p in building.project_set.filter(
            compliance__isnull=False,
            super_organization=organization
    ).distinct():
        project_dict = p.__dict__.copy()
        project_dict['is_compliance'] = p.has_compliance
        c = p.get_compliance()
        project_dict['compliance_type'] = c.compliance_type
        project_dict['end_date'] = c.end_date.strftime("%m/%d/%Y")
        project_dict['deadline_date'] = c.deadline_date.strftime("%m/%d/%Y")

        del(project_dict['_state'])
        del(project_dict['modified'])
        del(project_dict['created'])

        pb = ProjectBuilding.objects.get(project=p, building_snapshot=building)
        if pb.approved_date:
            approved_date = pb.approved_date.strftime("%m/%d/%Y")
        else:
            approved_date = None
        project_dict['building'] = {
            'compliant': pb.compliant,
            'approver': pb.approver.email if pb.approver else None,
            'approved_date': approved_date,
        }
        if pb.status_label:
            label = {
                'name': pb.status_label.name,
                'color': pb.status_label.color,
                'id': pb.status_label.pk,
            }
            project_dict['building']['label'] = label
        compliance_projects.append(project_dict)

    return compliance_projects


def get_labels(user):
    """return an JSON friendly list of labels for a user in an
       owner__organization__users
       lables = [
        {
            'name': name,
            'color': color,
            'id': label_id
        },
        ...
       ]

    """
    status_labels = StatusLabel.objects.filter(
        super_organization__in=user.orgs.all()
    )
    labels = []
    for label in status_labels:
        labels.append({
            'name': label.name,
            'color': label.color,
            'id': label.pk,
        })
    return labels


def update_buildings_with_labels(buildings, project_id):
    """update the buildings in a buildings list with their StatusLabel"""
    for b in buildings:
        pb = ProjectBuilding.objects.get(
            building_snapshot__pk=b['pk'],
            project__pk=project_id
        )
        if pb.status_label:
            b['project_building_snapshots__status_label__name'] = {
                'name': pb.status_label.name,
                'color': pb.status_label.color,
                'id': pb.status_label.pk,
            }
    return buildings


def convert_to_js_timestamp(timestamp):
    """converts a django/python datetime object to milliseconds since epoch"""
    if timestamp:
        return int(timestamp.strftime("%s")) * 1000
    return None


def apply_label(project_slug, buildings, select_all, label, search_params,
                user):
    """adds or updates a label for a ProjectBuilding related to a
       project and building in the buildings list of source_facility_ids

       :param project_slug: str, a slug to get a Project inst.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we get all buildings or just the ones in the list
       :param label: dict, dict of a info to get a StatusLabel inst., if label
       if an empty dict, apply_label will remove the label
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)

    """
    if 'id' in label:
        label = StatusLabel.objects.get(pk=label['id'])
    else:
        label = None

    if select_all:
        # get all the buildings for a project minus unselected ones
        qs = get_search_query(user, search_params)
        pb_qs = ProjectBuilding.objects.filter(
            building_snapshot__in=qs,
            project__slug=project_slug
        ).exclude(
            building_snapshot__pk__in=buildings
        )
    else:
        # just add selected buildings
        pb_qs = ProjectBuilding.objects.filter(
            building_snapshot__pk__in=buildings,
            project__slug=project_slug,
        )
    pb_qs.update(
        status_label=label
    )


def transfer_buildings(source_project_slug, target_project_slug, buildings,
                       select_all, search_params, user, copy_flag=False):
    """copies or moves buildings from one project to another

       :param source_project_slug: str, a slug to get a Project inst.
       :param target_project_slug: str, a slug to get a Project inst.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset
       and to update the projects' "last changed" and "last changed by"
       :copy_flag: bool, True - copy buildings, False - move buildings

    """
    target_project = Project.objects.get(slug=target_project_slug)
    source_project = Project.objects.get(slug=source_project_slug)

    # update source and target project info
    target_project.last_modified_by = user
    source_project.last_modified_by = user
    target_project.save()
    source_project.save()

    if copy_flag:
        copy_buildings(source_project, target_project, buildings,
                       select_all, search_params, user)
    else:
        move_buildings(source_project, target_project, buildings,
                       select_all, search_params, user)


def copy_buildings(source_project, target_project, buildings,
                   select_all, search_params, user):
    """copies buildings from source project to target project

       :param source_project_slug: str, a slug to get a Project inst.
       :param target_project_slug: str, a slug to get a Project inst.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset

    """
    delete_matching_buildings(
        target_project, buildings, select_all, search_params, user
    )
    pb_queryset = get_transfer_buildings(
        source_project, target_project, buildings, select_all, search_params,
        user
    )
    pbs = []
    for b in pb_queryset:
            # setting pk to None will create a copy the django instance
            b.pk = None
            b.project = target_project
            pbs.append(b)

    ProjectBuilding.objects.bulk_create(pbs)


def move_buildings(source_project, target_project, buildings,
                   select_all, search_params, user):
    """moves buildings from source project to target project

       :param source_project_slug: str, a slug to get a Project inst.
       :param target_project_slug: str, a slug to get a Project inst.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset

    """
    delete_matching_buildings(
        target_project, buildings, select_all, search_params, user
    )
    pb_queryset = get_transfer_buildings(
        source_project, target_project, buildings, select_all, search_params,
        user
    )
    # move buildings from source to target
    pb_queryset.update(project=target_project)


def delete_matching_buildings(project, buildings,
                              select_all, search_params, user):
    """deletes buildings in a project that match search search params

       :param project_slug: str, a slug to get a Project inst.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset

    """
    if select_all:
        # get all the buildings for a project minus unselected ones
        qs = get_search_query(user, search_params)
        ProjectBuilding.objects.filter(
            building_snapshot__in=qs,
            project=project
        ).exclude(building_snapshot__pk__in=buildings).delete()
    else:
        ProjectBuilding.objects.filter(
            building_snapshot__pk__in=buildings,
            project=project
        ).delete()


def get_transfer_buildings(source_project, target_project, buildings,
                           select_all, search_params, user):
    """generates move or copy buildings queryset

       :param source_project_slug: str, a slug to get a Project inst.
       :param target_project_slug: str, a slug to get a Project inst.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset

       :rtype Queryset: a django queryset of buildings to move or copy

    """
    if select_all:
        # get all the buildings for a project minus unselected ones
        qs = get_search_query(user, search_params)
        pb_queryset = ProjectBuilding.objects.filter(
            building_snapshot__in=qs,
            project=source_project
        ).exclude(building_snapshot__pk__in=buildings)
    else:
        pb_queryset = ProjectBuilding.objects.filter(
            building_snapshot__pk__in=buildings,
            project=source_project
        )
    return pb_queryset


def serialize_building_snapshot(b, pm_cb, building):
    """returns a dict that's safe to JSON serialize"""
    b_as_dict = b.__dict__.copy()
    for key, val in b_as_dict.items():
        if type(val) == datetime.datetime or type(val) == datetime.date:
            b_as_dict[key] = convert_to_js_timestamp(val)
    del(b_as_dict['_state'])
    # check if they're matched
    if b.canonical_building == pm_cb:
        b_as_dict['matched'] = True
    else:
        b_as_dict['matched'] = False
    if '_canonical_building_cache' in b_as_dict:
        del(b_as_dict['_canonical_building_cache'])
    return b_as_dict


ASSESSOR_FIELDS = [
    {
        "title": "PM Property ID",
        "sort_column": "pm_property_id",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "link",
        "field_type": "building_information",
        "sortable": True,
        "checked": False,
        "static": False,
        "link": True
    },
    {
        "title": "Tax Lot ID",
        "sort_column": "tax_lot_id",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "link",
        "field_type": "building_information",
        "sortable": True,
        "checked": False,
        "static": False,
        "link": True
    },
    {
        "title": "Custom ID 1",
        "sort_column": "custom_id_1",
        "class": "is_aligned_right whitespace",
        "title_class": "",
        "type": "link",
        "field_type": "building_information",
        "sortable": True,
        "checked": False,
        "static": False,
        "link": True
    },
    {
        "title": "Property Name",
        "sort_column": "property_name",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Address Line 1",
        "sort_column": "address_line_1",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Address Line 2",
        "sort_column": "address_line_2",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "County/District/Ward/Borough",
        "sort_column": "district",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Lot Number",
        "sort_column": "lot_number",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Block Number",
        "sort_column": "block_number",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "City",
        "sort_column": "city",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "State Province",
        "sort_column": "state_province",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Postal Code",
        "sort_column": "postal_code",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Year Built",
        "sort_column": "year_built",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "number",
        "min": "year_built__gte",
        "max": "year_built__lte",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Use Description",
        "sort_column": "use_description",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Building Count",
        "sort_column": "building_count",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "number",
        "min": "building_count__gte",
        "max": "building_count__lte",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Property Notes",
        "sort_column": "property_notes",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Recent Sale Date",
        "sort_column": "recent_sale_date",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "recent_sale_date__gte",
        "max": "recent_sale_date__lte",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Owner",
        "sort_column": "owner",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Owner Address",
        "sort_column": "owner_address",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Owner City",
        "sort_column": "owner_city_state",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Owner Postal Code",
        "sort_column": "owner_postal_code",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Owner Email",
        "sort_column": "owner_email",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Owner Telephone",
        "sort_column": "owner_telephone",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Gross Floor Area",
        "sort_column": "gross_floor_area",
        "subtitle": u"ft" + u"\u00B2",
        "class": "is_aligned_right",
        "type": "floor_area",
        "min": "gross_floor_area__gte",
        "max": "gross_floor_area__lte",
        "field_type": "assessor",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Energy Star Score",
        "sort_column": "energy_score",
        "class": "is_aligned_right",
        "type": "number",
        "min": "energy_score__gte",
        "max": "energy_score__lte",
        "field_type": "pm",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Site EUI",
        "sort_column": "site_eui",
        "class": "is_aligned_right",
        "type": "number",
        "min": "site_eui__gte",
        "max": "site_eui__lte",
        "field_type": "pm",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Generation Date",
        "sort_column": "generation_date",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "generation_date__gte",
        "max": "generation_date__lte",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Release Date",
        "sort_column": "release_date",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "release_date__gte",
        "max": "release_date__lte",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Year Ending",
        "sort_column": "year_ending",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "year_ending__gte",
        "max": "year_ending__lte",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Creation Date",
        "sort_column": "created",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "created__gte",
        "max": "created__lte",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    },
    {
        "title": "Modified Date",
        "sort_column": "modified",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "sortable": True,
        "checked": False
    }
]

ASSESSOR_FIELDS_BY_COLUMN = {field['sort_column']: field
                             for field in ASSESSOR_FIELDS}


def get_source_type(import_file, source_type=''):
    """Used for converting ImportFile source_type into an int."""
    source_type_str = getattr(import_file, 'source_type', '') or ''
    source_type_str = source_type or source_type_str
    source_type_str = source_type_str.upper().replace(' ', '_')

    return getattr(models, source_type_str, ASSESSED_RAW)


def get_api_endpoints():
    """
    Examines all views and returns those with is_api_endpoint set
    to true (done by the @api_endpoint decorator).

    TODO: this isn't particularly expensive now, but if the number of urls
    grows a lot, it may be worth caching this somewhere.
    """
    urlconf = import_module(settings.ROOT_URLCONF)
    urllist = urlconf.urlpatterns
    api_endpoints = {}
    for (url, callback) in get_all_urls(urllist):
        if getattr(callback, 'is_api_endpoint', False):
            clean_url = clean_api_regex(url)
            api_endpoints[clean_url] = callback
    return api_endpoints


def format_api_docstring(docstring):
    """
    Cleans up a python method docstring for human consumption.
    """
    if not isinstance(docstring, basestring):
        return "INVALID DOCSTRING"
    whitespace_regex = '\s+'
    ret = re.sub(whitespace_regex, ' ', docstring)
    ret = ret.strip()
    return ret


def clean_api_regex(url):
    """
    Given a django-style url regex pattern, strip it down to a human-readable
    url.

    TODO: If pks ever appear in the url, this will need to account for that.
    """
    url = url.replace('^', '')
    url = url.replace('$', '')
    if not url.startswith('/'):
        url = '/' + url
    return url


def get_all_urls(urllist, prefix=''):
    """
    Recursive generator that traverses entire tree of urls, starting with
    urllist, yielding a tuple of (url_pattern, view_function) for each
    one.
    """
    for entry in urllist:
        if hasattr(entry, 'url_patterns'):
            for url in get_all_urls(entry.url_patterns,
                                    prefix + entry.regex.pattern):
                yield url
        else:
            yield (prefix + entry.regex.pattern, entry.callback)
