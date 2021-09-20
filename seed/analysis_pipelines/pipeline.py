import abc
import functools
import inspect
import json
import logging

from seed.decorators import get_prog_key
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import Analysis, AnalysisPropertyView, AnalysisMessage

from django.db import transaction
from django.db.utils import OperationalError
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
    :returns: dictionary[int:int] IDs of the successfully created AnalysisPropertyViews listed by property_view_id
    """
    if progress_data_key is not None:
        progress_data = ProgressData.from_key(progress_data_key)
        progress_data.step('Copying property data')
    analysis_view_ids_by_property_view_id, failures = AnalysisPropertyView.batch_create(analysis_id, property_view_ids)
    for failure in failures:
        truncated_user_message = f'Failed to copy property data for PropertyView ID {failure.property_view_id}: {failure.message}'
        if len(truncated_user_message) > 255:
            truncated_user_message = truncated_user_message[:252] + '...'
        AnalysisMessage.objects.create(
            analysis_id=analysis_id,
            type=AnalysisMessage.DEFAULT,
            user_message=truncated_user_message,
        )
    return analysis_view_ids_by_property_view_id


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
        func._is_analysis_pipeline_task = True

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

            #
            # Check the analysis before running the task
            #
            # NOTE: this does not avoid time-of-check to time-of-use (TOCTOU) race conditions
            #   but should be generally sufficient as a guard
            #
            try:
                analysis = Analysis.objects.get(id=_analysis_id)
            except Analysis.DoesNotExist:
                # someone deleted the analysis, stop the chain
                log_message = {
                    'analysis_id': _analysis_id,
                    'debug_message': 'Analysis no longer exists before starting the task. '
                                     'Assuming the analysis was deleted and stopping the celery task chain.'
                }
                logger.info(json.dumps(log_message))
                _stop_task_chain(_self)
                return

            if analysis.status == expected_status:
                # everything is as expected, continue to run the task
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
                # TODO: we should probably try to fail the analysis at this point, but putting it off for now
                raise AnalysisPipelineException(f'When preparing to run the task {func}, expected analysis status to be {expected_status} but it was {analysis.status}')

            #
            # Run the task and catch all exceptions
            #
            try:
                return func(*args, **kwargs)
            except StopAnalysisTaskChain as e:
                # the task requested to stop the chain
                log_message = {
                    'analysis_id': _analysis_id,
                    'debug_message': 'StopAnalysisTaskChain exception raised, stopping the celery task chain.',
                    'exception': repr(e)
                }
                logger.info(json.dumps(log_message))
                _stop_task_chain(_self)
                return
            except Exception as e:
                # yikes, we didn't account for this. Try to bow out as gracefully as possible
                reraise_exception = False
                try:
                    with transaction.atomic():
                        # don't wait for lock to avoid deadlock
                        locked_analysis = (
                            Analysis.objects
                            .select_for_update(nowait=True)
                            .get(id=_analysis_id)
                        )

                        # analysis still exists, and we were able to get a lock on it
                        # something unexpected happened during the task
                        if locked_analysis.in_terminal_state():
                            # someone else has already finished the task off, just log and exit gracefully
                            log_message = {
                                'analysis_id': _analysis_id,
                                'debug_message': 'Task raised unhandled exception, but the analysis was already in a terminal state. '
                                                 'Ignoring the exception and stopping the celery task chain.',
                                'exception': repr(e)
                            }
                            logger.info(json.dumps(log_message))
                            _stop_task_chain(_self)
                            return
                        else:
                            # *force* the analysis to the failed status, log messages, and raise the exception
                            locked_analysis.status = Analysis.FAILED
                            locked_analysis.save()
                            AnalysisMessage.log_and_create(
                                logger=logger,
                                type_=AnalysisMessage.ERROR,
                                user_message='Unexpected error occurred.',
                                debug_message='Caught unexpected exception occurred during analysis task and the analysis still exists. '
                                              'Failing the analysis and re-raising the exception.',
                                analysis_id=_analysis_id,
                                analysis_property_view_id=None,
                                exception=e,
                            )
                            # NOTE: we must raise the exception once we exit the try/except
                            # we can't do it here b/c it would rollback the transaction
                            reraise_exception = True

                except OperationalError:
                    # the analysis still exists, but we failed to grab lock (worse case scenario)
                    # just log the error and raise the original exception (don't touch the analysis to avoid causing any more issues)
                    log_message = {
                        'analysis_id': _analysis_id,
                        'debug_message': 'Caught unexpected exception occurred during analysis task (and analysis still exists). '
                                         'Unable to acquire lock on analysis so it will likely be in an invalid state. '
                                         'Re-raising the exception.',
                        'exception': repr(e)
                    }
                    logger.error(json.dumps(log_message))
                    # no need to stop the task chain b/c raising the exception should do that
                    raise e
                except Analysis.DoesNotExist:
                    # someone deleted the analysis, and the original exception was probably due to that
                    # just log the error and forget
                    log_message = {
                        'analysis_id': _analysis_id,
                        'debug_message': 'Task raised unhandled exception, but the analysis no longer exists. '
                                         'Assuming the analysis was deleted. '
                                         'Ignoring the exception and stopping the celery task chain.',
                        'exception': repr(e)
                    }
                    logger.info(json.dumps(log_message))
                    _stop_task_chain(_self)
                    return

                if reraise_exception:
                    raise e

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
        from seed.analysis_pipelines.better import BETTERPipeline
        from seed.analysis_pipelines.eui import EUIPipeline

        if analysis.service == Analysis.BSYNCR:
            return BsyncrPipeline(analysis.id)
        elif analysis.service == Analysis.BETTER:
            return BETTERPipeline(analysis.id)
        elif analysis.service == Analysis.EUI:
            return EUIPipeline(analysis.id)
        else:
            raise AnalysisPipelineException(f'Analysis service type is unknown/unhandled. Service ID "{analysis.service}"')

    def prepare_analysis(self, property_view_ids, start_analysis=False):
        """Entrypoint for preparing an analysis.

        :param property_view_ids: list[int]
        :param start_analysis: bool, if true, the pipeline should immediately start the analysis after preparation
        :returns: ProgressData.result
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)
            if locked_analysis.status is Analysis.PENDING_CREATION:
                locked_analysis.status = Analysis.CREATING
                locked_analysis.save()
                progress_data = ProgressData(
                    self._get_progress_data_key_prefix(locked_analysis),
                    self._analysis_id,
                )
            else:
                raise AnalysisPipelineException('Analysis has already been prepared or is currently being prepared')

        self._prepare_analysis(property_view_ids, start_analysis)
        return progress_data.result()

    def start_analysis(self):
        """Entrypoint for starting an analysis.

        :returns: ProgressData.result
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)
            if locked_analysis.status is Analysis.READY:
                locked_analysis.status = Analysis.QUEUED
                locked_analysis.save()
                progress_data = ProgressData(
                    self._get_progress_data_key_prefix(locked_analysis),
                    self._analysis_id,
                )
            else:
                statuses = dict(Analysis.STATUS_TYPES)
                raise AnalysisPipelineException(f'Analysis cannot be started. Its status should be "{statuses[Analysis.READY]}" but it is "{statuses[locked_analysis.status]}"')

        self._start_analysis()
        return progress_data.result()

    def fail(self, message, logger, progress_data_key=None):
        """Fails the analysis. Creates an AnalysisMessage and logs it

        :param message: str, message to create an AnalysisMessage with
        :param logger: logging.Logger
        :param progress_data_key: str, fails the progress data if this key is provided
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)

            if progress_data_key is not None:
                progress_data = ProgressData.from_key(progress_data_key)
                progress_data.finish_with_error(message)
            else:
                progress_data = self.get_progress_data(locked_analysis)
                if progress_data is not None:
                    progress_data.finish_with_error(message)

            if locked_analysis.in_terminal_state():
                raise AnalysisPipelineException(f'Analysis is already in a terminal state: status {locked_analysis.status}')

            locked_analysis.status = Analysis.FAILED
            locked_analysis.end_time = tz.now()
            locked_analysis.save()

            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                user_message=message,
                debug_message='',
                analysis_id=self._analysis_id,
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

    def delete(self):
        """Deletes the analysis.

        Deleting an analysis can cause issues if it has tasks running, but
        we are currently requiring the tasks to deal with it instead of doing
        something more complex here.
        """
        Analysis.objects.get(id=self._analysis_id).delete()

    def set_analysis_status_to_ready(self, status_message):
        """Sets the analysis status to READY and saves the analysis start time.
        This method should be called once for an analysis. In addition, it should
        only be called by the pipeline once the analysis task has officially finished
        creation/preparation.

        Therefore, this should only be called in the context of a pipeline task.

        :param status_message: str, message to use for the finished ProgressData
            for the creating/preparation process
        :returns: None
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)

            if locked_analysis.status == Analysis.CREATING:
                progress_data = self.get_progress_data(locked_analysis)
                progress_data.finish_with_success(status_message)

                locked_analysis.status = Analysis.READY
                locked_analysis.start_time = tz.now()
                locked_analysis.save()
            else:
                statuses = dict(Analysis.STATUS_TYPES)
                raise AnalysisPipelineException(
                    f'Analysis status can\'t be set to READY. '
                    f'Its status should be "{statuses[Analysis.CREATING]}" but it is "{statuses[locked_analysis.status]}"'
                )

    def set_analysis_status_to_running(self):
        """Sets the analysis status to RUNNING and saves the analysis start time.
        This method should be called once for an analysis. In addition, it should
        only be called by the pipeline once the analysis task has officially started
        (ie a worker has picked up the actual work of the task).

        Therefore, this should only be called in the context of a pipeline task.

        :returns: ProgressData
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)

            # allow pipeline authors to go straight from Queued or Ready to Running
            valid_statuses = [Analysis.QUEUED, Analysis.READY]
            if locked_analysis.status in valid_statuses:
                progress_data = self.get_progress_data(locked_analysis)
                if progress_data:  # analyses in Ready status don't have progress data
                    progress_data.finish_with_success('Analysis is now being run')

                locked_analysis.status = Analysis.RUNNING
                locked_analysis.start_time = tz.now()
                locked_analysis.save()

                return ProgressData(
                    self._get_progress_data_key_prefix(locked_analysis),
                    locked_analysis.id
                )
            else:
                statuses = dict(Analysis.STATUS_TYPES)
                valid_statuses_str = ' or '.join([statuses[s] for s in valid_statuses])
                raise AnalysisPipelineException(
                    f'Analysis status can\'t be set to RUNNING. '
                    f'Its status should be {valid_statuses_str} but it is "{statuses[locked_analysis.status]}"'
                )

    def set_analysis_status_to_completed(self):
        """Sets the analysis status to COMPLETED and saves the analysis end time.
        This method should be called once for an analysis. In addition, it should
        only be called by the pipeline once the analysis task has officially ended
        (ie all work for the analysis is finished).

        Therefore, this should only be called in the context of a pipeline task.

        :returns: None
        """
        with transaction.atomic():
            locked_analysis = Analysis.objects.select_for_update().get(id=self._analysis_id)

            if locked_analysis.status == Analysis.RUNNING:
                progress_data = self.get_progress_data(locked_analysis)
                progress_data.finish_with_success('Analysis is complete')

                locked_analysis.status = Analysis.COMPLETED
                locked_analysis.end_time = tz.now()
                locked_analysis.save()
            else:
                statuses = dict(Analysis.STATUS_TYPES)
                raise AnalysisPipelineException(
                    f'Analysis status can\'t be set to COMPLETED. '
                    f'Its status should be "{statuses[Analysis.RUNNING]}" but it is "{statuses[locked_analysis.status]}"'
                )

    def _get_progress_data_key_prefix(self, analysis):
        statuses = dict(Analysis.STATUS_TYPES)
        return f'analysis-{statuses[analysis.status]}'

    def get_progress_data(self, analysis=None):
        """Get the ProgressData for the current task. If the analysis doesn't currently
        have progress data, this method returns None

        :returns: ProgressData | None
        """
        if analysis is None:
            analysis = Analysis.objects.get(id=self._analysis_id)

        if (
            # PENDING_CREATION doesn't have progress data due to... uninteresting reasons...
            analysis.status is Analysis.PENDING_CREATION
            # READY doesn't have progress data b/c it's waiting for the user to kick it off
            or analysis.status is Analysis.READY
            # Terminal states (e.g. Failed, Stopped, Complete) don't have progress data
            or analysis.in_terminal_state()
        ):
            return None

        progress_key = get_prog_key(
            self._get_progress_data_key_prefix(analysis),
            self._analysis_id
        )
        try:
            return ProgressData.from_key(progress_key)
        except Exception:
            logger.warn(
                f'Expected analysis to have progress data, but {progress_key} was not found. '
                'A race condition probably occurred due to the analysis status becoming "outdated" '
                'inside this method. Returning None for progress data...'
            )
            return None

    @abc.abstractmethod
    def _prepare_analysis(self, property_view_ids, start_analysis):
        """Abstract method which should do the work necessary for preparing
        an analysis, e.g. creating input file(s)

        :param property_view_ids: list[int]
        :param start_analysis: bool, if true, the pipeline should be started immediately
            after preparation is finished. It is the responsibility of the pipline
            implementation to make sure this happens by calling `pipeline.start_analysis()`
        :returns: None
        """
        pass

    @abc.abstractmethod
    def _start_analysis(self):
        """Abstract method which should start the analysis, e.g. make HTTP requests
        to the analysis service.

        :returns: None
        """
        pass
