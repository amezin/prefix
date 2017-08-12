import setuptools
import sys

setup_requires = ['setuptools_scm', 'setuptools_scm_git_archive']

if {'pytest', 'test', 'ptr'}.intersection(sys.argv[1:]):
    setup_requires.append('pytest-runner')

tests_require = ['pytest']

setuptools.setup(
    name='prefix',
    packages=setuptools.find_packages(exclude=['tests']),
    python_requires='>=3.6',
    use_scm_version={'write_to': 'prefix/version.py'},
    setup_requires=setup_requires,
    tests_require=tests_require,
    extras_require={
        'testing': tests_require
    },
    entry_points={
        'console_scripts': ['prefix=prefix.cli:parse_args']
    }
)
