# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='whist',
    version='0.1.0',
    description='A package containing the logic for the card game Whist and its variants.',
    long_description=readme,
    author='Peter Severin Rasmussen',
    author_email='git@petersr.com',
    url='https://github.com/PeterSR/pywhist',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
