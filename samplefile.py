#!/usr/bin/env python
# -*- coding: ascii -*-

"""
Sample App to demonstrage dumping a festis roster to file

Changelog:
    - 2018-12-16 - Initial Commit

"""

__author__ = "Joseph Porcelli (porcej@gmail.com)"
__version__ = "0.0.1"
__copyright__ = "Copyright (c) 2018 Joseph Porcelli"
__license__ = "MIT"

import os
import sys
import logging
import json
from festis import telestaff as ts



# Here we handle some command line input funkyness
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input


TS_DOMAIN = os.environ.get('TS_DOMAIN') or 'NTLM DOMAIN FOR AUTHENTICATION'
TS_SERVER = os.environ.get('TS_SERVER') or 'TELESTAFF URL'

TS_USER = os.environ.get('TS_USER') or 'TELESTAFF USER'
TS_PASS = os.environ.get('TS_PASS') or 'TELESTAFF PASSWORD'
D_USER = os.environ.get('D_USER') or 'DOMAIN USER'
D_PASS = os.environ.get('D_PASS') or 'DOMAIN USER PASSWORD'
date = None


if __name__ == '__main__':
    telestaff = ts.Telestaff(host=TS_SERVER,  \
                                t_user=TS_USER, \
                                t_pass=TS_PASS, \
                                domain=TS_DOMAIN,  \
                                d_user=D_USER, \
                                d_pass=D_PASS)

    with open('roster.json', 'w') as jfh:
        json.dump(telestaff.getTelestaff(kind='roster', date=date, jsonExport=True ), jfh)


