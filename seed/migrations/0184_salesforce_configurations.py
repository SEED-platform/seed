# Generated by Django 3.2.16 on 2023-02-01 17:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0024_salesforce_configurations'),
        ('seed', '0183_auto_20221216_1221'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesforceMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('salesforce_fieldname', models.CharField(max_length=255)),
                ('column', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='salesforce_column', to='seed.column')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='salesforce_mappings', to='orgs.organization', verbose_name='SeedOrg')),
            ],
        ),
        migrations.CreateModel(
            name='SalesforceConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_rec_type', models.CharField(blank=True, max_length=20, null=True)),
                ('contact_rec_type', models.CharField(blank=True, max_length=20, null=True)),
                ('last_update_date', models.DateTimeField(blank=True, null=True)),
                ('unique_benchmark_id_fieldname', models.CharField(blank=True, max_length=128, null=True)),
                ('url', models.CharField(blank=True, max_length=200, null=True)),
                ('username', models.CharField(blank=True, max_length=128, null=True)),
                ('password', models.CharField(blank=True, max_length=128, null=True)),
                ('security_token', models.CharField(blank=True, max_length=128, null=True)),
                ('domain', models.CharField(blank=True, max_length=50, null=True)),
                ('cycle_fieldname', models.CharField(blank=True, max_length=128, null=True)),
                ('status_fieldname', models.CharField(blank=True, max_length=128, null=True)),
                ('labels_fieldname', models.CharField(blank=True, max_length=128, null=True)),
                ('logging_email', models.CharField(blank=True, max_length=128, null=True)),
                ('benchmark_contact_fieldname', models.CharField(blank=True, max_length=128, null=True)),
                ('account_name_column', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='account_name_column', to='seed.column')),
                ('compliance_label', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='compliance_label', to='seed.statuslabel')),
                ('contact_email_column', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='contact_email_column', to='seed.column')),
                ('contact_name_column', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='contact_name_column', to='seed.column')),
                ('indication_label', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='indication_label', to='seed.statuslabel')),
                ('organization', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='orgs.organization')),
                ('seed_benchmark_id_column', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='benchmark_id_column', to='seed.column')),
                ('violation_label', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='violation_label', to='seed.statuslabel')),
            ],
        ),
    ]