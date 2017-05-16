"""setup.py file."""

import uuid

from pip.req import parse_requirements

from setuptools import find_packages, setup

__author__ = 'Colin Silcock <colin@neticulate.co.uk>'

install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name="napalm-asa",
    version="0.1.0",
    packages=find_packages(),
    author="Colin Silcock",
    author_email="colin@neticulate.co.uk",
    description="Network Automation and Programmability Abstraction Layer with Multivendor support",
    classifiers=[
        'Topic :: Utilities',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
    ],
    url="https://github.com/napalm-automation/napalm-asa",
    include_package_data=True,
    install_requires=reqs,
)
