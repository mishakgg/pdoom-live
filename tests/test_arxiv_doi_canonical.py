"""DOI 10.48550/arxiv.2206.08966 has one https://doi.org URL.

``https://doi.org/10.48550/arxiv.2206.08966`` and
``https://dx.doi.org/10.48550/arxiv.2206.08966`` share that URL.
A publisher PDF and an arXiv PDF stay unchanged.
The checks use :func:`pdoom_pipeline.urls.canonicalize_url` only.
Network sockets stay blocked, and the paper is not downloaded.
"""

from __future__ import annotations

import socket

import pytest

from pdoom_pipeline.urls import canonicalize_url

DOI = "10.48550/arxiv.2206.08966"
CANONICAL = f"https://doi.org/{DOI}"
PUBLISHER_PDF = f"https://onlinelibrary.wiley.com/doi/pdf/{DOI}"
ARXIV_PDF = "https://arxiv.org/pdf/2206.08966"
ARXIV_PDF_WITH_DOI = f"https://arxiv.org/pdf/{DOI}"


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("arxiv doi canonicalization must not use the network")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)


def test_doi_org_and_dx_doi_org_share_one_https_doi_url(monkeypatch: pytest.MonkeyPatch):
    _block_network(monkeypatch)
    direct = "https://doi.org/10.48550/arxiv.2206.08966"
    dx = "https://dx.doi.org/10.48550/arxiv.2206.08966"
    assert direct != dx
    shared = canonicalize_url(direct)
    assert shared == canonicalize_url(dx) == CANONICAL
    assert shared.startswith("https://doi.org/")
    assert shared == "https://doi.org/10.48550/arxiv.2206.08966"
    assert canonicalize_url(shared) == shared


def test_publisher_and_arxiv_pdf_stay_unchanged(monkeypatch: pytest.MonkeyPatch):
    _block_network(monkeypatch)
    assert canonicalize_url(PUBLISHER_PDF) == PUBLISHER_PDF
    assert canonicalize_url(ARXIV_PDF_WITH_DOI) == ARXIV_PDF_WITH_DOI
    arxiv_pdf = canonicalize_url(ARXIV_PDF)
    assert arxiv_pdf == "https://arxiv.org/abs/2206.08966"
    assert arxiv_pdf.startswith("https://arxiv.org/")
    assert arxiv_pdf != CANONICAL
