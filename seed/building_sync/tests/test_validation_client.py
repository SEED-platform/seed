# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
from unittest.mock import patch

from django.test import TestCase
from requests.models import Response
import json

from config.settings.common import BASE_DIR
from seed.building_sync.validation_client import validate_use_case, DEFAULT_USE_CASE, DEFAULT_SCHEMA_VERSION


def responseFactory(status_code, body_dict):
    the_response = Response()
    the_response.status_code = status_code
    the_response._content = json.dumps(body_dict).encode()
    return the_response


class TestValidationClient(TestCase):
    def setUp(self):
        # NOTE: the contents of these files are not actually used, it's just convenient
        # to use these files so we don't have to create tmp ones and clean them up
        self.single_file = open(os.path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_v2_0_bricr_workflow.xml'))
        self.zip_file = open(os.path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'ex_1_and_buildingsync_ex01_measures.zip'))

    def test_validation_single_file_ok(self):
        good_body = {
            'success': True,
            'schema_version': DEFAULT_SCHEMA_VERSION,
            'validation_results': {
                'schema': {
                    'valid': True
                },
                'use_cases': {
                    DEFAULT_USE_CASE: {
                        'errors': [],
                        'warnings': [],
                    }
                }
            }
        }

        with patch('seed.building_sync.validation_client._validation_api_post', return_value=responseFactory(200, good_body)):
            all_files_valid, file_summaries = validate_use_case(self.single_file)

        self.assertTrue(all_files_valid)
        self.assertEqual([], file_summaries)

    def test_validation_zip_file_ok(self):
        good_body = {
            'success': True,
            'schema_version': DEFAULT_SCHEMA_VERSION,
            'validation_results': [
                {
                    'file': 'file1.xml',
                    'results': {
                        'schema': {
                            'valid': True
                        },
                        'use_cases': {
                            DEFAULT_USE_CASE: {
                                'errors': [],
                                'warnings': [],
                            }
                        }
                    }
                }, {
                    'file': 'file2.xml',
                    'results': {
                        'schema': {
                            'valid': True
                        },
                        'use_cases': {
                            DEFAULT_USE_CASE: {
                                'errors': [],
                                'warnings': [],
                            }
                        }
                    }
                }
            ]
        }

        with patch('seed.building_sync.validation_client._validation_api_post', return_value=responseFactory(200, good_body)):
            all_files_valid, file_summaries = validate_use_case(self.zip_file)

        self.assertTrue(all_files_valid)
        self.assertEqual([], file_summaries)

    def test_validation_fails_when_one_file_has_bad_schema(self):
        bad_file_result = {
            'file': 'bad.xml',
            'results': {
                'schema': {
                    # Set the schema as NOT valid
                    'valid': False,
                    'errors': ['schema was bad']
                },
                'use_cases': {
                    DEFAULT_USE_CASE: {
                        'errors': [],
                        'warnings': [],
                    }
                }
            }
        }

        body = {
            'success': True,
            'schema_version': DEFAULT_SCHEMA_VERSION,
            'validation_results': [
                {
                    'file': 'file1.xml',
                    'results': {
                        'schema': {
                            'valid': True
                        },
                        'use_cases': {
                            DEFAULT_USE_CASE: {
                                'errors': [],
                                'warnings': [],
                            }
                        }
                    }
                },
                bad_file_result,
            ]
        }

        with patch('seed.building_sync.validation_client._validation_api_post', return_value=responseFactory(200, body)):
            all_files_valid, file_summaries = validate_use_case(self.zip_file)

        self.assertFalse(all_files_valid)
        bad_file_names = [f['file'] for f in file_summaries]
        self.assertEqual([bad_file_result['file']], bad_file_names)

    def test_validation_fails_when_one_file_fails_use_case(self):
        bad_file_result = {
            'file': 'bad.xml',
            'results': {
                'schema': {
                    'valid': True,
                },
                'use_cases': {
                    DEFAULT_USE_CASE: {
                        # Include a use case error
                        'errors': ['something was wrong'],
                        'warnings': [],
                    }
                }
            }
        }

        body = {
            'success': True,
            'schema_version': DEFAULT_SCHEMA_VERSION,
            'validation_results': [
                {
                    'file': 'file1.xml',
                    'results': {
                        'schema': {
                            'valid': True
                        },
                        'use_cases': {
                            DEFAULT_USE_CASE: {
                                'errors': [],
                                'warnings': [],
                            }
                        }
                    }
                },
                bad_file_result,
            ]
        }

        with patch('seed.building_sync.validation_client._validation_api_post', return_value=responseFactory(200, body)):
            all_files_valid, file_summaries = validate_use_case(self.zip_file)

        self.assertFalse(all_files_valid)
        bad_file_names = [f['file'] for f in file_summaries]
        self.assertEqual([bad_file_result['file']], bad_file_names)

    def test_validation_zip_file_ok_when_warnings(self):
        good_body = {
            'success': True,
            'schema_version': DEFAULT_SCHEMA_VERSION,
            'validation_results': [
                {
                    'file': 'file1.xml',
                    'results': {
                        'schema': {
                            'valid': True
                        },
                        'use_cases': {
                            DEFAULT_USE_CASE: {
                                'errors': [],
                                # Include a warning
                                'warnings': ['This is a warning!'],
                            }
                        }
                    }
                }, {
                    'file': 'file2.xml',
                    'results': {
                        'schema': {
                            'valid': True
                        },
                        'use_cases': {
                            DEFAULT_USE_CASE: {
                                'errors': [],
                                # Include a warning
                                'warnings': ['This is another warning!'],
                            }
                        }
                    }
                }
            ]
        }

        with patch('seed.building_sync.validation_client._validation_api_post', return_value=responseFactory(200, good_body)):
            all_files_valid, file_summaries = validate_use_case(self.zip_file)

        self.assertTrue(all_files_valid)
        file_names = [f['file'] for f in file_summaries]
        self.assertEqual(['file1.xml', 'file2.xml'], file_names)
