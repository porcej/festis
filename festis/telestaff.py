
#!/usr/bin/env python
# -*- coding: ascii -*-

"""
Festis.telestaff: downloads data from telestaff


Changelog:
    - 2017-06-23 - Updated getRosterNameField to correctly 
                    parse notes from titles
    - 2017-10-07 - Update getMemberInfo to look for data-popup-status to have a value of "Request Pending" instead of the existance of a "request field"
    - 2017-12-04 - Updated parseCalendar to handle pending requests (isRequest)
    - 2018-02-08 - Updated do_login to handle Contact Log Requests
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
    - 2019-12-25 - Updated do_login to resepect the object's 'verify_ssl_cert' state
    - 2019-12-25 - Extracted all Telestaff Resource End Points to resource_url() method
    - 2019-12-25 - Added handler method that returns the parser for resource type requested
    =======================================================================================
    * 2019-12-25 - Moved to version 0.0.7
    - 2021-02-09 - Updated to Support WF 7.1.16
    - 2021-05-01 - corrected error in fetching picklist by quaoting keyboard picklist in resource_url call
    - 2021-09-02 - Added the ability to select picklist by chain
    - 2021-09-02 - Added full roster functionality
    - 2022-11-13 - Added position id
    =======================================================================================
    * 2024-10-30 - Moved to version 0.1.2

"""

__author__ = 'Joe Porcelli (porcej@gmail.com)'
__copyright__ = 'Copyright (c) 2024 Joe Porcelli'
__license__ = 'New-style BSD'
__vcs_id__ = '$Id$'
__version__ = '0.1.2' #Versioning: http://www.python.org/dev/peps/pep-0386/

import base64
from urllib.parse import urlparse

