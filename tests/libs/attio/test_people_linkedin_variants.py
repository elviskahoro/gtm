from __future__ import annotations

from libs.attio.people import _linkedin_url_variants  # pyright: ignore[reportPrivateUsage]

EXPECTED_VARIANTS = {
    "https://www.linkedin.com/in/foo-bar",
    "https://www.linkedin.com/in/foo-bar/",
    "https://linkedin.com/in/foo-bar",
    "https://linkedin.com/in/foo-bar/",
    "http://www.linkedin.com/in/foo-bar",
    "http://www.linkedin.com/in/foo-bar/",
    "http://linkedin.com/in/foo-bar",
    "http://linkedin.com/in/foo-bar/",
}


def test_variants_cover_scheme_www_and_trailing_slash() -> None:
    variants = _linkedin_url_variants("https://www.linkedin.com/in/foo-bar")
    assert EXPECTED_VARIANTS.issubset(set(variants))


def test_variants_dedupe_preserves_order() -> None:
    variants = _linkedin_url_variants("https://www.linkedin.com/in/foo-bar")
    assert variants[0] == "https://www.linkedin.com/in/foo-bar"
    assert len(variants) == len(set(variants))


def test_variants_include_original_with_trailing_slash() -> None:
    original = "https://www.linkedin.com/in/foo-bar/"
    variants = _linkedin_url_variants(original)
    assert original in variants
    assert EXPECTED_VARIANTS.issubset(set(variants))


def test_variants_include_legacy_http_input() -> None:
    original = "http://linkedin.com/in/foo-bar/"
    variants = _linkedin_url_variants(original)
    assert original in variants
    assert "https://www.linkedin.com/in/foo-bar" in variants


def test_variants_returns_input_for_non_profile_url() -> None:
    company = "https://www.linkedin.com/company/acme"
    assert _linkedin_url_variants(company) == [company]
