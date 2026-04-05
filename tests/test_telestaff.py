"""Lightweight tests for festis.telestaff (no network)."""

from festis.telestaff import Telestaff


def test_set_cookies_from_string_roundtrip():
    t = Telestaff(host='https://example.com')
    t.set_cookies_from_string('a=1; b=two')
    assert t.get_cookies() == {'a': '1', 'b': 'two'}


def test_domain_user_concat():
    t = Telestaff(host='https://example.com', domain='DOM', d_user='\\user')
    assert t.domain_user() == 'DOM\\user'
