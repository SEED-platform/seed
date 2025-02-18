from django.db import migrations


def merge_extra_data(b1, b2, default=None):
    """
    This is a frozen version of `seed.mappings.mapper.merge_extra_data`
    """
    default = default or b1
    non_default = b2
    if default != b1:
        non_default = b1

    extra_data_sources = {}
    default_extra_data = getattr(default, "extra_data", {})
    non_default_extra_data = getattr(non_default, "extra_data", {})

    all_keys = set(list(default_extra_data.keys()) + list(non_default_extra_data.keys()))
    extra_data = {k: default_extra_data.get(k) or non_default_extra_data.get(k) for k in all_keys}

    for item in extra_data:
        if default_extra_data.get(item):
            extra_data_sources[item] = default.pk
        elif non_default_extra_data.get(item):
            extra_data_sources[item] = non_default.pk
        else:
            extra_data_sources[item] = default.pk

    return extra_data, extra_data_sources


def recover_extra_data(app, schema_editor, **kwargs):
    """
    Used in old version (< 1.5), not needed anymore
    """


def merge_extra_data_from_parents(bs):
    for parent in bs.parents.order_by("created").all():
        # First do a recursive call to do a recursive merge of all extra_data
        # fields deeper down the tree.
        merge_extra_data_from_parents(parent)

        # Now do a merge with this bs, prioritizing the data that is already in
        # place which will merge in any non-blank data from deeper down the
        # tree.
        extra_data, extra_data_sources = merge_extra_data(bs, parent)
        bs.extra_data = extra_data
        bs.extra_data_sources = extra_data_sources
        bs.save()


def stub(*args, **kwargs):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0011_auto_20151209_0821"),
    ]

    operations = [
        migrations.RunPython(recover_extra_data, stub),
    ]
