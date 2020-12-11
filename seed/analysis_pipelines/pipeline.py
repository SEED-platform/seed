import abc

from seed.models import Analysis, AnalysisPropertyView

from django.db import transaction
from celery import shared_task


@shared_task
def task_create_analysis_property_views(analysis_id, property_view_ids):
    analysis_view_ids, failures = AnalysisPropertyView.batch_create(analysis_id, property_view_ids)
    # TODO: create analysis messages based on failures
    return analysis_view_ids


class AnalysisPipelineException(Exception):
    pass


class AnalysisPipeline(abc.ABC):
    def __init__(self, analysis_id):
        self._analysis_id = analysis_id

    def prepare_analysis(self, property_view_ids):
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(self._analysis_id)
            if locked_analysis.status is None:
                locked_analysis.status = Analysis.CREATING
                locked_analysis.save()
            else:
                raise AnalysisPipelineException('Analysis has already been prepared')

        return self._prepare_analysis(self._analysis_id, property_view_ids)

    @abc.abstractmethod
    def _prepare_analysis(self, analysis_id, property_view_ids):
        pass
