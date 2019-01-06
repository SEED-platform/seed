from setuptools import setup, find_packages

# TODO: This file can most likely be removed.

setup(
    name='seed',
    version='2.4.1',
    packages=find_packages(),
    url='',
    license='revised BSD',
    author='Richard Brown',
    author_email='rebrown@lbl.gov',
    description='The SEED Platform is a web-based application that helps organizations easily manage data on the energy performance of large groups of buildings.',
    scripts=['bin/seedutil']
)
