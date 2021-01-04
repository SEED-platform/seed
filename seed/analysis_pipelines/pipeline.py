import abc
import functools
import inspect
import json
import logging

from seed.lib.progress_data.progress_data import ProgressData
from seed.models import Analysis, AnalysisPropertyView, AnalysisMessage

from django.db import transaction
from django.utils import timezone as tz

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def task_create_analysis_property_views(analysis_id, property_view_ids, progress_data_key=None):
    """A celery task which batch creates the AnalysisPropertyViews for the analysis.
    It will create AnalysisMessages for any property view IDs that couldn't be
    used to create an AnalysisPropertyView.

    :param analysis_id: int
    :param property_view_ids: list[int]
    :param progress_data_key: str, optional
    :returns: list[int], IDs of the successfully created AnalysisPropertyViews
    """
    if progress_data_key is not None:
        progress_data = ProgressData.from_key(progress_data_key)
        progress_data.step('Copying property data')
    analysis_view_ids, failures = AnalysisPropertyView.batch_create(analysis_id, property_view_ids)
    for failure in failures:
        AnalysisMessage.objects.create(
            analysis_id=analysis_id,
            type=AnalysisMessage.DEFAULT,
            user_message=f'Failed to copy property data for PropertyView ID {failure.property_view_id}: {failure.message}',
        )
    return analysis_view_ids


def check_analysis_status(status):
    """Decorator factory for checking the status of the analysis, and raise an
    exception if the status isn't what was expected

    This can be used as a guard to avoid running a task when an analysis has been
    stopped or failed elsewhere.

    :param status: int, one of Analysis.STATUS_TYPES
    :returns: function, a decorator
    """

    def decorator_check_analysis_status(func):
        try:
            params = inspect.getfullargspec(func)
            analysis_id_param_idx = params.args.index('analysis_id')
        except ValueError:
            raise Exception('Decorated function must include an argument named "analysis_id"')

        @functools.wraps(func)
        def _check(*args, **kwargs):
            # try to get the analysis_id from args, then from kwargs
            try:
                _analysis_id = args[analysis_id_param_idx]
            except IndexError:
                _analysis_id = kwargs['analysis_id']
            analysis = Analysis.objects.get(id=_analysis_id)
            if analysis.status != status:
                raise AnalysisPipelineException(f'Expected analysis status to be {status} but it was {analysis.status}')

            return func(*args, **kwargs)
        return _check
    return decorator_check_analysis_status


class AnalysisPipelineException(Exception):
    pass


class AnalysisPipeline(abc.ABC):
    """
    AnalysisPipeline is an abstract class for defining workflows for preparing,
    running, and post processing analyses.
    """
    def __init__(self, analysis_id):
        self._analysis_id = analysis_id

    @classmethod
    def factory(cls, analysis):
        """Factory method for constructing pipelines for a given analysis.

        :param analysis: Analysis
        :returns: An implementation of AnalysisPipeline, e.g. BsyncrPipeline
        """
        # import here to avoid circular dependencies
        from seed.analysis_pipelines.bsyncr import BsyncrPipeline

        if analysis.service == Analysis.BSYNCR:
            return BsyncrPipeline(analysis.id)
        else:
            raise AnalysisPipelineException(f'Analysis service type is unknown/unhandled. Service ID "{analysis.service}"')

    def prepare_analysis(self, property_view_ids):
        """Entrypoint for preparing an analysis.

        :param property_view_ids: list[int]
        :returns: str, ProgressData.result
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)
            if locked_analysis.status is Analysis.PENDING_CREATION:
                locked_analysis.status = Analysis.CREATING
                locked_analysis.save()
            else:
                raise AnalysisPipelineException('Analysis has already been prepared or is currently being prepared')

        return self._prepare_analysis(self._analysis_id, property_view_ids)

    def start_analysis(self):
        """Entrypoint for starting an analysis.

        :returns: str, ProgressData.result
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)
            if locked_analysis.status is Analysis.READY:
                locked_analysis.status = Analysis.QUEUED
                locked_analysis.save()
            else:
                statuses = dict(Analysis.STATUS_TYPES)
                raise AnalysisPipelineException(f'Analysis cannot be started. Its status should be "{statuses[Analysis.READY]}" but it is "{statuses[locked_analysis.status]}"')

        return self._start_analysis()

    def fail(self, message, progress_data_key=None, logger=None):
        """Fails the analysis. Creates an AnalysisMessage and optionally logs it
        if a logger is provided.

        :param message: str, message to create an AnalysisMessage with
        :param progress_data_key: str, fails the progress data if this key is provided
        :param logger: logging.Logger
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)

            if progress_data_key is not None:
                progress_data = ProgressData.from_key(progress_data_key)
                progress_data.finish_with_error(message)

            if locked_analysis.in_terminal_state():
                raise AnalysisPipelineException(f'Analysis is already in a terminal state: status {locked_analysis.status}')

            locked_analysis.status = Analysis.FAILED
            locked_analysis.end_time = tz.now()
            locked_analysis.save()

            if logger is not None:
                AnalysisMessage.log_and_create(
                    logger=logger,
                    type_=AnalysisMessage.ERROR,
                    user_message=message,
                    debug_message='',
                    analysis_id=self._analysis_id,
                )
            else:
                AnalysisMessage.objects.create(
                    analysis_id=self._analysis_id,
                    type=AnalysisMessage.ERROR,
                    user_message=message,
                )

    def stop(self):
        """Stops the analysis. If analysis is already in a terminal state it does
        nothing
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)

            if locked_analysis.in_terminal_state():
                log_message = {
                    'analysis_id': self._analysis_id,
                    'debug_message': 'Attempted to stop analysis when already in a terminal state'
                }
                logger.info(json.dumps(log_message))
                return

            locked_analysis.status = Analysis.STOPPED
            locked_analysis.end_time = tz.now()
            locked_analysis.save()

    @abc.abstractmethod
    def _prepare_analysis(self, analysis_id, property_view_ids):
        """Abstract method which should do the work necessary for preparing
        an analysis, e.g. creating input file(s)

        :param analysis_id: int
        :param property_view_ids: list[int]
        :returns: str, ProgressData.result
        """
        pass

    @abc.abstractmethod
    def _start_analysis(self):
        """Abstract method which should start the analysis, e.g. make HTTP requests
        to the analysis service.

        :param analysis_id: int
        :returns: str, ProgressData.result
        """
        pass
