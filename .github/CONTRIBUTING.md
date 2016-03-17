General Information
===================

You can contribute to the SEED-platform project in many ways: by using the
software, reporting issues, contributing documentation, or contributing
code back to the project. The GitHub [Contributing to Open Source](https://guides.github.com/activities/contributing-to-open-source/#contributing) guide provides a good overview.

This wiki provides a quick overview of the software. Full documentation is
available at http://seed-platform.readthedocs.org.

If you find a bug, report it in the GitHub [issue tracker](https://github.com/SEED-platform/seed/issues)
for this repository.

Questions and discussion about the code are handled on the
[seed-platform-dev](https://groups.google.com/forum/?hl=en#!forum/seed-platform-dev)
google group. Please discuss your ideas there before embarking on any
significant coding effort.

You may also want to join the [seed-platform-users](https://groups.google.com/forum/?hl=en#!forum/seed-platform-users)
google group, which is a forum for users of SEED-platform to ask questions and
get support, as well as a place for general announcements about the project.

**Software Contributor Approval Process**

To be approved as a SEED-Platform Affiliate, software contributors must follow
this process:
* Fork the SEED-Platform Source Code
* Create a feature branch in the local repository
* Follow [coding standards](https://github.com/SEED-platform/seed/wiki/Coding-Standards) and testing requirements: patches should pass existing tests and provide new tests if needed, along with adequate documentation.
* Agree to the software contribution terms: The SEED-platform project does not currently have a contributor license agreement. Developers who contribute code to this project will retain the copyright in their work and at the same time grant permission for LBNL to distribute the software under the [modified BSD license](https://github.com/SEED-platform/seed/blob/master/LICENSE) contained in this repository. Note that LBNL cannot accept into the project any code licensed under GPL, Apache 2, or other similarly restrictive licenses. If you wish to contribute code under any license other than the LBNL modified BSD license, please contact the [LBNL team](seed-support@lists.lbl.gov) ahead of time so we can determine the acceptability of that license.
* Commit your changes
* Create a new [Pull Request](https://help.github.com/articles/creating-a-pull-request/) against SEED-Platform’s develop branch
* Check on the continuous integration test results in your pull request to verify that it successfully passed all the CI tests.
* Complete a code review, if requested
* Code contribution must be a significant feature addition or bug fix, and be accepted into the Master (stable) branch of SEED-Platform, in order to be officially recognized as a SEED-Platform Affiliate.


Coding Standards
----------------

For the portions of the app in python/django, follow the
[Django Coding Guidelines](https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/).

These are basically PEP 8 (the standard Python coding conventions), with a
few minor alterations (line length, etc.). Run Flake8 to ensure that your code
follows the PEP8 standard.

For the portions of SEED written in Javascript, please try to follow Douglas
Crockford's [guide](http://javascript.crockford.com/code.html).

Note: do not use tabs for indentation in non-Python files; the unit of
indentation should be 4 spaces.
