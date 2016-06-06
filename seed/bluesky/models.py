from __future__ import unicode_literals

from django_pgjson.fields import JsonField

from django.db import models

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization


class Cycle(models.Model):
    organization = models.ForeignKey(Organization, blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True)
    name = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()

    def __unicode__(self):
        return u'Cycle - %s' % (self.name)


class Property(models.Model):
    organization = models.ForeignKey(Organization)
    campus = models.BooleanField(default=False)
    parent_property = models.ForeignKey('Property', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'properties'

    def __unicode__(self):
        return u'Property - %s' % (self.pk)


class PropertyState(models.Model):
    # import_record = models.ForeignKey(ImportRecord)
    confidence = models.FloatField(default=0)

    jurisdiction_property_identifier = models.CharField(max_length=255, null=True, blank=True)
    lot_number = models.CharField(max_length=255, null=True, blank=True)
    property_name = models.CharField(max_length=255, null=True, blank=True)
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=255, null=True, blank=True)
    building_count = models.IntegerField(null=True, blank=True)  # Only spot where it's 'building' in the app, b/c this is a PortMgr field.
    property_notes = models.TextField(null=True, blank=True)
    use_description = models.CharField(max_length=255, null=True, blank=True)  # Tax IDs are often stuck in here.
    gross_floor_area = models.FloatField(null=True, blank=True)
    year_built = models.IntegerField(null=True, blank=True)
    recent_sale_date = models.DateTimeField(null=True, blank=True)
    conditioned_floor_area = models.FloatField(null=True, blank=True)
    occupied_floor_area = models.FloatField(null=True, blank=True)
    owner = models.CharField(max_length=255, null=True, blank=True)
    owner_email = models.CharField(max_length=255, null=True, blank=True)
    owner_telephone = models.CharField(max_length=255, null=True, blank=True)
    owner_address = models.CharField(max_length=255, null=True, blank=True)
    owner_city_state = models.CharField(max_length=255, null=True, blank=True)
    owner_postal_code = models.CharField(max_length=255, null=True, blank=True)
    building_portfolio_manager_identifier = models.CharField(max_length=255, null=True, blank=True)
    building_home_energy_saver_identifier = models.CharField(max_length=255, null=True, blank=True)
    energy_score = models.IntegerField(null=True, blank=True)
    site_eui = models.FloatField(null=True, blank=True)
    generation_date = models.DateTimeField(null=True, blank=True)
    release_date = models.DateTimeField(null=True, blank=True)
    site_eui_weather_normalized = models.FloatField(null=True, blank=True)
    source_eui = models.FloatField(null=True, blank=True)
    energy_alerts = models.TextField(null=True, blank=True)
    space_alerts = models.TextField(null=True, blank=True)
    building_certification = models.CharField(max_length=255, null=True, blank=True)

    extra_data = JsonField(default={}, blank=True)

    def __unicode__(self):
        return u'Property State - %s' % (self.pk)


class PropertyView(models.Model):
    property = models.ForeignKey(Property, related_name='views')
    cycle = models.ForeignKey(Cycle)
    state = models.ForeignKey(PropertyState)

    def __unicode__(self):
        return u'Property View - %s' % (self.pk)


class TaxLot(models.Model):
    organization = models.ForeignKey(Organization)

    def __unicode__(self):
        return u'TaxLot - %s' % (self.pk)


class TaxLotState(models.Model):
    # The state field names should match pretty close to the pdf, just
    # because these are the most 'public' fields in terms of
    # communicating with the cities.

    # import_record = models.ForeignKey(ImportRecord)
    confidence = models.FloatField(default=0)

    jurisdiction_taxlot_identifier = models.CharField(max_length=255, null=True, blank=True)
    block_number = models.CharField(max_length=255, null=True, blank=True)
    district = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=255, null=True, blank=True)
    number_properties = models.IntegerField(null=True, blank=True)

    extra_data = JsonField(default={}, blank=True)

    def __unicode__(self):
        return u'TaxLot State - %s' % (self.pk)


class TaxLotView(models.Model):
    taxlot = models.ForeignKey(TaxLot, related_name='views', null=True)
    state = models.ForeignKey(TaxLotState)
    cycle = models.ForeignKey(Cycle)

    def __unicode__(self):
        return u'TaxLot View - %s' % (self.pk)


class TaxLotProperty(models.Model):
    property_view = models.ForeignKey(PropertyView)
    taxlot_view = models.ForeignKey(TaxLotView)

    cycle = models.ForeignKey(Cycle)

    # If there is a complex TaxLot/Property association, this field
    # lists the "main" tax lot that Properties should be reported under.
    # User controlled flag.
    primary = models.BooleanField(default=True)

    def __unicode__(self):
        return u'M2M Property View %s / TaxLot View %s' % (self.property_view_id, self.taxlot_view_id)
