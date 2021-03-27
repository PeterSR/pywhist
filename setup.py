# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

setup(
    name="whist",
    version="0.1.0",
    description="A package containing the logic for the card game Whist and its variants.",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Peter Severin Rasmussen",
    author_email="git@petersr.com",
    url="https://github.com/PeterSR/pywhist",
    license="MIT License",
    packages=find_packages(exclude=("tests", "docs")),
    python_requires=">=3.7",
)
