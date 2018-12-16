# festis

A really simple python client library for Workforce Telestaff.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

This module is designed to work with `Python 3.4+`.  `Python 2` may work, your milage may very.  The `requirements.txt` file contains the required libraries.  

```
python3.4+
$pip install -r requirements.txt
```


### Optional Prerequisites

The python [requests-ntlm](https://github.com/requests/requests-ntlm) module can optionally be used to authenticate with Workforce Telestaff installations behind a NTLM Challenge-Response authorization mechanizm.  

```

pip install requests_ntlm

``` 


### Installation

This package can be installed from github:

```
$ git clone http://github.com/porcej/festis
$ cd festis
$ python3 setup.py install
```

### Removal


```
$ pip uninstall festis
```

### Usage

#### Using this module in your application

Import the telestaff class from the festis module
```
from festis import telestaff as ts
```



Initilize a telestaff object and request the desired data 

```
telestaff = ts.Telestaff(host=current_app.config['TS_SERVER'],  \
                                    t_user=current_app.config['TS_USER'], \
                                    t_pass=current_app.config['TS_PASS'], \
                                    domain=current_app.config['TS_DOMAIN'],  \
                                    d_user=current_app.config['D_USER'], \
                                    d_pass=current_app.config['D_PASS'])

telestaff.getTelestaff(kind='roster', date=date, jsonExport=True)
```


### Sample applicaitons

#### sample.py

The sample applicaiton, `sample.py` demonstrates using a911 to pretty print alert data to the screen.  

```
Usage: sample.py [options]

Options:
  -h, --help                show this help message and exit
  -q, --quiet               set logging to ERROR
  -d, --debug               set logging to DEBUG
  -v, --verbose             set logging to COMM
  -a AREG, --aid=AREG       Active911 Registration ID
```


#### samplefile.py
The example applicaiton, `samplefile.py` demonstrates using a911's Active911 class to save alert messages as json files in a predefined directory.

```
Usage: samplefile.py [options]

Options:
  -h, --help            show this help message and exit
  -q, --quiet           set logging to ERROR
  -d, --debug           set logging to DEBUG
  -v, --verbose         set logging to COMM
  -a AREG, --aid=AREG   Active911 Registration ID
  -p OPATH, --path=OPATH
                        Output directory
```


## Built With

* [Anaconda Python](https://conda.io/) - The python framework
* [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) - Screen Scraping
* [Requests](http://docs.python-requests.org/en/master/) - Request and session handling

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/porcej/cc71497a2b455f27bca8c879731e68dc) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/porcej/a911_bridge/tags). 

## Authors

* **Joseph Porcelli** - *Initial work* - [porcej](https://github.com/porcej)

See also the list of [contributors](https://github.com/porcej/a911_bridge/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

