# Generated by Django 1.9.5 on 2016-04-11 18:39

import django_extensions.db.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0015_merge"),
    ]

    operations = [
        migrations.AlterField(
            model_name="buildingsnapshot",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
        ),
        migrations.AlterField(
            model_name="buildingsnapshot",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
        ),
        migrations.AlterField(
            model_name="compliance",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
        ),
        migrations.AlterField(
            model_name="compliance",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
        ),
        migrations.AlterField(
            model_name="project",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
        ),
        migrations.AlterField(
            model_name="project",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
        ),
        migrations.AlterField(
            model_name="projectbuilding",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
        ),
        migrations.AlterField(
            model_name="projectbuilding",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
        ),
        migrations.AlterField(
            model_name="statuslabel",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
        ),
        migrations.AlterField(
            model_name="statuslabel",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
        ),
    ]
