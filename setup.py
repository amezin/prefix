import setuptools

setuptools.setup(
    name='prefix',
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    use_scm_version={'write_to': 'prefix/version.py'},
    setup_requires=['setuptools_scm', 'setuptools_scm_git_archive']
)
