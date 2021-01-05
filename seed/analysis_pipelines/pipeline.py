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


def analysis_pipeline_task(expected_status):
    """Decorator factory for analysis pipeline celery tasks. In other words, this
    function _returns_ a decorator for wrapping tasks used in analysis pipelines.
    This wrapper **MUST** be added to all pipeline tasks to avoid unexpected errors.
    The function and its decorators must look something like this:
    ```
    @shared_task(bind=True)
    @analysis_pipeline_task(Analysis.SOME_STATUS)
    def my_task(self, analysis_id, ...):
        ...
    ```
    Note:
    - `bind=True` is provided for the shared_task decorator (necessary for stopping the celery chain, ie when we don't want to run the remaining tasks)
    - `self` is the first argument of the function (the celery task instance is passed as first argument when `bind=True`)
    - `analysis_id` is some argument (it can be in any position)

    The decorator provides the following functionality:
    - Checks if the analysis exists before running the task
    - Checks if the analysis status is the expected status before running the task
    - Catches any uncaught exceptions from the task, and handles them as we see fit

    The benefit of this functionality is to
    1. guard tasks from starting when an analysis has already been stopped, deleted, etc.
    2. handling some unhandled exceptions gracefully (e.g. a database error when someone else deletes the analysis)

    :param expected_status: int, one of Analysis.STATUS_TYPES
    :returns: function, a decorator
    """

    def decorator_analysis_pipeline_task(func):
        # add a property to indicate this function was wrapped
        # the only purpose of this is so we can test that all tasks have been properly wrapped
        func._analysis_pipeline_task = True

        params = inspect.getfullargspec(func)

        self_error_message = 'Decorated task function must have `self` as first argument, and @shared_task decorator must have `bind=True`'
        try:
            if params.args.index('self') != 0:
                raise Exception(self_error_message)
        except ValueError:
            raise Exception(self_error_message)

        try:
            analysis_id_param_idx = params.args.index('analysis_id')
        except ValueError:
            raise Exception('Decorated task function must include an argument named "analysis_id"')

        @functools.wraps(func)
        def _run_task(*args, **kwargs):
            def _stop_task_chain(task_instance):
                # stops the celery task chain (ie any child tasks)
                # see: https://github.com/celery/celery/issues/3550
                task_instance.request.chain = task_instance.request.callbacks = None

            # self is first arg, the celery.Task instance, b/c the celery task was decorated with `bind=True`
            _self = args[0]

            # try to get the analysis_id from args, then from kwargs
            try:
                _analysis_id = args[analysis_id_param_idx]
            except IndexError:
                _analysis_id = kwargs['analysis_id']

            # Check the analysis before running the task
            # If the analysis exists and has the expected status, run the task
            # If the analysis exists but the status isn't what we expected, and...
            #   - It WAS stopped or failed, stop the task chain (someone somewhere else stopped/failed the task)
            #   - It WAS NOT stopped or failed, raise an exception! (something unexpected has happened)
            # If the analysis no longer exists, stop the task chain (someone somewhere deleted the analysis)
            try:
                analysis = Analysis.objects.get(id=_analysis_id)
                if analysis.status == expected_status:
                    pass
                elif analysis.status in [Analysis.STOPPED, Analysis.FAILED]:
                    # assume someone else stopped or failed the analysis and that we shouldn't run the task
                    log_message = {
                        'analysis_id': _analysis_id,
                        'debug_message': 'Analysis has already been stopped or failed before starting the task. '
                                         'Not running the task and stopping the task chain.'
                    }
                    logger.info(json.dumps(log_message))
                    _stop_task_chain(_self)
                    return
                else:
                    # something Bad has happened
                    raise AnalysisPipelineException(f'When preparing to run the task {func}, expected analysis status to be {expected_status} but it was {analysis.status}')
            except Analysis.DoesNotExist:
                # someone deleted the analysis
                log_message = {
                    'analysis_id': _analysis_id,
                    'debug_message': 'Analysis no longer exists before starting the task. '
                                     'Assuming the analysis was deleted and stopping the celery task chain.'
                }
                logger.info(json.dumps(log_message))
                _stop_task_chain(_self)
                return

            # Catch all exceptions raised by the task
            # If the exception was to stop the task chain, stop the task chain
            # If the analysis no longer exists, ignore the exception (the analysis was deleted by someone else)
            # If the analysis _does_ still exist, raise the exception (something unexpected happened)
            try:
                return func(*args, **kwargs)
            except StopAnalysisTaskChain as e:
                log_message = {
                    'analysis_id': _analysis_id,
                    'debug_message': 'StopAnalysisTaskChain exception raised, stopping the celery task chain.',
                    'exception': repr(e)
                }
                logger.info(json.dumps(log_message))
                _stop_task_chain(_self)
                return
            except Exception as e:
                try:
                    Analysis.objects.get(id=_analysis_id)

                    log_message = {
                        'analysis_id': _analysis_id,
                        'debug_message': 'Caught unexpected exception occurred during analysis task (and analysis still exists). Re-raising exception and continuing.',
                        'exception': repr(e)
                    }
                    logger.error(json.dumps(log_message))
                    raise e
                except Analysis.DoesNotExist:
                    # someone deleted the analysis, and the error was probably due to that
                    log_message = {
                        'analysis_id': _analysis_id,
                        'debug_message': 'Task raised unhandled exception, but the analysis no longer exists. '
                                         'Assuming the analysis was deleted and stopping the celery task chain.',
                        'exception': repr(e)
                    }
                    logger.info(json.dumps(log_message))
                    _stop_task_chain(_self)
                    return

        return _run_task
    return decorator_analysis_pipeline_task


class AnalysisPipelineException(Exception):
    """An analysis pipeline specific exception"""
    pass


class StopAnalysisTaskChain(Exception):
    """Analysis pipeline tasks should raise this exception to stop the celery task
    chain.
    """
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
