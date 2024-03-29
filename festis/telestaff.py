
#!/usr/bin/env python
# -*- coding: ascii -*-

"""
Festis.telestaff: downlaods data from telestaff


Changelog:
    - 2017-06-23 - Updated getRosterNameField to correctly 
                    parse notes from titles
    - 2017-10-07 - Update getMemberInfo to look for data-popup-status to have a value of "Request Pending" instead of the existance of a "request field"
    - 2017-12-04 - Updated parseCalendar to handle pending requests (isRequest)
    - 2018-02-08 - Updated doLogin to handle Contact Log Requests
    - 2018-02-08 - Updated parseWebstaffroster to check for roster lenght (make sure it is there before attempting to parse it)
    - 2018-03-12 - Updated getMemberInfo to handle formating workcodes from SVGs
    - 2018-06-12 - Refactored to be Object Oriented
    - 2018-07-26 - Update parsing of Telestaff to indicate nonWorking work codes
    - 2018-12-16 - Update URL handling to better encode dates
    - 2018-12-16 - Added logging support
    - 2018-12-16 - Changed how position title is obtained in WT 6.7.0
    - 2018-12-17 - Added a flag to the init option to control SSL Cert Verification
    - 2018-12-25 - Updated handling for invalid domain credentials
    - 2018-12-25 - Updated several typos
    - 2019-05-23 - Updated getRosterNameField to remove etra status and make the regex more efficient
    - 2019-05-23 - Updated getTelestaffPicklist to handle picklists outside the default
    - 2019-12-25 - Updated doLogin to resepect the object's 'verify_ssl_cert' state
    - 2019-12-25 - Extracted all Telestaff Resource End Points to resourceURL() method
    - 2019-12-25 - Added handler method that returns the parser for resource type requested
    =======================================================================================
    * 2019-12-25 - Moved to version 0.0.7
    - 2021-02-09 - Updated to Support WF 7.1.16
    - 2021-05-01 - corrected error in fetching picklist by quaoting keyboard picklist in resourceURL call
    - 2021-09-02 - Added the ability to select picklist by chain
    - 2021-09-02 - Added full roster functionality
    - 2022-11-13 - Added position id


"""

__author__ = 'Joe Porcelli (porcej@gmail.com)'
__copyright__ = 'Copyright (c) 2017 Joe Porcelli'
__license__ = 'New-style BSD'
__vcs_id__ = '$Id$'
__version__ = '0.1.0' #Versioning: http://www.python.org/dev/peps/pep-0386/


import urllib, base64, requests

# Optionally import requests_ntlm for the case where
# NTLM auth is not requeired
try: from requests_ntlm import HttpNtlmAuth
except ImportError: HttpNtlmAuth = None
from bs4 import BeautifulSoup
from datetime import datetime
import re
import yaml
import logging


# Import JSON... Try Simple if its available and default to stdlib
try: import simplejson as json
except ImportError: import json


