# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from seed.decorators import get_prog_key
from seed.utils.cache import get_cache, set_cache, delete_cache

_log = logging.getLogger(__name__)


class ProgressData(object):

    def __init__(self, func_name, unique_id, init_data=None):
        self.func_name = func_name
        self.unique_id = unique_id
        self.key = get_prog_key(func_name, unique_id)
        self.total = None
        self.increment_by = None

        # Load in the initialized data, some of this may be overloaded based
        # on the contents in the cache
        self.initialize(init_data)

        # read the data from the cache, if there is any
        self.load()

    def initialize(self, init_data=None):
        if init_data:
            self.data = init_data
        else:
            self.data = {}
            self.data['status'] = 'not-started'
            self.data['status_message'] = ''
            self.data['progress'] = 0
            self.data['progress_key'] = self.key
            self.data['unique_id'] = self.unique_id
            self.data['func_name'] = self.func_name
            self.data['message'] = None
            self.data['stacktrace'] = None
            self.data['summary'] = None
            self.total = None
            self.increment_by = None

        # set some member variables
        if 'progress_key' in self.data:
            self.key = self.data['progress_key']

        if 'total' in self.data:
            self.total = self.data['total']

        return self.save()

    def delete(self):
        """
        Delete the cache and reinitialize

        :return: dict, re-initialized data
        """
        delete_cache(self.key)

        return self.initialize()

    def finish_with_success(self, message=None):
        # update to get the latest results out of the cache
        self.load()

        self.data['status'] = 'success'
        self.data['progress'] = 100
        self.data['message'] = message

        return self.save()

    def finish_with_warning(self, message=None):
        # update to get the latest results out of the cache
        self.load()

        _log.debug('Returning with warning from %s with %s' % (self.key, message))
        self.data['status'] = 'warning'
        self.data['progress'] = 100
        self.data['message'] = message

        return self.save()

    def finish_with_error(self, message=None, stacktrace=None):
        # update to get the latest results out of the cache
        self.load()

        _log.debug('Returning with error from %s with %s' % (self.key, message))
        self.data['status'] = 'error'
        self.data['progress'] = 100
        self.data['message'] = message
        self.data['stacktrace'] = stacktrace

        return self.save()

    @classmethod
    def from_key(cls, key):
        data = get_cache(key)
        if 'func_name' in data and 'unique_id' in data:
            return cls(func_name=data['func_name'], unique_id=data['unique_id'], init_data=data)
        else:
            raise Exception("Could not find key %s in cache" % key)

    def save(self):
        """Save the data to the cache"""
        # save some member variables
        self.data['total'] = self.total

        set_cache(self.key, self.data['status'], self.data)

        return get_cache(self.key)

    def load(self):
        """Read in the data from the cache"""

        # Merge the existing data with items from the cache, favor cache items
        self.data = dict(list(self.data.items()) + list(get_cache(self.key).items()))

        # set some member variables
        if self.data['progress_key']:
            self.key = self.data['progress_key']

        if self.data['total']:
            self.total = self.data['total']

    def step(self, status_message=None, new_summary=None):
        """Step the function by increment_value and save back to the cache"""
        # load the latest value out of the cache
        self.load()

        value = self.data['progress']
        if value + self.increment_value() >= 100.0:
            value = 100.0
        else:
            value += self.increment_value()

        self.data['progress'] = value
        self.data['status'] = 'parsing'
        if status_message is not None:
            self.data['status_message'] = status_message

        if new_summary is not None:
            self.data['summary'] = new_summary

        self.save()

        return self.result()

    def result(self):
        """
        Return the result from the cache

        :return: dict
        """
        return get_cache(self.key)

    def increment_value(self):
        """
        Return the value to increment the progress back. Currently this is always assume that that
        size of the step is 1 to the self.total count.

        :return: float, value to increment the step by
        """
        if self.total:
            return 1.0 / self.total * 100
        else:
            return 0

    def add_file_info(self, filename, info):
        """
        Add info for a file. Used when mapping xml data and errors/warnings are encountered.
        After mapping, the frontend checks for the 'file_info' attribute and displays
        the messages.
        """
        self.load()

        file_info = self.data.get('file_info', {})
        file_info[filename] = info
        self.data['file_info'] = file_info

        self.save()

    def update_summary(self, summary):
        self.data['summary'] = summary
        self.save()

    def summary(self):
        """
        Return the summary data of the progress key
        :return: dict
        """
        # read the latest from the cache
        self.load()
        return self.data['summary']
