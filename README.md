# festis

A small Python client library for Kronos Workforce Telestaff (HTML scraping + authenticated session handling).

## Prerequisites

Python 3.8+ is recommended. Install dependencies:

```bash
pip install -r requirements.txt
```

Optional: [requests-ntlm](https://github.com/requests/requests-ntlm) if Telestaff sits behind NTLM challenge-response authentication:

```bash
pip install requests-ntlm
```

## Installation

```bash
git clone https://github.com/porcej/festis.git
cd festis
pip install .
```

## Usage

```python
from festis import telestaff as ts

telestaff = ts.Telestaff(
    host="https://telestaff.example.org",
    t_user="...",
    t_pass="...",
    domain="...",
    d_user="...",
    d_pass="...",
    cookies=None,  # optional: "name=value; name2=value2" from a prior session
)

telestaff.do_login()
result = telestaff.get_telestaff(kind="roster", date=None)
# result is {"status_code": int, "data": ...}
cookies = telestaff.get_cookies()
```

See `sample.py` and `samplefile.py` for runnable examples.

## Development tests

```bash
pip install pytest
pytest
```

## Built with

- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) — HTML parsing
- [Requests](https://requests.readthedocs.io/) — HTTP session and cookies

## License

MIT — see the `LICENSE` file in this repository.
