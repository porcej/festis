#!/usr/bin/env python
# -*- coding: ascii -*-

"""
Sample app: log in, fetch roster, write JSON to roster.json

Changelog:
    - 2018-12-16 - Initial Commit

"""

__author__ = "Joseph Porcelli (porcej@gmail.com)"
__version__ = "0.0.1"
__copyright__ = "Copyright (c) 2018 Joseph Porcelli"
__license__ = "MIT"

import os
import json
from festis import telestaff as ts


TS_DOMAIN = os.environ.get('TS_DOMAIN') or 'NTLM DOMAIN FOR AUTHENTICATION'
TS_SERVER = os.environ.get('TS_SERVER') or 'https://telestaff.example.org'

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

    telestaff.do_login()

    with open('roster.json', 'w') as jfh:
        json.dump(telestaff.get_telestaff(kind='roster', date=date), jfh, indent=2)