from requests import Session, RequestException, HTTPError, codes
from typing import Any, Callable, Dict, Optional, Union

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
# try: import simplejson as json
# except ImportError: import json


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
        'verify_ssl_cert': True,
        'cookies': {}
    }

    app = None
    logger = logging


    def __init__(self, host, 
                t_user=None, t_pass=None, cookies=None,
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

        if isinstance(cookies, str):
            self.set_cookies_from_string(cookies)

        # Initilize session object   
        self.session = Session()
        self.session.cookies.update(self.creds['cookies'])
        self.session.verify = self.creds['verify_ssl_cert']
        self.session.headers.update({'User-Agent': self.userAgent})


    def set_cookies_from_string(self, cookie_string: str) -> None:
        """
        Parses a cookie string and sets cookies in the credentials.

        Args:
            cookie_string (str): A string containing cookies in "key=value" pairs separated by semicolons.
                                 Example: "cookie1=value1; cookie2=value2"
        """
        # Initialize cookies dictionary if not already present
        self.creds.setdefault('cookies', {})

        # Split and add each cookie
        for cookie in cookie_string.split(';'):
            cookie_parts = cookie.strip().split('=', 1)
            if len(cookie_parts) == 2:
                key, value = cookie_parts
                self.creds['cookies'][key] = value


    def build_response_dict(self, status_code: int, data: Union[str, dict, list]) -> Dict[str, Union[int, str, dict, list]]:
        """
        Builds a response dictionary with a status code and data payload.

        Args:
            status_code (int): The HTTP status code of the response.
            data (Union[str, dict, list]): The data payload of the response, which can be a string, dictionary, or list.

        Returns:
            Dict[str, Union[int, str, dict, list]]: A dictionary containing the status code and data payload.
        """
        return {'status_code': status_code, 'data': data}


    def resource_url(self, resource_type: Optional[str] = None, date: Optional[str] = None) -> Union[str, bool]:
        """
        Constructs and returns the URL for a specified resource type and date.
        
        Args:
            resource_type (Optional[str]): The type of resource for which to get the URL (default is 'dashboard').
            date (Optional[str]): The date to include in the URL if applicable (default is the current date).

        Returns:
            Union[str, bool]: The full URL as a string if the resource type is known, otherwise `False`.
        """
        # Set default values if parameters are not provided
        resource_type = resource_type or 'dashboard'
        date = date or self.current_date()

        # URL paths by resource type
        urls = {
            'loginPage': '/login',
            'logout': '/logout',
            'login': '/processWebLogin',
            'contactLog': '/contactLog?myContactLog=true',
            'dispoContactLog': '/contactLog?dispositionedUnrespondedLogs=true',
            'pickList': f'/schedule/pickList/fromCalendar/{date}/675?returnUrl=%2Fcalendar%2F{date}%2F675',
            'customPickList': '/schedule/pickList/setPickListProperty',
            'pickListData': '/schedule/pickList/tableAjaxData',
            'roster': f'/roster/d%5B{date}%5D/',
            'rosterFull': f'/roster/d%5B{date}%5D?rosterViewId=-1_3',
            'calendar': f'/calendar/{date}/list/',
            'dashboard': '/calendar/dashboard'
        }

        # Retrieve the URL for the specified resource type, or return False if unknown
        resource_path = urls.get(resource_type)
        if not resource_path:
            return False

        return self.make_url(resource_path)

    def handler(self, kind: str = 'dashboard') -> Union[Callable, bool]:
        """
        Returns the appropriate handler function based on the provided `kind` value.

        Args:
            kind (str): The type of handler to retrieve (e.g., 'dashboard', 'roster').

        Returns:
            Union[Callable, bool]: The handler function if `kind` is known; otherwise, `False`.
        """
        handlers = {
            'dashboard': self.parse_calendar_dashboard,
            'roster': self.parse_web_staff_roster,
            'rosterFull': self.parse_web_staff_roster,
            'calendar': self.parse_full_calendar
        }

        return handlers.get(kind, False)


    def domain_user(self) -> str:
        """
        Combines `domain` and `domain_user` from credentials to form an auth-user string.

        Returns:
            str: The combined domain and user string (e.g., "example.comuser").
        """
        try:
            return self.creds['domain'] + self.creds['domain_user']
        except KeyError as e:
            raise KeyError(f"Missing credential key: {e}")


    def make_url(self, path: Optional[str] = None) -> str:
        """
        Constructs a full URL for Telestaff paths based on the base URL.

        Args:
            path (Optional[str]): The path to append to the base URL. If `None` or an empty string is provided,
                                  the base URL is returned.

        Returns:
            str: The constructed full URL.
        
        Example:
            If `self.url` is "https://example.com" and `path` is "login", this method returns "https://example.com/login".
        """
        # Return the base URL if no path is specified
        if not path:
            return self.url

        # Ensure path starts with a forward slash
        if not path.startswith('/'):
            path = '/' + path
        return self.url + path


    def current_date(self) -> str:
        """Returns the current date in 'YYYYMMDD' format."""
        return datetime.now().strftime('%Y%m%d')

    def clean_string(self, text: str) -> str:
        """
        Cleans a string by stripping whitespace and removing newline, carriage return, and tab characters.

        Args:
            text (str): The string to be cleaned.

        Returns:
            str: The cleaned string.
        """
        return text.strip().replace('\n', '').replace('\r', '').replace('\t', '')

    def get_clean_string(self, soup: BeautifulSoup, class_name: str, element: str = 'div') -> Union[str, bool]:
        """
        Returns a cleaned text string for the text content of the specified HTML element with the given class.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object containing the HTML.
            class_name (str): The class name to search for within the HTML element.
            element (str): The type of HTML element to search for (default is 'div').

        Returns:
            Union[str, bool]: The cleaned text string if found; otherwise, `False`.
        """
        try:
            target_element = soup.find(element, attrs={'class': class_name})
            return self.clean_string(target_element.text) if target_element else False
        except AttributeError:
            return False

    def get_roster_date(self, src: BeautifulSoup) -> Optional[str]:
        """
        Extracts and returns the text string for the current roster date from the given HTML source.

        Args:
            src (BeautifulSoup): The BeautifulSoup object containing the HTML source to search.

        Returns:
            Optional[str]: The text of the roster date if found, otherwise `None`.
        """
        try:
            date_div = src.find_all("div", {"class": "dateName"})[0]
            return date_div.span.text.strip() if date_div and date_div.span else None
        except (IndexError, AttributeError) as e:
            # Log or handle exception as needed
            logger.warning(f"Error extracting roster date: {e}")
            return None


    def get_roster_name_field(self, soup: BeautifulSoup) -> Dict[str, Union[str, bool]]:
        """
        Extracts and returns the name and notes for the Workforce Telestaff's name div.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object containing the HTML source.

        Returns:
            Dict[str, Union[str, bool]]: A dictionary containing the 'title', 'notes', and 'isSuppressed' status.
        """
        name_classes = ['dateName', 'organizationName', 'battalionName', 'shiftName', 'unitName', 'positionName']
        name_and_notes = {"title": '', "notes": '', "isSuppressed": False}

        # Locate the div with any of the specified classes
        tmp = soup.find("div", {"class": name_classes})

        if tmp:
            # Extract the title, falling back to 'positionNameText' if necessary
            title_span = tmp.span.text.strip() if tmp.span and tmp.span.text.strip() else tmp.find("span", {"class": 'positionNameText'}).text
            name_and_notes["title"] = title_span

            # Parse title span using regex
            match = re.search(r'^({?(\.)?[^{]*){?([^}]*)}?', title_span)
            if match and match.lastindex and match.lastindex > 1:
                name_and_notes["title"] = match.group(1).strip() if match.group(1) else name_and_notes["title"]
                name_and_notes['isSuppressed'] = bool(match.group(2))
                name_and_notes['notes'] = match.group(3).strip() if match.group(3) and not name_and_notes['isSuppressed'] else name_and_notes['notes']

        return name_and_notes

    #  ****************************************************************************
    #  Replaced on 2017/10/07 to accept telestaffs new pending status convention
    #  Updated on 2018/03/12 to handle workcode formating using SVG
    #  Updated on 2018/07/26 to handle nonWorking code and unassignedPosition code
    def get_member_info(self, soup: BeautifulSoup) -> Dict[str, Union[int, str, bool]]:
        """
        Extracts and returns member information from a Telestaff HTML element.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object containing the HTML source.

        Returns:
            Dict[str, Union[int, str, bool]]: A dictionary containing member information such as id, name,
                                               work code, shift times, and additional status flags.
        """
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

        # Extract the member ID
        data['id'] = soup.get('data-id', 0)

        # Check for non-working status
        if( soup.find('div', attrs={"class": 'nonWorking'})):
            data["isWorking"] = False

        # Check for assignment status
        if (soup.find('div', attrs={"class": "unassignedPosition"})):
            data['isAssigned'] = False

        # Check if the position is vacant
        if (soup.find('div', attrs={"class": 'vacancyDisplay'})):
            data['isVacant'] = True

        # Extract personal information
        resourceDisplay = soup.find("div", attrs={"data-field": "resourcedisplay"})
        if resourceDisplay.has_attr('data-popup-title'):
            data["name"] = resourceDisplay['data-popup-title']

        # Extract personal specialties
        if resourceDisplay.has_attr('data-popup-specialties'):
            data["specialties"] = resourceDisplay['data-popup-specialties']

        # Extract badge ID
        fid = soup.find("div", attrs={"data-field": "idcolumn"})
        if fid.has_attr("data-id"):
            data['badge'] = fid['data-id']

        # Extract work code information
        codes = soup.find("div", attrs={"data-field": "workcode"})
        if codes.has_attr('data-popup-title'):
            data['workcode'] = codes['data-popup-title']
            
            # Handle exception code styling
            styleSpan = codes.find('span', attrs={'class': 'exceptionCode'})
            if styleSpan.has_attr('style'):
                data['workcode_style'] = styleSpan['style']
                
            # Check for SVG style (supports different versions)
            rect = codes.find('svg', attrs={'class': 'svg'}).rect   # Support WF Telestaff 7.1.16
            if rect.has_attr('style'):
                data['workcode_style'] += "background-color: " + rect['style'].replace('fill:','')
            
            #         if codes.has_attr('style'):
            #             data['workcode_style'] = codes['style']

            # Check pending approval status
            if codes.has_attr('data-popup-statusenum'):
                data['isRequest'] =  codes['data-popup-statusenum'] == "APPROVAL_PENDING"


            # Support legacy request field
            if codes.has_attr('data-popup-request'):        
                data['isRequest'] = codes['data-popup-request']
            exceptCode = codes.find("span",  { "class" : "exceptionCode" })
            data["exceptioncode"] = exceptCode.text;

        # Extract work time information
        start_time = soup.find("div", attrs={"class": "shiftTimes", "data-popup-title": "From"})
        if start_time.has_attr('data-popup-value'):
            data['startTime'] = start_time['data-popup-value']

        end_time = soup.find("div", attrs={"class": "shiftTimes", "data-popup-title": "Through"})
        if end_time.has_attr('data-popup-value'):
            data['endTime'] = end_time['data-popup-value']

        duration = soup.find("div", attrs={"class": "shiftDuration"})
        if duration.has_attr('data-popup-value'):
            data['duration'] = duration['data-popup-value']

        return data


    def parse_roster(self, soup: BeautifulSoup, parent: str = "root") -> Dict[str, Any]:
        """
        Recursively parses a Workforce Telestaff roster, extracting group and member information.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object containing the HTML source.
            parent (str): The name of the parent group, default is "root".

        Returns:
            Dict[str, Any]: A dictionary containing parsed roster data, organized by group type.
        """
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
            groupData.update(self.get_roster_name_field(li))

            # Check if this is a person, if so look for more data
            if "Position" == li['class'][0][2:]:
                groupData.update(self.get_member_info(li))
            else:
                # Nope, not a person... lets see if there are any people hanging around here
                if li.find("li", {"class": idClasses}):
                    groupData.update(self.parse_roster(li, li['class'][0][2:]))
            
            data.setdefault(groupType, []).append(groupData)

        return data


    def parse_web_staff_roster(self, raw: str) -> Dict[str, Union[str, Dict]]:
        """
        Parses a raw HTML page to locate and parse the Telestaff roster.

        Args:
            raw (str): The raw HTML content of the Telestaff roster page.

        Returns:
            Dict[str, Union[str, Dict]]: A dictionary containing parsed roster data or an error message.
        """
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
        roster = self.parse_roster(soup)
        roster['type'] = 'roster'
        return roster


    # 12/4/2017 - Added pending field to event dictionary to repsent pending events
    def parse_calendar(self, soup):
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
                name = self.get_clean_string(eventsoup, class_name='listItemName')
                if name:
                    event['name'] = name

                # Get Event pending status (added 12/4/2017)
                if eventsoup.find('span', attrs={'class': 'glyphicon-asterisk'}):
                    event['isRequest'] = True

                # Get Event Location
                loc = self.get_clean_string(eventsoup, class_name='listItemWhere')
                if loc:
                    event['location'] = loc

                # Get Event Type
                if eventsoup.has_attr('data-attrtype'):
                    event['type'] = eventsoup['data-attrtype']

                # Get Event time as a range
                time = self.get_clean_string(eventsoup, class_name='listItemStartTime')
                if time:
                    event['time'] = time

                # Get Event length (typically in hours)
                length = self.get_clean_string(eventsoup, class_name='listItemHours')
                if length:
                    event['length'] = length

                code = self.get_clean_string(eventsoup, class_name="exception")
                if code:
                    event['exception-code'] = code

                # exceptionCode = self.get_clean_String(eventsoup, 'exception')
                # if exceptionCodeexception-code:
                #     event['exception-code'] = exceptionCode

                # # Get Event icon styling
                box = eventsoup.find('div', attrs={'class': 'listItemBox'})
                box = box.div

                if box.has_attr('style'):
                    event['icon_style'] = self.clean_string(box['style'])

                events.append(event)


            # Append the day's date and events as a dict to the days list
            daysData.append({ 'date': datetime.strptime(dateText, '%A, %B %d, %Y').strftime('%Y%m%d'),
                              'events': events
                            })
        return daysData


    def parse_full_calendar(self, raw: str) -> Dict[str, str]:
        """
        Takes a raw HTML page, finds and parses the Telestaff calendar details.

        Args:
            raw (str): The raw HTML content of the Telestaff calendar page.

        Returns:
            Dict[str, str]: A dictionary containing the parsed calendar data.
        """
        data = {'type': 'calendar'}

        # Create Soup Tree from HTML
        soup = BeautifulSoup(raw.encode('utf-8'), self.parser)

        # Extract header information
        header = self.get_clean_string(soup, class_name='listHeader')
        if header:
            match = re.search(r'\(([^)]*)\)?\s?([\S]*)[\D]*([^a-zA-Z]*)', header)
            if match:
                data['owner'] = match.group(1).strip() if match.group(1) else ''
                data["start"] = match.group(2).strip() if match.group(2) else ''
                data['end'] = match.group(3).strip() if match.group(3) else ''

        # Locate calendar content
        calendar_container = soup.find('div', attrs={'class': ['fullWidth', 'topMarginSmall']})
        if calendar_container:
            data['days'] = self.parse_calendar(calendar_container)
        else:
            data['days'] = []  # Default empty list if calendar days are not found

        return data


    def parse_calendar_dashboard(self, raw: str) -> Dict[str, str]:
        """
        Parses the HTML of the calendar dashboard, extracting the date range and daily data.

        Args:
            raw (str): The raw HTML content of the calendar dashboard page.

        Returns:
            Dict[str, str]: A dictionary containing the type, date range, and parsed days data.
        """
        data = {'type': 'dashboard'}
        
        # Create Soup Tree from HTML
        soup = BeautifulSoup(raw.encode('utf-8'), self.parser)

        # Pull out the date range for the calendar, handling possible missing elements
        date_range_element = soup.find("span", {"class": "dateRange"})
        if date_range_element:
            data['daterange'] = date_range_element.text.strip()
        else:
            data['daterange'] = 'Unknown'  # Default or placeholder if not found

        # Parse calendar days
        data['days'] = self.parse_calendar(soup)

        return data

    def do_login(self) -> Union[Dict[str, int], bool]:
        """
        Logs in to the application and returns a response with status code or False on failure.

        Returns:
            Union[Dict[str, int], bool]: Login response with 'status_code' on success, or `False` on failure.
        """
        try:
            # Initial login page request
            login_page_response = self.session.get(self.resource_url('loginPage'))

            # Handle NTLM authentication if necessary
            if login_page_response.status_code == codes.unauthorized and HttpNtlmAuth:
                self.session.auth = HttpNtlmAuth(self.domainUser(), self.creds['domain_pass'])
                login_page_response = self.session.get(self.resource_url('loginPage'))

            login_page_response.raise_for_status()


            # Check if login page was successfully retrieved
            if login_page_response.status_code != 200:
                data = f'Application error loging onto Teletsaff: {login_page_response.status_code}'
                return self.build_response_dict(500, data)

            # Extract CSRF token
            csrf_token = self.get_csrf_token(login_page_response)
            if not csrf_token:
                return False
            self.creds['telestaff']['CSRFToken'] = csrf_token

            # Submit login credentials
            login_response = self.session.post(self.resource_url('login'), data=self.creds['telestaff'])

            # Check for contact log disposition requirements
            if login_response.url.endswith('/checkContactLog'):
                self.session.get(self.resource_url('contactLog?myContactLog=true'))
                self.session.get(self.resource_url('contactLog?dispositionedUnrespondedLogs=true'))

            return self.build_response_dict(login_response.status_code, data)

        except HTTPError as e:
            return self.build_response_dict(500, "Login failed with HTTP Error: {e}")
        except RequestException as e:
            return self.build_response_dict(500, "Login failed with error: {e}")
            return {'status_code': f'Login failed with error {e}'}
        except Exception as e:
            return self.build_response_dict(500, "Login failed with unknown error: {e}")


    def do_logout(self) -> Union[Dict[str, int], bool]:
        """
        Logs out of the Telestaff application and returns a response with status code or False on failure.

        Returns:
            Union[Dict[str, int], bool]: Logout response with 'status_code' on success, or `False` on failure.
        """
        try:
            # Initial login page request
            logout_page_response = self.session.get(self.resource_url('logout'))

            logout_page_response.raise_for_status()
            if self.check_if_logged_out(logout_page_response.url):
                return self.build_response_dict(200, "Logged out")
        except HTTPError as e:
            return self.build_response_dict(500, "Logout failed with HTTP Error: {e}")
        except RequestException as e:
            return self.build_response_dict(500, "Logout failed with error: {e}")
            return {'status_code': f'Logout failed with error {e}'}
        except Exception as e:
            return self.build_response_dict(500, "Logout failed with unknown error: {e}")

    def check_if_logged_out(self, url: str) -> bool:
        """
        Checks if the given URL corresponds to the login page.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL matches the login page, False otherwise.
        """
        return urlparse(url).path == '/login'

    def get_csrf_token(self, page_response: 'requests.Response') -> Optional[str]:
        """
        Extracts CSRF token from the page response.

        Args:
            page_response (requests.Response): The response object containing the page HTML.

        Returns:
            Optional[str]: The CSRF token if found, otherwise `None`.
        """
        soup = BeautifulSoup(page_response.text.encode('utf-8'), self.parser)
        csrf_element = soup.find("input", {"name": "CSRFToken"})
        return csrf_element.get('value') if csrf_element else None


    def get_telestaff_data(self, path: str, handler: Callable[[str], Union[dict, str]]) -> Dict[str, Union[str, int]]:
        """
        Fetches Telestaff data, and processes it with a specified handler.

        Args:
            path (str): The URL path for the Telestaff data.
            handler (Callable[[str], Union[dict, str]]): A function to process the response text.

        Returns:
            Dict[str, Union[str, int]]: A dictionary with the status code and processed data or an error message.
        """
        try:
            response = self.session.get(path)
            response.raise_for_status()
            if self.check_if_logged_out(response.url):
                return self.build_response_dict(403, 'Telestaff username and password combination is incorrect.')
            return self.build_response_dict(response.status_code, handler(response.text))
        except HTTPError as e:
            return self.build_response_dict(response.status_code, e)
        except RequestException as e:
            return self.build_response_dict(500, e)


    def get_telestaff_calendar(self, date: Optional[str] = None) -> Union[str, dict]:
        """Fetches the Telestaff calendar data."""
        return self.get_telestaff(kind='calendar', date=date)


    def get_telestaff_roster(self, date: Optional[str] = None) -> Union[str, dict]:
        """Fetches the Telestaff roster data."""
        return self.get_telestaff(kind='roster', date=date)


    def get_telestaff_dashboard(self, date: Optional[str] = None) -> Union[str, dict]:
        """Fetches the Telestaff dashboard data."""
        return self.get_telestaff(kind='dashboard', date=date)


    def get_telestaff(self, kind: str = 'dashboard', date: Optional[str] = None, chain: Optional[str] = None) -> Union[str, dict]:
        """
        Retrieves Telestaff data of the specified type.

        Args:
            kind (str): The type of data to retrieve (default is 'dashboard').
            date (Optional[str]): The date for the data (default is `None`, meaning current date).
            json_export (bool): If `True`, returns JSON; otherwise, returns a data object (default is `True`).
            chain (Optional[str]): Chain parameter for specialized requests (applicable for picklists).

        Returns:
            Union[str, dict]: JSON-encoded string if `json_export` is `True`, otherwise a dictionary with data.
        """
        # Determine handler and action based on kind
        handler = self.parse_calendar_dashboard
        action = self.resource_url()

        # Handle different types of Telestaff data requests
        if kind == 'picklist':
            return self.get_telestaff_picklist(date, chain)
        
        action = self.resource_url(resource_type=kind, date=date)
        handler = self.handler(kind=kind)

        # Fetch data and return in the requested format
        return self.get_telestaff_data(action, handler)


    def get_telestaff_picklist(self, date: str = '', chain: Optional[str] = None) -> Union[Dict[str, Union[str, int]], str]:
        """
        Fetch a Telestaff picklist. If `chain` is provided, fetches a custom picklist.
        
        Args:
            date (str): The date for which to fetch the picklist.
            chain (Optional[str]): Custom chain parameter for specialized picklist retrieval.
            
        Returns:
            Union[Dict[str, Union[str, int]], str]: A dictionary with `status_code` and `data` or JSON-encoded string with picklist data.
        """
        # Set default date if none provided
        date = date or self.current_date()
        r_url = self.resource_url(resource_type='pickList', date=date)
        
        # Update session headers
        this_host = urlparse(self.url).hostname
        self.session.headers.update({
            'Host': this_host,
            'Referer': r_url,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        # Initial picklist request
        response = self.session.get(r_url)
        response.raise_for_status()  # Ensure request succeeded

        # If chain parameter is provided, fetch custom picklist
        if chain is not None:
            soup = BeautifulSoup(response.text, self.parser)
            picklist_data = {
                'date': soup.find("input", {"name": "date"}).get('value', ''),
                'regionTbl': soup.find("select", {"name": "regionTbl"}).find('option', selected=True).get('value', ''),
                'shiftTbl': soup.find("select", {"name": "shiftTbl"}).find('option', selected=True).get('value', ''),
                'strategyChainTbl': chain,
                'CSRFToken': soup.find("input", {"name": "CSRFToken"}).get('value', '')
            }
            
            # Submit the custom picklist request
            self.session.post(self.resource_url('customPickList'), data=picklist_data)

        # Fetch the final picklist data
        try:
            response = self.session.get(self.resource_url('pickListData'))
            response.raise_for_status()  # Check for successful data retrieval
            
            # Check if still logged in
            if response.url.endswith('login'):
                return {'status_code': 403, 'data': 'Username or password not found.'}

            # Process and return JSON data
            data = response.json()
            data['type'] = 'picklist'
            return self.build_response_dict(200, data)

        except requests.exceptions.RequestException as e:
            logging.warning(f"Error fetching picklist data: {e}")
            return self.build_response_dict(500, "Failed to retrieve picklist data: {e}")



