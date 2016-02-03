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
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization


@step(u'I visit the landing page')
def i_visit_the_landing_page(step):
    world.browser.visit(django_url(reverse("landing:logout")))
    world.browser.visit(django_url(reverse("landing:landing_page")))


@step(u'I should see the login prompt')
def then_i_should_see_the_login_prompt(step):
    assert len(world.browser.find_by_css(".signup_form")) > 0


@step(u'And I am an exising user')
def and_i_am_an_exising_user(step):
    if not hasattr(world, 'user'):
        world.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_passS3',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        world.user = User.objects.create_user(**world.user_details)
        world.org = Organization.objects.create(name='my org')
        world.org.add_member(world.user)


@step(u'When I log into the system')
def when_i_log_into_the_system(step):
    world.browser.fill("email", world.user.email)
    world.browser.fill("password", world.user_details['password'])
    world.browser.find_by_css("input[type=submit]").click()


@step(u'Then I should be redirected to the home page')
def then_i_should_be_redirected_to_the_home_page(step):
    assert world.browser.is_element_present_by_css(".menu_toggle_container")


@step(u'When I try to log into the system with the wrong password')
def when_i_try_to_log_into_the_system_with_the_wrong_password(step):
    world.browser.fill("email", world.user.email)
    world.browser.fill("password", "the wrong password!!!")
    world.browser.find_by_css("input[type=submit]").click()


@step(u'Then I should see the text "([^"]*)"')
def then_i_should_see_the_text_group1(step, group1):
    assert world.browser.is_text_present(group1)


@step(u'Given I am logged in')
def given_i_am_logged_in(step):
    and_i_am_an_exising_user(step)
    world.browser.visit(django_url(reverse("landing:logout")))
    world.browser.visit(django_url(reverse("landing:landing_page")))
    when_i_log_into_the_system(step)

