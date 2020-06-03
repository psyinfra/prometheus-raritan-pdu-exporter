#!/usr/bin/env python

from setuptools import setup, find_packages

try:
    import pypandoc
    long_description = pypandoc.convert(readme, 'rst')

except (ImportError, OSError) as exc:
    print('WARNING: pypandoc failed to import or threw an error while '
          'converting README.md to RST: %s .md version will be used as is'
          % exc)
    long_description = open(readme).read()

setup(
    name='raritan_exporter',
    version='1.0',
    python_requires='>=3.7.3',
    description='Prometheus exporter for Raritan PDUs',
    long_description=long_description,
    url='https://github.com/inm7/raritan_exporter',
    author='Niels Reuter',
    author_email='niels.reuter@gmail.com',
    license='Apache',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'prometheus_client>=0.6.0',
        'jsonrpcclient>=3.3.6'
    ],
    extras_require={
        'devel-docs': [
            # for converting README.md -> .rst for long description
            'pypandoc',
        ],
    },
)
