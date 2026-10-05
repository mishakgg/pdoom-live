"""doi.org and dx.doi.org collapse to one https://doi.org URL.

The checks use :func:`pdoom_pipeline.urls.canonicalize_url` only.
They do not resolve DOI names or open a network connection.
"""

from __future__ import annotations

import socket

import pytest

from pdoom_pipeline.urls import canonicalize_url

DOI = "10.1111/phc3.12964"
CANONICAL = f"https://doi.org/{DOI}"
TITLE = "Artificial Intelligence: Arguments for Catastrophic Risk"


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("network disabled")

    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)


def test_doi_org_and_dx_doi_org_share_one_https_doi_url(monkeypatch: pytest.MonkeyPatch):
    _block_network(monkeypatch)
    variants = (
        f"https://doi.org/{DOI}",
        f"https://dx.doi.org/{DOI}",
        f"http://doi.org/{DOI}",
        f"http://dx.doi.org/{DOI}",
        f"https://DOI.org/{DOI}",
        f"https://DX.DOI.ORG/{DOI}",
        f"https://www.doi.org/{DOI}",
        f"https://doi.org/{DOI}/",
        f"https://dx.doi.org/{DOI}?utm_source=newsletter#section",
    )
    canonical = [canonicalize_url(url) for url in variants]
    assert set(canonical) == {CANONICAL}
    assert all(url == CANONICAL for url in canonical)


def test_non_doi_url_stays_unchanged(monkeypatch: pytest.MonkeyPatch):
    _block_network(monkeypatch)
    page = "https://example.com/papers/artificial-intelligence-arguments-for-catastrophic-risk"
    publisher = f"https://onlinelibrary.wiley.com/doi/pdf/{DOI}"
    assert canonicalize_url(page) == page
    assert canonicalize_url(publisher) == publisher
    assert not canonicalize_url(page).startswith("https://doi.org/")
    assert not canonicalize_url(publisher).startswith("https://doi.org/")


def test_title_is_not_invented_as_a_doi(monkeypatch: pytest.MonkeyPatch):
    _block_network(monkeypatch)
    with pytest.raises(ValueError):
        canonicalize_url(TITLE)
    titled = "https://example.com/artificial-intelligence-arguments-for-catastrophic-risk"
    assert canonicalize_url(titled) == titled
    assert DOI not in canonicalize_url(titled)
