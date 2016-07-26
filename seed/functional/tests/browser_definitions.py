# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA

..note::
    This should be periodically checked against
    https://wiki.saucelabs.com/display/DOCS/Platform+Configurator#/
    for newer browser versions etc and updated accordingly.

    See README.rst for details on how to define additional browsers

:author Paul Munday<paul@paulmunday.net>
 """
from collections import namedtuple
import os

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

################################################################################
#                            WARNING! HACK ALERT                               #
#                                                                              #
#   There's a bug with Firefox version >= 47.0 that prevents the Selenium      #
#   webdriver from working: https://github.com/SeleniumHQ/selenium/issues/2110 #
#   There is a fix coming:                                                     #
#   https://developer.mozilla.org/en-US/docs/Mozilla/QA/Marionette/WebDriver   #
#   In the meantime you can manually install it to get things working.         #
#   It will need to be on the sytem search path e.g. /usr/local/bin/wires      #
#                                                                              #
#   N.B it will need to be named wires not geckodriver                         #
#                                                                              #
#   The following is a hack to detect the browser version and check to see     #
#   if Marionette is installed and if so, use it.                              #
#                                                                              #
#   It should be removed when the upstream fix lands. Check if to see          #
#   if it has landed if your browser version > 47.0                            #
#                                                                              #
################################################################################

from distutils.spawn import find_executable
import errno
import subprocess

try:
    ENOPKG = errno.ENOPKG
except AttributeError:
    errno.ENOPKG = 65

FIREFOX_IS_BROKEN = False
HAS_MARIONETTE = False

# Assume tests are being ran locally.
if not os.getenv('TRAVIS') == 'true':
    HAS_MARIONETTE = find_executable('wires')
    THIS_PATH = os.path.dirname(os.path.realpath(__file__))
    THIS_FILE = os.path.join(THIS_PATH, 'browser_definitions.py')

    FIREFOX_BINARY = find_executable('firefox')
    if not FIREFOX_BINARY:
        print "Can't find Firefox!"
        errmsg = (
            "Can't find Firefox! Please ensure it is on $PATH"
            "or somewhere it can be found.See: {}".format(THIS_FILE)
        )
        raise EnvironmentError(errno.ENOPKG, errmsg)
    FIREFOX_VERSION = subprocess.check_output(
        [FIREFOX_BINARY, '--version']).rstrip().split()[-1]

    FIREFOX_IS_BROKEN = FIREFOX_VERSION >= '47.0'
    print "HAS MARIONETTE: {}".format(HAS_MARIONETTE)
    print "FIREFOX VERSION is: {}".format(FIREFOX_VERSION)

    if FIREFOX_IS_BROKEN and not HAS_MARIONETTE:
        errmsg = os.strerror(errno.ENOPKG)
        errmsg += ': Marionette. See: {}'.format(THIS_FILE)
        raise EnvironmentError(errno.ENOPKG, errmsg)

################################################################################
#                                    HACK ENDS                                 #
################################################################################


def get_firefox_webdriver():
    # leave this, it disables the reader view popup
    # which can break tests
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.reader.detectedFirstArticle", True)
    profile.set_preference("browser.reader.parse-on-load.enabled", False)
    profile.set_preference("browser.startup.homepage_override.mstone", "ignore")
    profile.set_preference("startup.homepage_welcome_url.additional",
                           "about:blank")
    profile.update_preferences()
    # This can be removed if hack is not longer needed
    if FIREFOX_IS_BROKEN and HAS_MARIONETTE:
        caps = DesiredCapabilities.FIREFOX
        caps["marionette"] = True
        caps["binary"] = find_executable('firefox')
        driver = webdriver.Firefox(capabilities=caps, firefox_profile=profile)
    else:
        driver = webdriver.Firefox(firefox_profile=profile)
    return driver


# N.B. driver must be the name of the webdriver not an instance
# e.g. webdriver.Chrome *not* webdriver.Chrome()
BrowserDefinition = namedtuple(
    'BrowserDefinition', ['name', 'capabilities', 'driver'])

BrowserCap = namedtuple(
    'BrowserCap',
    ['valid_platforms', 'valid_versions']     # list, dict
)

# Define constants for browser capability definitions
MAX_VERSIONS = {
    'Firefox': {
        'Linux': 45,
        'Windows XP': 45,
        'other': 46,
    },
    'Chrome': {
        'Linux': 48,
        'Windows XP': 49,
        'OS X 10.8': 49,
        'other': 51,
    },
}

MIN_VERSIONS = {
    'Chrome': 27,
    'Firefox': 4,
}

WINDOWS_VERSIONS = [
    'Windows 10', 'Windows 8.1', 'Windows 8', 'Windows 7', 'Windows XP'
]
OS_X_VERSIONS = [
    'OS X 10.11', 'OS X 10.10', 'OS X 10.9', 'OS X 10.8'
]

ALL_PLATFORMS = WINDOWS_VERSIONS + OS_X_VERSIONS + ['Linux']


def get_valid_versions(browser, platform):
    """Helper method for generating BrowserCap named tuples."""
    max_version = MAX_VERSIONS[browser].get(platform)
    if not max_version:
        max_version = MAX_VERSIONS[browser]['other']
    min_version = MIN_VERSIONS[browser]
    valid_versions = [
        "{}.0".format(i) for i in range(max_version, min_version - 1, -1)
    ]
    valid_versions.extend(['latest'])
    if platform != 'Linux' or platform != 'Windows XP':
        valid_versions.extend(['dev', 'beta'])
    return valid_versions


FIREFOX_CAP = BrowserCap(
    ALL_PLATFORMS,
    {platform: get_valid_versions('Firefox', platform)
     for platform in ALL_PLATFORMS}
)

CHROME_CAP = BrowserCap(
    ALL_PLATFORMS,
    {platform: get_valid_versions('Chrome', platform)
     for platform in ALL_PLATFORMS}
)

SAFARI_CAP = BrowserCap(
    OS_X_VERSIONS,
    {platform: "{}.0".format(9 - OS_X_VERSIONS.index(platform)) for
     platform in OS_X_VERSIONS}
)

IE_CAP = BrowserCap(
    WINDOWS_VERSIONS,
    {
        'Windows 10': ['11.103'],
        'Windows 8.1': ['11.0'],
        'Windows 8': ['10.0'],
        'Windows 7': ['11.0', '10.0', '9.0', '8.0'],
        'Windows XP': ['8.0', '7.0', '6.0'],
    }
)

BROWSER_CAPABILITIES = {
    'Firefox': FIREFOX_CAP,
    'Chrome': CHROME_CAP,
    'Safari': SAFARI_CAP,
    'Internet Explorer': IE_CAP,
}

SELENIUM_VERSION = '2.52.0'


def browser_cap_factory(browser_name, version=None, platform=None, **kw):
    """
    Browser Capabilites Factory.

    Factory function to produce a Browser Capabilites dictionary.
    By default it will use the latest browser version and platform will be set
    to a current version (OS X or appropriate). Javascript is enabled by
    default but can be overridden by supplying javascriptEnabled as a keyword.
    Version can be supplied as string or integer. Postive integers will be
    transformed into a browser string e.g. 44 -> '44.0'. Negative integers are
    used to set a version before the lastest e.g. -l > latest but one.
    The browser, browser version and platform will be checked for capability.
    Either of the platform or version may be overridden. If only one
    is supplied this will take precendence, otherwise platform  will.

    If you wish to test against a mobile browser you must supply
    the platform and version.

    See: https://wiki.saucelabs.com/display/DOCS/Platform+Configurator#/
    & https://wiki.saucelabs.com/display/DOCS/Desired+Capabilities+Required+for+Selenium+and+Appium+Tests
    for more information on what can be set.

    :param browser_name: Name of browser one of Firefox, Chrome, Safari etc
    :param version: Desired browser version.
    :param platform:  Desired OS for the browser to run on.
    :type browser_name: string
    :type version: int or string
    :type platform: string
    :returns: dictionary
    """
    if version and type(version) != str and type(version) != int:
        print browser_name, 'version', version, type(version)
        raise TypeError('version must be a string or int if supplied')
    version, platform = validate_browser(browser_name, version, platform)
    capabilities = {
        'browserName': 'MicrosoftEdge' if browser_name == 'Microsoft Edge' else browser_name.lower(),
        'platform': platform,
        'version': version,
        'loggingPrefs': {'browser': 'ALL'},
    }
    if SELENIUM_VERSION in globals():
        capabilities['selenium-version'] = SELENIUM_VERSION
    if browser_name.lower() not in ['edge', 'htmlunit']:
        capabilities['javascriptEnabled'] = True
    capabilities.update(kw)
    return capabilities


def validate_browser(browser_name, version, platform):
    """Ensure  version and platform are valid for browser."""
    if browser_name == 'Microsoft Edge':
        version = '13.10586'
        platform = 'Windows 10'
    elif browser_name in ['Firefox', 'Chrome', 'Internet Explorer', 'Safari']:
        version, platform = validate_details(browser_name, version, platform)
    if not version or not platform:
        msg = "Unable to determine correct version and platform for {}".format(
            browser_name)
        msg += '. These must be supplied in this instance'
        raise ValueError(msg)
    return version, platform


def validate_details(browser, version, platform):
    """Ensure version and platform match browser."""
    capacities = BROWSER_CAPABILITIES[browser]
    if not platform:
        platform = capacities.valid_platforms[0]
    if browser in ['Firefox', 'Chrome']:
        if not version:
            version = 'latest'
        elif type(version) == int and version < 0:
            version = "latest{}".format(version)
    elif not version:
            version = capacities.valid_versions[platform][0]
    if type(version) == int:
        if version < 0:
            n = -version
            try:
                version = capacities.valid_versions[platform][n]
            except IndexError:
                version = 'not available'
        else:
            version = "{}.0".format(version)
    if version not in capacities.valid_versions[platform]:
        msg = "Version or platform  mismatch "
        msg += "Browser:{}  Version:{} Platform()".format(
            browser, version, platform)
        raise ValueError(msg)
    return version, platform


# BROWSER DEFINITIONS

FIREFOX = BrowserDefinition(
    'Firefox', browser_cap_factory('Firefox'), get_firefox_webdriver
)

CHROME = BrowserDefinition(
    'Chrome', browser_cap_factory('Chrome'), webdriver.Chrome
)

IE = BrowserDefinition(
    'Internet Explorer', browser_cap_factory('Internet Explorer'),
    webdriver.Ie
)

IE10 = BrowserDefinition(
    'Internet Explorer',
    browser_cap_factory('Internet Explorer', version=10, platform='Windows 8'),
    webdriver.Ie
)

SAFARI = BrowserDefinition(
    'Safari', browser_cap_factory('Safari'), webdriver.Safari
)

EDGE = BrowserDefinition(
    'Microsoft Edge', browser_cap_factory('Microsoft Edge'), webdriver.Edge
)

# Create Browser definitions list

# tests running on Travis, Sauce Labs and BrowserCapabilities will be used
if os.getenv('TRAVIS') == 'true':
    # IE removed as set_cookies does not work
    # see: https://support.saucelabs.com/customer/en/portal/articles/2014444-error---unable-to-add-cookie-to-page-in-ie-  # NOQA
    BROWSERS = [FIREFOX, CHROME]               # IE,  IE10, SAFARI, EDGE]
else:
    # tests running locally, we might want to do os detection at some point
    # for now use only cross platform browsers
    BROWSERS = [FIREFOX, CHROME]
    # allow browsers to be added locally
    if os.getenv('SEED_TEST_BROWSER'):
        BROWSERS.append(os.getenv('SEED_TEST_BROWSER'))
