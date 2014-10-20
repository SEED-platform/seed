"""
:copyright: (c) 2014 Building Energy Inc
"""
import os
import tempfile
import unicodecsv as csv
import xlwt
from django.db.models.fields import FieldDoesNotExist
from django.db.models import Manager
from django.db.models.fields.related import (
    ForeignRelatedObjectsDescriptor,
    ReverseSingleRelatedObjectDescriptor
)


def _make_export_subdirectory(export_id):
    return os.path.join("exports", export_id)


def _make_export_filename(export_id, export_name, export_type):
    return os.path.join(
        _make_export_subdirectory(export_id),
        "%s.%s" % (export_name, export_type)
    )


def _make_object_row(obj, fields):
    """
    Creates an exportable row of data from an object and a list of fields.
    Ignores nones and instances of the Django Manager object, replacing them
    with blank unicode strings.
    """
    row = []
    for field in fields:
        value = _get_field_value(field, obj)
        if isinstance(value, Manager) or value is None:
            row.append(u'')
        else:
            row.append(unicode(value))
    return row


def _get_fields_from_queryset(qs):
    """
    Creates a list of all accessible fields on a model based off of a queryset.
    """
    fields = qs.model._meta.get_all_field_names()
    for field in fields:
        try:
            qs.model._meta.get_field(field)
            yield field
        except FieldDoesNotExist:
            continue


def _get_field_name(field, qs):
    """
    Takes a field name like "building_snapshot__state" and returns the verbose
    field name as set in django, to be used as the header in exported files.
    """
    par = qs.model
    components = field.split("__")
    for component in components[:-1]:  # iterate through the parent models
        par = getattr(par, component)

        # If the component resolves to a Manager or Descriptor,
        # we have to get to the model differently than a standard field
        if isinstance(par, (Manager,
                            ForeignRelatedObjectsDescriptor)):
            par = par.related.model

        # Special case for status_label in project exports, where we want
        # the name from the relation field -- not the field the value comes
        # from.
        elif component == 'status_label':
            components[-1] = component
            par = par.field.model

        # Reverse descriptors also have some special ways to get to the model
        elif isinstance(par, ReverseSingleRelatedObjectDescriptor):
            par = par.field.related_field.model

    # Use unicode to force this to something the XLS writer can handle properly
    try:
        name = unicode(par._meta.get_field(components[-1]).verbose_name)
    except FieldDoesNotExist:
        name = unicode(components[-1])

    return name


def _get_field_value(field, obj):
    """
    Does some deep deiving to find the right value given a string like
    "building_snapshot__state"
    """
    par = obj
    components = field.split("__")
    for component in components[:-1]:
        par = getattr(par, component)
        if par is None:
            break

    try:
        return getattr(par, components[-1]) if par else None
    except AttributeError:
        # try extra_data JSONField
        return par.extra_data.get(components[-1])


def export_csv(qs, fields=[], cb=None):
    filename = tempfile.mktemp('.csv')
    export_file = open(filename, 'w')
    writer = csv.writer(export_file)

    if not fields:
        fields = list(_get_fields_from_queryset(qs))

    header = []
    for field in fields:
        field_name = _get_field_name(field, qs)
        header.append(field_name)
    writer.writerow(header)

    i = 0
    for obj in qs:
        row = _make_object_row(obj, fields)
        writer.writerow(row)
        if cb:
            cb(i)
        i += 1

    export_file.close()

    return filename


def export_xls(qs, fields=[], cb=None):
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Exported SEED Data')

    if not fields:
        fields = list(_get_fields_from_queryset(qs))

    for i in range(len(fields)):
        header = _get_field_name(fields[i], qs)
        worksheet.write(0, i, header)

    i = 0
    for obj in qs:
        row = _make_object_row(obj, fields)
        for j in range(len(row)):
            worksheet.write(i + 1, j, row[j])
        if cb:
            cb(i)
        i += 1

    filename = tempfile.mktemp('.xls')
    workbook.save(filename)

    return filename
