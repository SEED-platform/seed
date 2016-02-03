"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.core.management import call_command
from django.test.simple import DjangoTestSuiteRunner

from lettuce import after, before, step, world
from splinter.browser import Browser
from logging import getLogger
from selenium import webdriver

try:
	from south.management.commands import patch_for_test_db_setup
except:
	pass

logger = getLogger(__name__)
logger.info("Loading the terrain file...")

@before.runserver
def setup_database(actual_server):
	'''
	This will setup your database, sync it, and run migrations if you are using South.
	It does this before the Test Django server is set up.
	'''
	logger.info("Setting up a test database...")

	# Uncomment if you are using South
	patch_for_test_db_setup()

	world.test_runner = DjangoTestSuiteRunner(interactive=False)
	DjangoTestSuiteRunner.setup_test_environment(world.test_runner)
	world.created_db = DjangoTestSuiteRunner.setup_databases(world.test_runner)

	call_command('syncdb', interactive=False, verbosity=0)

	# Uncomment if you are using South
	call_command('migrate', interactive=False, verbosity=0)


@before.all
def setup_browser():
	world.browser = Browser('chrome')
