from setuptools import setup, find_packages

setup(
    name='seed',
    version='0.1.0',
    packages=find_packages(),
    url='',
    license='revised BSD',
    author='Richard Brown',
    author_email='rebrown@lbl.gov',
    description='The SEED Platform is a web-based application that helps organizations easily manage data on the energy performance of large groups of buildings.',
    scripts=['bin/seedutil']
)
