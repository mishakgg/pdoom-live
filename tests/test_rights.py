"""Local license classification. These tests do not use the network."""

from __future__ import annotations

import socket

import pytest

from pdoom_pipeline.rights import ARXIV_NONEXCLUSIVE, CC0, CC_BY, CC_BY_ND, CC_BY_SA, classify_license


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def rejected(*_args, **_kwargs):
        raise AssertionError("license classification tried to use the network")

    monkeypatch.setattr(socket, "create_connection", rejected)
    monkeypatch.setattr(socket, "socket", rejected)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    _block_network(monkeypatch)


@pytest.mark.parametrize(
    "value",
    [
        "CC0",
        "cc0-1.0",
        "CC0 1.0",
        "https://creativecommons.org/publicdomain/zero/1.0/",
        "http://creativecommons.org/publicdomain/zero/1.0/legalcode",
        "https://spdx.org/licenses/CC0-1.0.html",
    ],
)
def test_cc0_is_copyable(value: str):
    result = classify_license(value)
    assert result.license_id == CC0
    assert result.known is True
    assert result.copyable is True
    assert result.unchanged_only is False
    assert result.allows_copy(unchanged=False) is True
    assert result.allows_copy(unchanged=True) is True


@pytest.mark.parametrize(
    "value",
    [
        "CC-BY",
        "CC BY 4.0",
        "cc-by-4.0",
        "CC_BY_4.0",
        "https://creativecommons.org/licenses/by/4.0/",
        "http://creativecommons.org/licenses/by/3.0/",
        "https://creativecommons.org/licenses/by/4.0/deed.en",
        "https://creativecommons.org/licenses/by/4.0/?ref=chooser-v1",
        "HTTPS://CreativeCommons.org/licenses/BY/4.0/legalcode",
        "https://spdx.org/licenses/CC-BY-4.0.html",
    ],
)
def test_cc_by_is_copyable(value: str):
    result = classify_license(value)
    assert result.license_id == CC_BY
    assert result.known is True
    assert result.copyable is True
    assert result.unchanged_only is False
    assert result.allows_copy() is True


@pytest.mark.parametrize(
    "value",
    [
        "CC-BY-SA",
        "CC BY-SA 4.0",
        "cc-by-sa-4.0+",
        "https://creativecommons.org/licenses/by-sa/4.0/",
        "https://creativecommons.org/licenses/by-sa/4.0/legalcode.en",
        "https://spdx.org/licenses/CC-BY-SA-4.0",
    ],
)
def test_cc_by_sa_is_copyable(value: str):
    result = classify_license(value)
    assert result.license_id == CC_BY_SA
    assert result.known is True
    assert result.copyable is True
    assert result.unchanged_only is False
    assert result.allows_copy(unchanged=False) is True


@pytest.mark.parametrize(
    "value",
    [
        "CC-BY-ND",
        "CC-BY-ND-4.0",
        "cc by-nd 3.0",
        "https://creativecommons.org/licenses/by-nd/4.0/",
        "https://creativecommons.org/licenses/by-nd/4.0/deed.en",
        "https://spdx.org/licenses/CC-BY-ND-4.0.html",
    ],
)
def test_cc_by_nd_is_unchanged_only(value: str):
    result = classify_license(value)
    assert result.license_id == CC_BY_ND
    assert result.known is True
    assert result.copyable is False
    assert result.unchanged_only is True
    assert result.allows_copy() is False
    assert result.allows_copy(unchanged=False) is False
    assert result.allows_copy(unchanged=True) is True


def test_nd_is_not_a_silent_yes_for_by():
    by_license = classify_license("CC-BY-4.0")
    nd_license = classify_license("CC-BY-ND-4.0")
    assert by_license.copyable is True
    assert nd_license.copyable is False
    assert by_license.license_id != nd_license.license_id
    assert nd_license.unchanged_only is True
    assert by_license.unchanged_only is False


@pytest.mark.parametrize(
    "value",
    [
        "http://arxiv.org/licenses/nonexclusive-distrib/1.0/",
        "https://arxiv.org/licenses/nonexclusive-distrib/1.0",
        "http://arXiv.org/licenses/nonexclusive-distrib/1.0/",
        "  http://arxiv.org/licenses/nonexclusive-distrib/1.0/  ",
        "http://arxiv.org/licenses/nonexclusive-distrib/1.0/?ref=1",
        "arxiv.org/licenses/nonexclusive-distrib/1.0/",
    ],
)
def test_arxiv_nonexclusive_license_is_not_copyable(value: str):
    result = classify_license(value)
    assert result.license_id == ARXIV_NONEXCLUSIVE
    assert result.known is True
    assert result.copyable is False
    assert result.unchanged_only is False
    assert result.allows_copy(unchanged=False) is False
    assert result.allows_copy(unchanged=True) is False


@pytest.mark.parametrize("value", [None, "", "   ", "\n\t"])
def test_missing_or_blank_license_stays_unknown(value: str | None):
    result = classify_license(value)
    assert result.license_id is None
    assert result.known is False
    assert result.copyable is False
    assert result.unchanged_only is False
    assert result.allows_copy(unchanged=True) is False


@pytest.mark.parametrize(
    "value",
    [
        "unknown",
        "none",
        "MIT",
        "Apache-2.0",
        "public",
        "public domain",
        "public-domain",
        "all rights reserved",
        "CC-BY-NC",
        "CC-BY-NC-4.0",
        "CC-BY-NC-SA-4.0",
        "CC-BY-NC-ND-4.0",
        "CCBY",
        "licensed under CC-BY-4.0",
        "https://creativecommons.org/licenses/by-nc/4.0/",
        "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "https://creativecommons.org/licenses/sampling/1.0/",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "https://spdx.org/licenses/MIT.html",
        "https://spdx.org/licenses/CC-BY-NC-4.0.html",
    ],
)
def test_unknown_license_is_not_copyable(value: str):
    result = classify_license(value)
    assert result.known is False
    assert result.license_id is None
    assert result.copyable is False
    assert result.unchanged_only is False
    assert result.allows_copy(unchanged=True) is False


@pytest.mark.parametrize(
    "value",
    [
        "https://arxiv.org/abs/2209.10604",
        "https://arxiv.org/pdf/2209.10604.pdf",
        "https://export.arxiv.org/licenses/nonexclusive-distrib/1.0/",
        "https://example.com/",
        "https://example.com/cc-by",
        "https://example.com/?license=cc-by",
        "https://creativecommons.org/",
        "https://creativecommons.org/licenses/",
        "https://creativecommons.org/about/",
        "https://creativecommons.org/licenses/by/4.0/about",
        "https://en.wikipedia.org/wiki/Creative_Commons",
        "https://spdx.org/",
        "//example.com/public",
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC-BY</a>',
        "<html><title>Public</title><p>This page is public.</p></html>",
    ],
)
def test_public_web_page_is_not_a_license(value: str):
    result = classify_license(value)
    assert result.known is False
    assert result.copyable is False
    assert result.unchanged_only is False
    assert result.allows_copy(unchanged=True) is False
