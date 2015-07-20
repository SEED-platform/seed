"""
:copyright: (c) 2014 Building Energy Inc
"""
"""
Utility methods pertaining to data import tasks.
"""
import datetime

from django.core.exceptions import ValidationError
from django.core.cache import cache

def get_core_pk_column(table_column_mappings, primary_field):
	for tcm in table_column_mappings:
		if tcm.destination_field == primary_field:
			return tcm.order - 1
	raise ValidationError("This file doesn't appear to contain a column mapping to %s" % primary_field)


def get_or_create_core_model_from_row(app, Model, row_data, table_column_mappings):
	"""
	Given a row from a CSV, get the corresponding
	"""
	data = get_model_data_for_row(app, Model, row_data, table_column_mappings)
	site, created = PrimaryModel.objects.get_or_create(pk=site_pk)
	return site
					
					
def get_model_data_for_row(app, Model, row_data, table_column_mappings):
	values = {}
	
	for tcm in table_column_mappings:
		CurrentModel = get_model(app, tcm.destination_model)

		if Model != CurrentModel:
			continue
		
		uncoerced_value = row[tcm.order-1]
		if uncoerced_value == '':
			continue #skip this cell, no meaningful data
		
		values[tcm.destination] = uncoerced_value
	
	return values


def acquire_lock(name, expiration=None):
    """
    Tries to acquire a lock from the cache.
    Also sets the lock's value to the current time, allowing us to see how long
    it has been held.

    Returns False if lock already belongs by another process.
    """
    return cache.add(name, datetime.datetime.now(), expiration)

def release_lock(name):
    """
    Frees a lock.
    """
    return cache.delete(name)

def get_lock_time(name):
    """
    Examines a lock to see when it was acquired.
    """
    return cache.get(name)

def chunk_iterable(iter, chunk_size):  
    """
    Breaks an iterable (e.g. list) into smaller iterables,
    returning a generator of said iterables.
    """
    assert hasattr(iter, "__iter__"), "iter is not an iterable"  
    for i in xrange(0, len(iter), chunk_size):  
        yield iter[i:i + chunk_size]  

		
		
class CoercionRobot(object):
	
	def __init__(self):
		self.values_hash = {}
		
	def lookup_hash(self, uncoerced_value, destination_model, destination_field):
		key = self.make_key(uncoerced_value, destination_model, destination_field)
		if key in self.values_hash:
			return self.values_hash[key]
		return None
		
	def make_key(self, value, model, field):
		return "%s|%s|%s" % (value, model,field)
					
	
	
	
	
	
	
	
	
	
	
	
	
