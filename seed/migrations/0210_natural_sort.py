from django.contrib.postgres.operations import CreateCollation
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0209_auto_20230929_0959'),
    ]

    operations = [
        CreateCollation(
            'natural_sort',
            provider='icu',
            locale='en@colNumeric=yes',
        ),
        # PropertyState fields
        migrations.AlterField(
            model_name='propertystate',
            name='address_line_1',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='address_line_2',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='audit_template_building_id',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='building_certification',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='city',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='custom_id_1',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='egrid_subregion_code',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='energy_alerts',
            field=models.TextField(blank=True, db_collation='natural_sort', null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='geocoding_confidence',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='home_energy_score_id',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='jurisdiction_property_id',
            field=models.TextField(blank=True, db_collation='natural_sort', null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='lot_number',
            field=models.TextField(blank=True, db_collation='natural_sort', null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='owner',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='owner_address',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='owner_city_state',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='owner_email',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='owner_postal_code',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='owner_telephone',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='pm_parent_property_id',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='pm_property_id',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='postal_code',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='property_name',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='property_notes',
            field=models.TextField(blank=True, db_collation='natural_sort', null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='property_timezone',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='property_type',
            field=models.TextField(blank=True, db_collation='natural_sort', null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='space_alerts',
            field=models.TextField(blank=True, db_collation='natural_sort', null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='state',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='ubid',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='propertystate',
            name='use_description',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        # TaxlotState fields
        migrations.AlterField(
            model_name='taxlotstate',
            name='address_line_1',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='address_line_2',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='block_number',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='city',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='custom_id_1',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='district',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='geocoding_confidence',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='jurisdiction_tax_lot_id',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=2047, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='postal_code',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='state',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='taxlotstate',
            name='ubid',
            field=models.CharField(blank=True, db_collation='natural_sort', max_length=255, null=True),
        ),
    ]
