# Generated by Django 1.11.6 on 2018-01-11 23:31

from django.db import migrations


def convert_rule_units_to_pint(apps, schema_editor):
    """
    pre-pint rules (esp old defaults) will have their units specified as
    human-readable strings instead of Pint specs. This converts them so
    that any custom rules can be maintained instead of just dumped and
    re-created.
    """
    Rule = apps.get_model("seed", "Rule")
    for rule in Rule.objects.all():
        if rule.units == "square feet":
            rule.units = "ft**2"
        elif rule.units == "kBtu/sq. ft./year":
            rule.units = "kBtu/ft**2/year"

        rule.save()


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0085_rename_propertystate_from_pint"),
    ]

    operations = [migrations.RunPython(convert_rule_units_to_pint)]
