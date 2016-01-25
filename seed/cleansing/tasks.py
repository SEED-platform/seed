# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from models import Cleansing
from seed.decorators import get_prog_key
from seed.utils.cache import set_cache
from seed.models import BuildingSnapshot

logger = get_task_logger(__name__)


@shared_task
def cleanse_data_chunk(ids, file_pk, increment):
    """

    :param ids: list of primary key ids to process
    :param file_pk: import file primary key
    :param increment: currently unused, but needed because of the special method that appends this onto the function  # NOQA
    :return: None
    """

    # get the db objects based on the ids
    qs = BuildingSnapshot.objects.filter(id__in=ids).iterator()

    c = Cleansing()
    c.cleanse(qs)
    c.save_to_cache(file_pk)


@shared_task
def finish_cleansing(file_pk):
    """
    Chord that is called after the cleansing is complete

    :param file_pk: import file primary key
    :return:
    """

    prog_key = get_prog_key('cleanse_data', file_pk)
    result = {
        'status': 'success',
        'progress': 100,
        'message': 'cleansing complete'
    }
    set_cache(prog_key, result['status'], result)
