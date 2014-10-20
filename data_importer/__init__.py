"""
:copyright: (c) 2014 Building Energy Inc
"""
##### monkey-patch to suppress threading error message in python 2.7.3
##### See http://stackoverflow.com/questions/13193278/understand-python-threading-bug
import sys
if sys.version_info[:3] == (2, 7, 3):
    import threading
    threading._DummyThread._Thread__stop = lambda x: 42
#####
