#!/usr/bin/env python3

import setuptools
import sys


needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setuptools.setup(
    name='prefix',
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    setup_requires=pytest_runner,
    tests_require=['pytest']
)