class Telestaff():
    """
    A really simple client for Kronos's Workforce Telestaff
    """

    parser = 'html.parser'
    url = None
    domain = None
    session = None
    userAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
    creds = {
        'telestaff': {
            'username': '',
            'password': ''
        },
        'domain': '',
        'domain_user': '',
        'domain_pass': '',
        'verify_ssl_cert': True
    }

    app = None
    logger = logging


    def __init__(self, host, 
                t_user=None, t_pass=None, 
                domain=None, d_user=None, d_pass=None,
                verify_ssl_cert=True, app=None):
        """
        Initilize Telestaff Client
        """

        if app:
            self.app = app
            self.logger=app.logger


        # We will attempt to us lxml parser... 
        #     but we will fail back to html.parser just incase
        try:
            from lxml import html
            self.parser = 'lxml'
        except ImportError: 
            self.parser = 'html.parser'

        self.url = host

        # Initialize connection parameters
        self.creds['telestaff']['username'] = t_user
        self.creds['telestaff']['password'] = t_pass
        self.creds['domain'] = domain
        self.creds['domain_user'] = d_user
        self.creds['domain_pass'] = d_pass
        self.creds['verify_ssl_cert'] = verify_ssl_cert

        # Initilize session object   
        self.session = requests.Session()
        self.session.verify = self.creds['verify_ssl_cert']
        self.session.headers.update({'User-Agent': self.userAgent})


    def resourceURL(self, resource_type=None, date=None):
        """
        Accepts optional resource_type (string) and date (string)
        and returns a string representation of that resource's url
        Defaults:
            resource_type: 'dashboard'
            date: The current date
        Returns false for unknown resource types
        """

        # If resourse is not provided assume dashboard
        if resource_type is None:
            resource_type = 'dashboard'

        # If date is not provided, assume today
        if date is None:
            date = self.currentDate()

        urls = {
            'loginPage':        '/login',
            'login':            '/processWebLogin',
            'contactLog':       '/contactLog?myContactLog=true',
            'dispoContactLog':  '/contactLog?dispositionedUnrespondedLogs=true',
            'pickList':         '/schedule/pickList/fromCalendar/' + date + '/675?returnUrl=%2Fcalendar%2F'+ date + '%2F675',
            'customPickList':   '/schedule/pickList/setPickListProperty',
            'pickListData':     '/schedule/pickList/tableAjaxData',
            'roster':           '/roster/d%5B' + date + '%5D/',
            'rosterFull':       '/roster/d%5B' + date + '%5D?rosterViewId=-1_3',
            'calendar':         '/calendar/' + date + '/list/',
            'dashboard':        '/calendar/dashboard'
        }

        if resource_type not in urls.keys():
            return False

        return self.makeURL(urls[resource_type])

    def handler(self, kind='dashboard'):
        """
        Accepts a handler name and returns a link to its handler
        if the handler is unknown, returns false
        """
        if kind == 'dashboard':
            return self.parseCalendarDashboard
        elif kind == 'roster':
            return self.parseWebStaffRoster
        elif kind == 'rosterFull':
            return self.parseWebStaffRoster
        elif kind == 'calendar':
            return self.parseFullCalendar
        else:
            return False


    def domainUser(self):
        """
        Mashes Authdomain and user to form auth-user
        """
        return self.creds['domain'] + self.creds['domain_user'];


    def makeURL(self, path=''):
        """
        Build URL's for Telestaff Paths
        """
        if path == '':
            return self.url

        if not path.startswith('/'):
            path = '/' + path
        return self.url + path


    def currentDate(self):
        return datetime.now().strftime('%Y%m%d')

    def cleanString(self, str):
        return str.strip().replace('\n', '').replace('\r', '').replace('\t', '')

    def getcleanString(self, soup, cls, elm='div'):
        """Returns a clean text string for text componet of the elm with class cls"""
        try:
            return self.cleanString(soup.find(elm, attrs={'class': cls}).text)
        except:
            return False


    def getRosterDate(self, src):
        """Returns the text string for current roster date from Workforce Telstaff 5.4.5.2"""
        return src.findAll("div", { "class" : "dateName" })[0].span.text


    def getRosterNameField(self, soup):
        """Returns name and notes for Workforce Telestaff's Name Div"""
        nameClasses = ['dateName', 'organizationName', 'battalionName', 'shiftName', 'unitName', 'positionName']
        nameAndNotes = {"title": '', "notes":'', "isSurrpressed": False}
        
        tmp = soup.find("div", {"class": nameClasses})

        if tmp:
            if tmp.span.text.strip():
                titleSpan = tmp.span.text.strip()
            else:
                titleSpan = tmp.find("span", {"class": 'positionNameText'}).text

            nameAndNotes["title"] = titleSpan

            m = re.search('^({?(\.)?[^{]*){?([^}]*)}?', titleSpan)
            if m.lastindex and m.lastindex > 1:
                if m.group(1):
                    nameAndNotes["title"] = m.group(1).strip()
                if m.group(2):
                    nameAndNotes['isSurrpressed'] = True
                if m.group(3):
                    if not nameAndNotes['isSurrpressed']:
                        nameAndNotes['notes'] = m.group(3).strip()

        return nameAndNotes

    #  ****************************************************************************
    #  Replaced on 2017/10/07 to accept telestaffs new pending status convention
    # def getMemberInfo(soup):
    #     data = {"name": "", "specialties": "", "badge": "", "workcode": "", "exceptioncode": "", "isRequest": False, "startTime": "", "endTime": "", "duration": 24}

    #     # Get Personal Info
    #     resourceDisplay = soup.find("div", attrs={"data-field": "resourcedisplay"})
    #     if resourceDisplay.has_attr('data-popup-title'):
    #         data["name"] = resourceDisplay['data-popup-title']

    #     if resourceDisplay.has_attr('data-popup-specialties'):
    #         data["specialties"] = resourceDisplay['data-popup-specialties']

    #     fid = soup.find("div", attrs={"data-field": "idcolumn"})
    #     if fid.has_attr("data-id"):
    #         data['badge'] = fid['data-id']

    #     # Get Work Code Info
    #     codes = soup.find("div", attrs={"data-field": "workcode"})
    #     if codes.has_attr('data-popup-title'):
    #         data['workcode'] = codes['data-popup-title']
    #         if codes.has_attr('style'):
    #             data['workcode_style'] = codes['style']
    #         if codes.has_attr('data-popup-request'):
    #             data['isRequest'] = codes['data-popup-request']
    #         exceptCode = codes.find("span",  { "class" : "exceptionCode" })
    #         data["exceptioncode"] = exceptCode.text;

    #     # Get work time info
    #     times = soup.find("div", attrs={"class": "shiftTimes", "data-popup-title": "From"})
    #     if times.has_attr('data-popup-value'):
    #         data['startTime'] = times['data-popup-value']

    #     times = soup.find("div", attrs={"class": "shiftTimes", "data-popup-title": "Through"})
    #     if times.has_attr('data-popup-value'):
    #         data['endTime'] = times['data-popup-value']

    #     times = soup.find("div", attrs={"class": "shiftDuration"})
    #     if times.has_attr('data-popup-value'):
    #         data['duration'] = times['data-popup-value']

    #     return data

    #  ****************************************************************************
    #  Replaced on 2017/10/07 to accept telestaffs new pending status convention
    #  Updated on 2018/03/12 to handle workcode formating using SVG
    #  Updated on 2018/07/26 to handle nonWorking code and unassignedPosition code
    def getMemberInfo(self, soup):
        data = {"id": 0, 
                "name": "", 
                "specialties": "", 
                "badge": "", 
                "workcode": "", 
                "exceptioncode": "", 
                "isRequest": False, 
                "startTime": "", 
                "endTime": "", 
                "duration": 24, 
                "isWorking": True, 
                "isAssigned": True,
                "isVacant": False}

        data['id'] = soup['data-id']

        # Look for nonWorking Code
        if( soup.find('div', attrs={"class": 'nonWorking'})):
            data["isWorking"] = False

        # Look for isAssigned 
        if (soup.find('div', attrs={"class": "unassignedPosition"})):
            data['isAssigned'] = False

        # Is this position vacant?
        if (soup.find('div', attrs={"class": 'vacancyDisplay'})):
            data['isVacant'] = True

        # Get Personal Info
        resourceDisplay = soup.find("div", attrs={"data-field": "resourcedisplay"})
        if resourceDisplay.has_attr('data-popup-title'):
            data["name"] = resourceDisplay['data-popup-title']

        if resourceDisplay.has_attr('data-popup-specialties'):
            data["specialties"] = resourceDisplay['data-popup-specialties']

        fid = soup.find("div", attrs={"data-field": "idcolumn"})
        if fid.has_attr("data-id"):
            data['badge'] = fid['data-id']

        # Get Work Code Info
        codes = soup.find("div", attrs={"data-field": "workcode"})
        if codes.has_attr('data-popup-title'):
            data['workcode'] = codes['data-popup-title']
            
            # Added on 2018/03/12 to handle formating iconogrpahy
            styleSpan = codes.find('span', attrs={'class': 'exceptionCode'})
            if styleSpan.has_attr('style'):
                data['workcode_style'] = styleSpan['style']
                
            # rect = codes.find('svg', attrs={'class': 'rosterSvg'}).rect 
            rect = codes.find('svg', attrs={'class': 'svg'}).rect   # Support WF Telestaff 7.1.16
            if rect.has_attr('style'):
                data['workcode_style'] += "background-color: " + rect['style'].replace('fill:','')
            
            #         if codes.has_attr('style'):
            #             data['workcode_style'] = codes['style']

            # Added on 2017-`0-07 to deal with new status field and the removal of the request field
            if codes.has_attr('data-popup-statusenum'):
                data['isRequest'] =  codes['data-popup-statusenum'] == "APPROVAL_PENDING"


            # Still support the old telestaff request field
            if codes.has_attr('data-popup-request'):        
                data['isRequest'] = codes['data-popup-request']
            exceptCode = codes.find("span",  { "class" : "exceptionCode" })
            data["exceptioncode"] = exceptCode.text;

        # Get work time info
        times = soup.find("div", attrs={"class": "shiftTimes", "data-popup-title": "From"})
        if times.has_attr('data-popup-value'):
            data['startTime'] = times['data-popup-value']

        times = soup.find("div", attrs={"class": "shiftTimes", "data-popup-title": "Through"})
        if times.has_attr('data-popup-value'):
            data['endTime'] = times['data-popup-value']

        times = soup.find("div", attrs={"class": "shiftDuration"})
        if times.has_attr('data-popup-value'):
            data['duration'] = times['data-popup-value']

        return data


    def parseRoster(self, soup, parent="root"):
        """Recursivly parses a Workforce Telestaff Roster"""
        # Dict object to hold data
        data = {}
        idClasses = ['idDate', 'idInstitution', 'idAgency', 'idBatallion', 'idShift', 'idStation', 'idUnit', 'idPosition']

        # Find the first data class
        first_li = soup.find("li", {"class": idClasses})

        # Now that we have the first class, find all of that class's siblings (same level)
        # lis = [dateLi] + dateLi.find_all("li", {"class": idClasses})
        lis = [first_li] + first_li.find_next_siblings('li', {'class': idClasses})

        # return getRosterNameField(first_li)['title']

        # Loop over the first class and all of it's siblings, we will look for people,
        #    or, optionally, look deeper in the tree for people
        for li in lis:

            groupType = li['class'][0][2:]
            groupData = {}
            groupData.update(self.getRosterNameField(li))

            # Check if this is a person, if so look for more data
            if "Position" == li['class'][0][2:]:
                groupData.update(self.getMemberInfo(li))
            else:
                # Nope, not a person... lets see if there are any people hanging around here
                if li.find("li", {"class": idClasses}):
                    groupData.update(self.parseRoster(li, li['class'][0][2:]))
            
            data.setdefault(groupType, []).append(groupData)

        return data


    def parseWebStaffRoster(self, raw):
        """"Takes a raw HTML page, finds Telestaff Roster and Parses it"""

        # Create Soup Tree from HTML
        soup = BeautifulSoup(raw.encode('utf-8'), self.parser)

        # Find roster in soup tree and through away everything else
        soup = soup.findAll("ol", {"class": "rosterTableList"})

        #
        if (len(soup) > 0):
            soup = soup[0]
        else:
            return {'error': 'No roster found'}

        # And now we parse the roster...
        roster = self.parseRoster(soup)
        roster['type'] = 'roster'
        return roster


    # 12/4/2017 - Added pending field to event dictionary to repsent pending events
    def parseCalendar(self, soup):
        """"Takes a raw HTML page, finds Telestaff Calendar and parses it"""
        daysData = []

        # Next we find days and loop over them
        days = soup.findAll("div", {'class': "calendarDay"})
        for day in days:
            # Get the date for the day
            dateText = day.find('div', attrs={'class': 'dateDiv'}).text.strip()

            # Find all the events for that day and loop over them
            eventssoup = day.find_all('div', attrs={'class': 'listItem'})

            events = []
            for eventsoup in eventssoup:
                # Initilize a dict to hold events, if we don't have a type for it, we assume it an unknown
                event = {'type': 'unknown', 'isRequest': False}

                # Get Event Name
                name = self.getcleanString(eventsoup, 'listItemName')
                if name:
                    event['name'] = name

                # Get Event pending status (added 12/4/2017)
                if eventsoup.find('span', attrs={'class': 'glyphicon-asterisk'}):
                    event['isRequest'] = True

                # Get Event Location
                loc = self.getcleanString(eventsoup, 'listItemWhere')
                if loc:
                    event['location'] = loc

                # Get Event Type
                if eventsoup.has_attr('data-attrtype'):
                    event['type'] = eventsoup['data-attrtype']

                # Get Event time as a range
                time = self.getcleanString(eventsoup, 'listItemStartTime')
                if time:
                    event['time'] = time

                # Get Event length (typically in hours)
                length = self.getcleanString(eventsoup, 'listItemHours')
                if length:
                    event['length'] = length

                code = self.getcleanString(eventsoup, "exception")
                if code:
                    event['exception-code'] = code

                # exceptionCode = self.getcleanString(eventsoup, 'exception')
                # if exceptionCodeexception-code:
                #     event['exception-code'] = exceptionCode

                # # Get Event icon styling
                box = eventsoup.find('div', attrs={'class': 'listItemBox'})
                box = box.div

                if box.has_attr('style'):
                    event['icon_style'] = self.cleanString(box['style'])

                events.append(event)


            # Append the day's date and events as a dict to the days list
            daysData.append({ 'date': datetime.strptime(dateText, '%A, %B %d, %Y').strftime('%Y%m%d'),
                              'events': events
                            })
        return daysData

    def parseFullCalendar(self, raw):
        """"Takes a raw HTML page, finds Telestaff Calendar and parses it"""
        data = {'type': 'calendar'}

        # Create Soup Tree from HTML
        soup = BeautifulSoup(raw.encode('utf-8'), self.parser)

        header = self.getcleanString(soup, cls='listHeader')
        if header:
            m = re.search('\(([^)]*)\)?\s?([\S]*)[\D]*([^a-zA-Z]*)', header)
            if m.group(1):
                data['owner'] = m.group(1).strip()
            if m.group(2):
                data["start"] = m.group(2).strip()
            if m.group(3):
                data['end'] = m.group(3).strip()
        soup.find({'class': ["centerContainer", "fullWidth", "topMargin"]})
        soup = soup.find('div', attrs={'class': ['fullWidth', 'topMarginSmall']})
        data['days'] = self.parseCalendar(soup)
        return data

    def parseCalendarDashboard(self, raw):
        data = {'type': 'dashboard'}

        # Create Soup Tree from HTML
        soup = BeautifulSoup(raw.encode('utf-8'), self.parser)

        # Pull out the daterange for the calendar
        data['daterange'] = soup.find("span", {"class": "dateRange"}).text.strip()
        data['days'] = self.parseCalendar(soup)

        return data

    # Logs in and returns session object... if login fails returns false
    def doLogin(self):

        # Holder for HTTP response codes
        login = { 'status_code': '403' }

        # Updated 25/12/2019
        # Removed verify=True, as this is done in the session.verify statement above
        loginPage = self.session.get(self.resourceURL('loginPage'));

        # Added 3/5/2018 
        # This fails to NTLM Auth if an unathorized error is received
        # Updated on 16/12/2018 - cleaned up NTLM Auth
        if (loginPage.status_code == 401) and (HttpNtlmAuth is not None):
            
            # Build NTLM Authenication Object
            self.session.auth = HttpNtlmAuth( \
                                             self.domainUser(),\
                                             self.creds['domain_pass'])

            loginPage = self.session.get(self.resourceURL('loginPage'));
            
        if (loginPage.status_code != 200):
            login['status_code'] = loginPage.status_code
            return login

        soup = BeautifulSoup(loginPage.text.encode('utf-8'), self.parser)
        
        # Find the token in soup tree and through away everything else
        self.creds['telestaff']['CSRFToken'] = \
                soup.find("input", {"name": "CSRFToken"}).get('value');
        

        # Login in to Workforce Telestaff
        # 28-12-2019 - Changed login location from login to processWebLogin
        loginResponse = self.session.post( self.resourceURL('login'), \
                                           data=self.creds['telestaff'])
        #   loginResponse = login['session'].post(makeURL('/login'), data=payload)
        
        # Added 2/8/2018 to handle Check Contact Log Messages
        # We simply check if we are on the checkContactLog page
        #    If we have a checkContactLog page then we must:
        #        Firstly) View Contact Log (/contactLog?myContactLog=true)
        #        Secondly) Disposition Unresponded logs (/contactLog?dispositionedUnrespondedLogs=true)
        # If we are we request to disposition the contact log for this session 
        if (loginResponse.url.endswith('/checkContactLog')):
            contactResponse = self.session.get(self.resourceURL('contectLog'))
            loginResponse = self.session.get(self.resourceURL('dispoContactLog'))
        
        login['status_code'] = loginResponse.status_code

        return login


    def getTelestaffData(self, path, handler):

        login = self.doLogin()

        # Check to see if login suceceed:
        if (login['status_code'] == requests.codes.ok):

            response = self.session.get(path)

            if (response.status_code == requests.codes.ok):
                if (not response.url.endswith('login')):
                    return {'status_code': response.status_code, 'data': handler(response.text)}
                else:
                    return {'status_code': '403', 'data': 'Telestaff username and password combination not.'}
            else:
                return {'status_code': response.status_code}
        else:
            return {'status_code': str(login['status_code']), 'data': str(login) }
        return {'status_code': '403', 'data': 'Authentication or authorization issue. Code--: ' + str(login['status_code']) + '.' }


    def getTelestaffCalendar(self, date=None, jsonExport=False):
        return self.getTelestaff(kind='calendar', date=date, jsonExport=jsonExport)


    def getTelestaffRoster(self, date=None, jsonExport=False):
        return self.getTelestaff(kind='roster', date=date, jsonExport=jsonExport)


    def getTelestaffDashboard(self, date=None, jsonExport=False):
        return self.getTelestaff(kind='dashboard', date=None, jsonExport=jsonExport)


    def getTelestaff(self, kind='dashboard', date=None, jsonExport=True, chain=None):
        """
        Gets Data from telestaff of type kind
        If jsonExport is true, returns Json, otherwise returns data object
        Defaults:
            kind - Dashboard
            date - None
        """
        handler = self.parseCalendarDashboard
        action = self.resourceURL()

        if  kind == 'picklist':
            return self.getTelestaffPicklist(date, chain)
        else:
            action = self.resourceURL(resource_type=kind, date=date)
            handler = self.handler(kind=kind)

        if jsonExport:
            return json.dumps(self.getTelestaffData(action, handler))
        return self.getTelestaffData(action, handler)


    def getTelestaffPicklist(self, date='', chain=None):
        """
        Fetch a Telestaff picklist.
        If picklist is None, fetchs default picklist else fetches listed picklist
        """

        # Authenticate against the system and establish a session
        login = self.doLogin()
        if (login['status_code'] == requests.codes.ok):

            if not date:
                date = self.currentDate()
            thisHost = urllib.parse.urlparse(self.url).hostname

            rURL = self.resourceURL(resource_type='pickList', date=date)
            self.session.headers.update({
                    'Host': thisHost,
                    'Referer': rURL,
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'XMLHttpRequest'
                })

            response = self.session.get(rURL)

            if chain is not None:
                picklist = {}
                soup = BeautifulSoup(response.text.encode('utf-8'), self.parser)
                picklist['date'] = soup.find("input", {"name": "date"}).get('value')
                picklist['regionTbl'] = soup.find("select", {"name": "regionTbl"}).find('option', selected=True).get('value')
                picklist['shiftTbl'] = soup.find("select", {"name": "shiftTbl"}).find('option', selected=True).get('value')
                picklist['strategyChainTbl'] = chain
                picklist['CSRFToken'] = soup.find("input", {"name": "CSRFToken"}).get('value');

                response = self.session.post(self.resourceURL('customPickList'), data=picklist)

            response = self.session.get(self.resourceURL('pickListData'))

            
            if (response.status_code == requests.codes.ok):
                if (not response.url.endswith('login')):
                    # rjson = handler(response.text)
                    data = response.json();
                    data['type'] = 'picklist';
                    return json.dumps({'status_code': '200', 'data': data})
                else:
                    return {'status_code': '403', 'data': 'Username or password not found.'}
            else:
                return {'status_code': response.status_code}
        return {'status_code': '403', 'data': 'Authentication or authorization issue. Code: ' + str(login['status_code']) + '.' }



