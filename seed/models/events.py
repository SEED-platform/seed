from django.db import models
from django_extensions.db.models import TimeStampedModel
from model_utils.managers import InheritanceManager

from seed.models import Cycle, Property


class Event(TimeStampedModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='events')
    cycle = models.ForeignKey(Cycle, on_delete=models.PROTECT)

    objects = InheritanceManager()


class ATEvent(Event):
    building_file = models.ForeignKey("BuildingFile", on_delete=models.PROTECT)
    # has a one to many with Scenario


class AnalysisEvent(Event):
    analysis = models.ForeignKey("Analysis", on_delete=models.PROTECT)


class NoteEvent(Event):
    note = models.ForeignKey("Note", on_delete=models.PROTECT)