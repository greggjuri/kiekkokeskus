"""Smoke-helper tests for /bolts additions. No network — just the pure matchers."""

from __future__ import annotations

import smoke

# --- _is_html_content_type ---


def test_text_html_accepted():
    assert smoke._is_html_content_type("text/html") is True


def test_text_html_with_charset_accepted():
    assert smoke._is_html_content_type("text/html; charset=utf-8") is True


def test_case_insensitive_html():
    assert smoke._is_html_content_type("TEXT/HTML") is True


def test_text_plain_rejected_for_html():
    assert smoke._is_html_content_type("text/plain") is False


def test_application_octet_rejected_for_html():
    assert smoke._is_html_content_type("application/octet-stream") is False


# --- _body_contains ---


def test_body_contains_hits_the_shared_stylesheet_link():
    body = b"<html><head><link href='/kiekkokeskus/kk.css'></head></html>"
    assert smoke._body_contains(body, "/kiekkokeskus/kk.css") is True


def test_body_contains_case_insensitive():
    body = b"<HTML><HEAD><LINK HREF='/KIEKKOKESKUS/KK.CSS'></HEAD></HTML>"
    assert smoke._body_contains(body, "/kiekkokeskus/kk.css") is True


def test_body_contains_rejects_absent_substring():
    body = b"<html><head></head></html>"
    assert smoke._body_contains(body, "/kiekkokeskus/kk.css") is False


def test_body_contains_invalid_utf8_returns_false():
    assert smoke._body_contains(b"\xff\xfe\xfd", "needle") is False
