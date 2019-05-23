#!/usr/bin/env python
# -*- coding: ascii -*-

"""
A really simple client library for Krono's Workforce Telestaff


This software is licensed as described in the README.md and LICENSE
file, which you should have received as part of this distribution.

Changelog:
    - 2017-06-23 - Updated getRosterNameField to correctly 
                    parse notes from titles
    - 2017-10-07 - Update getMemberInfo to look for data-popup-status to have 
                    a value of "Request Pending" instead of the existance of 
                    a "request field"
    - 2017-12-04 - Updated parseCalendar to handle pending requests 
                    (isRequest)
    - 2018-02-08 - Updated doLogin to handle Contact Log Requests
    - 2018-02-08 - Updated parseWebstaffroster to check for roster 
                    lenght (make sure it is there before attempting to 
                    parse it)
    - 2018-03-12 - Updated getMemberInfo to handle formating workcodes 
                    from SVGs
    - 2018-06-12 - Refactored to be Object Oriented
    - 2018-07-26 - Update parsing of Telestaff to indicate nonWorking 
                    work codes
    - 2018-12-16 - Update URL handling to better encode dates
    - 2019-02-27 - Replaced requires with install_requires


"""

import sys
import codecs
try:
    from setuptools import setup, Command
except ImportError:
    from distutils.core import setup, Command

from festis import __version__

VERSION          = __version__
DESCRIPTION      = 'A tiny Python client for Workforce Telestaff.'
with codecs.open('README.md', 'r', encoding='UTF-8') as readme:
    LONG_DESCRIPTION = ''.join(readme)

CLASSIFIERS      = [ 'Intended Audience :: Developers',
                     'License :: OSI Approved :: MIT License',
                     'Programming Language :: Python',
                     'Programming Language :: Python :: 2.7',
                     'Programming Language :: Python :: 3.4',
                     'Programming Language :: Python :: 3.5',
                     'Programming Language :: Python :: 3.6',
                     'Programming Language :: Python :: 3.7',
                     'Topic :: Software Development :: Libraries :: Python Modules',
                   ]

REQUIREMENTS    = [
                    'beautifulsoup4==4.6.0',
                    'DateTime==4.2',
                    'requests==2.21.0',
                    'pyyaml>=4.2b1'
                ]

packages     = [ 'festis' ]

setup(
    name             = "festis",
    version          = VERSION,
    description      = DESCRIPTION,
    long_description = LONG_DESCRIPTION,
    long_description_content_type = "text/markdown",
    author       = 'Joe Porcelli',
    author_email = 'joe@kt3i.com',
    url          = 'http://github.com/porcej/festis',
    license      = 'MIT',
    platforms    = [ 'any' ],
    packages     = packages,
    install_requires     = REQUIREMENTS,
    classifiers  = CLASSIFIERS
)