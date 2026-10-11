"""Smoke helper tests: content-type matcher accepts the module-script MIME variants and
rejects everything else. No network — _get() is unused here."""

from __future__ import annotations

import smoke


def test_text_javascript_accepted():
    assert smoke._is_js_content_type("text/javascript") is True


def test_text_javascript_with_charset_accepted():
    assert smoke._is_js_content_type("text/javascript; charset=utf-8") is True


def test_application_javascript_accepted():
    assert smoke._is_js_content_type("application/javascript") is True


def test_application_javascript_with_charset_accepted():
    assert smoke._is_js_content_type("application/javascript; charset=UTF-8") is True


def test_case_insensitive():
    assert smoke._is_js_content_type("TEXT/JAVASCRIPT") is True


def test_text_plain_rejected():
    assert smoke._is_js_content_type("text/plain") is False


def test_text_html_rejected():
    # The known-bad case: S3 served HTML MIME type for a .js object. Module script would refuse.
    assert smoke._is_js_content_type("text/html") is False


def test_empty_rejected():
    assert smoke._is_js_content_type("") is False
