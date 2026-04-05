#!/usr/bin/env python
# -*- coding: ascii -*-

"""
Festis.telestaff: downloads data from telestaff
"""

import importlib

__author__ = 'Joe Porcelli (porcej@gmail.com)'
__copyright__ = 'Copyright (c) 2017 Joe Porcelli'
__license__ = 'New-style BSD'
__vcs_id__ = '$Id$'

from festis._version import __version__

__all__ = ['__version__', 'telestaff']


def __getattr__(name):
    """Lazy-load telestaff so `pip install` / setuptools never import requests pre-install."""
    if name == 'telestaff':
        return importlib.import_module('.telestaff', __name__)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
