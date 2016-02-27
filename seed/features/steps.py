# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

# TODO: Convert these to selenium tests
from salad.steps.everything import *
from lettuce import step
from django.core.urlresolvers import reverse


@step(u'I visit the home page')
def i_visit_the_home_page(step):
    world.browser.visit(django_url(reverse("seed:home")))


@step(u'I go to the jasmine unit tests for the SEED')
def given_i_go_to_the_jasmine_unit_tests_for_the_SEED(step):
    world.browser.visit(django_url(reverse("seed:angular_js_tests")))


@step(u'I should see that the tests passed')
def then_i_should_see_that_the_tests_passed(step):
    time.sleep(2)
    try:
        assert world.browser.is_element_present_by_css(".passingAlert.bar")
    except:
        time.sleep(50)
        assert len(world.browser.find_by_css(".passingAlert.bar")) > 0


@step(u'When I visit the projects page')
def when_i_visit_the_projects_page(step):
    world.browser.visit(django_url(reverse("seed:home")) + "#/projects")


@step(u'Then I should see my projects')
def then_i_should_see_my_projects(step):
    assert world.browser.is_text_present('Projects')
    assert world.browser.is_text_present('my project')


@step(u'And I have a project')
def and_i_have_a_project(step):
    Project.objects.create(
        name="my project",
        super_organization_id=world.org.id,
        owner=world.user
    )


@step(u'And I have a dataset')
def and_i_have_a_dataset(step):
    ImportRecord.objects.create(
        name='dataset 1',
        super_organization=world.org,
        owner=world.user
    )


@step(u'When I visit the dataset page')
def when_i_visit_the_dataset_page(step):
    world.browser.visit(django_url(reverse("seed:home")) + "#/data")


@step(u'And I delete a dataset')
def and_i_delete_a_dataset(step):
    delete_icon = world.browser.find_by_css('.delete_link')
    delete_icon.click()
    alert = world.browser.get_alert()
    alert.accept()


@step(u'Then I should see no datasets')
def then_i_should_see_no_datasets(step):
    number_of_datasets = len(world.browser.find_by_css('.import_row'))
    number_of_datasets = len(world.browser.find_by_css('.import_row'))
    number_of_datasets = len(world.browser.find_by_css('.import_row'))
    assert number_of_datasets == 0
