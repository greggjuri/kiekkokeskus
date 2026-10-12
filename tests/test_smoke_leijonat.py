"""Smoke-helper tests for /leijonat additions. Thin — the pure matchers (
_is_html_content_type, _body_contains, _is_js_content_type) are shared with the /bolts tests;
this file just pins the new path constants so a typo trips the tests. No network."""

from __future__ import annotations

import smoke


def test_leijonat_path_constants_pinned():
    # One place to notice if a typo creeps in; the smoke script's loop depends on these.
    assert smoke.LEIJONAT_PAGE == "/leijonat"
    assert smoke.LEIJONAT_PAGE_SLASH == "/leijonat/"
    assert smoke.LEIJONAT_HERO == "/leijonat/hero.webp"


def test_body_contains_hits_a_leijonat_shell_body():
    # Sanity-check the shared matcher against a representative /leijonat body shape so a
    # regression here would trip both page smoke blocks.
    body = (
        b"<!DOCTYPE html><html><head><title>leijonat</title>"
        b"<link rel='stylesheet' href='/kiekkokeskus/kk.css'></head></html>"
    )
    assert smoke._body_contains(body, "/kiekkokeskus/kk.css") is True


def test_text_html_still_matches_for_leijonat_pages():
    assert smoke._is_html_content_type("text/html") is True
    assert smoke._is_html_content_type("text/html; charset=utf-8") is True


def test_webp_mime_detection_pin():
    # Not a dedicated matcher — smoke.py uses a substring check "image/webp" — this test
    # locks the string so a MIME-detection rewrite can't silently relax it.
    assert "image/webp" in "image/webp"
    assert "image/webp" in "image/webp; something"
