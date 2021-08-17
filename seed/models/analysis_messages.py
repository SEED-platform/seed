# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
import json

from django.db import models

from seed.models import (
    Analysis,
    AnalysisPropertyView
)


logger = logging.getLogger(__name__)


class AnalysisMessage(models.Model):
    """
    The AnalysisMessage represents user-facing messages of events that occur
    during an analysis, like a breadcrumb trail.
    """
    DEFAULT = 1
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40

    MESSAGE_TYPES = (
        (DEFAULT, 'default'),
        (DEBUG, 'debug'),
        (INFO, 'info'),
        (WARNING, 'warning'),
        (ERROR, 'error'),
    )
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    # if the message is relevant to a specific property then it should be linked
    # to an AnalysisPropertyView in addition to being linked to the analysis.
    # e.g. if the AnalysisPropertyView is missing some required data
    # if the message is generic and applies to the entire analysis, analysis_property_view
    # should be None/NULL
    # e.g. the service request returned a non-200 response
    analysis_property_view = models.ForeignKey(AnalysisPropertyView, on_delete=models.CASCADE, null=True, blank=True)
    type = models.IntegerField(choices=MESSAGE_TYPES)
    # human-readable message which is presented on the frontend
    user_message = models.CharField(max_length=255, blank=False, default=None)
    # message for debugging purposes, not intended to be displayed on frontend
    debug_message = models.CharField(max_length=255, blank=True)

    @classmethod
    def log_and_create(cls, logger, type_, user_message, debug_message, analysis_id,
                       analysis_property_view_id=None, exception=None):
        """Log the messages using the provided logger, then create an AnalysisMessage

        :param logger: logging.Logger
        :param type_: AnalysisMessage.MESSAGE_TYPE
        :param user_message: str
        :param debug_message: str
        :param analysis_id: int
        :param analysis_property_view_id: int, optional
        :param exception: Exception, optional
        :returns: AnalysisMessage
        """
        logger_levels = {
            cls.DEFAULT: logging.NOTSET,
            cls.DEBUG: logging.DEBUG,
            cls.INFO: logging.INFO,
            cls.WARNING: logging.WARNING,
            cls.ERROR: logging.ERROR
        }
        logger_level = logger_levels.get(type_)
        if logger_level is None:
            logger.error(f'Unhandled AnalysisMessage type passed to logger: "{type_}". Fix this by updating the log_and_create method.')
            logger_level = logging.ERROR

        log_message_dict = {
            'analysis_id': analysis_id,
            'analysis_property_view': analysis_property_view_id,
            'user_message': user_message,
            'debug_message': debug_message,
            'exception': repr(exception),
        }
        logger.log(logger_level, json.dumps(log_message_dict))

        # truncate the messages to make sure they meet our db constraints
        MAX_MESSAGE_LENGTH = 255
        ELIPSIS = '...'
        if len(user_message) > MAX_MESSAGE_LENGTH:
            user_message = user_message[:MAX_MESSAGE_LENGTH - len(ELIPSIS)] + ELIPSIS
        if len(debug_message) > MAX_MESSAGE_LENGTH:
            debug_message = debug_message[:MAX_MESSAGE_LENGTH - len(ELIPSIS)] + ELIPSIS

        return AnalysisMessage.objects.create(
            type=type_,
            analysis_id=analysis_id,
            analysis_property_view_id=analysis_property_view_id,
            user_message=user_message,
            debug_message=debug_message,
        )
