#!/usr/bin/env python

import codecs
import os
import re
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

def read(*parts):
    # intentionally *not* adding an encoding option to open
    return codecs.open(os.path.join(HERE, *parts), 'r').read()


setup(
    name='encyc-tng',
    version = read('..', 'VERSION'),
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points='',
)
