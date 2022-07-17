import json

from setuptools import find_packages, setup


def get_version():
    with open('package.json') as f:
        j = json.load(f)

    return j['version']


setup(
    name='seed',
    version=get_version(),
    packages=find_packages(),
    url='seed-platform.org',
    license='revised BSD',
    author='NREL/LBNL',
    author_email='info@seed-platform.org',
    description='The SEED Platform is a web-based application that helps organizations easily manage data on the energy performance of large groups of buildings.',
)
