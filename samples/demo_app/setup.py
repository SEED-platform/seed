#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:copyright: (c) 2014 Building Energy Inc
"""
from setuptools import setup, find_packages

setup(
    name='stats',
    version='0.0.1',
    description='stats demo app',
    long_description=open('README.md').read(),
    author='Aleck Landgraf',
    author_email='aleck.landgraf@buildingenergy.com',
    url='http://github.com/buildingenergy/seed_demo_app',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
         'django<1.7',
         'django-annoying',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
