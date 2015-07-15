"""
Unit tests for map.py
"""
__author__ = 'Dan Gunter <dkgunter@lbl.gov>'
__date__ = '2/13/15'

import json
from StringIO import StringIO

import pytest
from seed.common import mapper


@pytest.fixture
def jsonfile():
    return _jsonfile()

def _jsonfile():
    d = {"Key1": "value1",
     "key2": "value2",
     "has spaces": "value3",
     "has_underscores": "value4",
     "has  multi spaces": "value5",
     "has___multi  underscores": "value6",
     "normal ft2": "value7",
     "caret ft2": "value8",
     "super ft2": "value9"
     }
    for key in d:
        d[key] = [d[key], {mapper.Mapping.META_BEDES: True,
                           mapper.Mapping.META_TYPE: 'string'}]
    return StringIO(json.dumps(d))

def test_mapping_init(jsonfile):
    with pytest.raises(Exception):
        mapper.Mapping(None)
    m = mapper.Mapping(jsonfile)
    assert m

def test_mapping_regex(jsonfile):
    m = mapper.Mapping(jsonfile, regex=True)
    assert m['.*1'].field == "value1"

def test_mapping_case(jsonfile):
    m = mapper.Mapping(jsonfile, ignore_case=True)
    assert m['key1'].field == "value1"
    assert m['KEY1'].field == "value1"
    m = mapper.Mapping(_jsonfile(), ignore_case=True, regex=True)
    assert m["K..1"].field == "value1"

def test_mapping_spc(jsonfile):
    m = mapper.Mapping(jsonfile)
    assert m['has_spaces'].field == 'value3'
    assert m['has spaces'].field == 'value3'
    assert m['has underscores'].field == 'value4'
    assert m['has_multi spaces'].field == 'value5'
    assert m['has_multi underscores'].field == 'value6'

def test_units(jsonfile):
    m = mapper.Mapping(jsonfile, encoding='latin_1')
    assert m['normal ft2'].field == 'value7'
    assert m['caret ft^2'].field == 'value8'
    assert m['super ft_'].field == 'value9'
    assert m[(u"super ft" + u'\u00B2').encode('latin_1')].field == 'value9'

def test_mapping_conf():
    conf = mapper.MappingConfiguration()
    pm_mapping = conf.pm((1,0))
    assert isinstance(pm_mapping, mapper.Mapping)

def test_mapping_pm_bedes():
    expected = {"Address 1": "Address Line 1",
                "Property ID": "PM Property ID",
                "Portfolio Manager Property ID":
                    "Portfolio Manager Property Identifier"}
    pm = mapper.get_pm_mapping("1.0", expected.keys())
    for src, tgt in expected.items():
        assert pm[src].field == tgt
        assert pm[src].is_bedes == True