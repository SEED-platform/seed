# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Dan Gunter <dkgunter@lbl.gov>'
"""
"""
Test API calls for mapping.
"""

import json

#import pytest
import requests

# init
host, port = '127.0.0.1', 8000
url_template = "http://{host}:{port:d}/app/create_pm_mapping/"
url = url_template.format(host=host, port=port)
user, apikey = 'admin@my.org', 'DEADBEEF'
auth = {'authorization': '{}:{}'.format(user, apikey)}

def get_mapping(columns):
    body = json.dumps({'columns': columns})
    r = requests.post(url, data=body, headers=auth)
    return r.json()


def test_empty():
    result = get_mapping([])
    assert result['success']
    assert len(result['mapping']) == 0

def test_basic():
    cids = ['Custom Property ID {:d} - ID'.format(i) for i in (1,2,3)]
    addrs = ['Address {:d}'.format(i) for i in (1,2)]
    result = get_mapping(cids + addrs)
    assert result['success']
    mapped_names = {}
    for col in result['mapping']:
        mapped_names[col[0]] = col[1]
    expected = {'Address 2': 'Premises Street Additional Info'}
    for k, v in expected.items():
        assert mapped_names[k] == expected[k]

def test_nodata():
    r = requests.post(url, data="{}", headers=auth)
    assert r.json()['success'] == False

