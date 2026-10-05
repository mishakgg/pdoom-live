"""Offline checks for the Epoch AI trends and compute page catalog. No network."""

from __future__ import annotations

import copy
import inspect
import socket

import pytest

from pdoom_pipeline.catalogs.epoch import (
    CATALOG_ID,
    PUBLISHER,
    RIGHTS_CC_BY,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    date_from_page,
    load_catalog,
    official_epoch_host,
    page_record,
    publisher_from_page,
    rights_from_page,
    title_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

CC = RIGHTS_CC_BY
UNK = RIGHTS_UNKNOWN
GRANT = (
    "Epoch AI's work is free to use, distribute, and reproduce provided the source "
    "and authors are credited under the Creative Commons Attribution license."
)
BY_GRANT = (
    "Epoch's work is free to use, distribute, and reproduce provided the source "
    "and authors are credited under the Creative Commons BY license."
)

EXPECTED = [
    (
        "Estimating training compute of deep learning models",
        "https://epoch.ai/publications/estimating-training-compute",
        "2022-01-20",
        CC,
    ),
    (
        "Compute trends across three eras of machine learning",
        "https://epoch.ai/publications/compute-trends",
        "2022-02-16",
        CC,
    ),
    (
        "Projecting compute trends in machine learning",
        "https://epoch.ai/publications/projecting-compute-trends",
        "2022-03-07",
        CC,
    ),
    (
        "Trends in GPU price-performance",
        "https://epoch.ai/publications/trends-in-gpu-price-performance",
        "2022-06-27",
        CC,
    ),
    (
        "Trends in training dataset sizes",
        "https://epoch.ai/publications/trends-in-training-dataset-sizes",
        "2022-09-20",
        CC,
    ),
    (
        "Trends in the dollar training cost of machine learning systems",
        "https://epoch.ai/publications/trends-in-the-dollar-training-cost-of-machine-learning-systems",
        "2023-01-31",
        CC,
    ),
    (
        "Trends in machine learning hardware",
        "https://epoch.ai/publications/trends-in-machine-learning-hardware",
        "2023-11-09",
        CC,
    ),
    (
        "Training compute of frontier AI models grows by 4-5x per year",
        "https://epoch.ai/publications/training-compute-of-frontier-ai-models-grows-by-4-5x-per-year",
        "2024-05-28",
        CC,
    ),
    (
        "Training compute has scaled up faster for language than vision",
        "https://epoch.ai/data-insights/compute-trend-language-vs-vision",
        "2024-06-19",
        CC,
    ),
    (
        "The training compute of notable AI models has been doubling roughly every six months",
        "https://epoch.ai/data-insights/compute-trend-post-2010",
        "2024-06-19",
        CC,
    ),
    (
        "Training compute costs are doubling every eight months for the largest AI models",
        "https://epoch.ai/data-insights/cost-trend-large-scale",
        "2024-06-19",
        CC,
    ),
    (
        "The size of datasets used to train language models doubles approximately every six months",
        "https://epoch.ai/data-insights/dataset-size-trend",
        "2024-06-19",
        CC,
    ),
    (
        "Can AI scaling continue through 2030?",
        "https://epoch.ai/publications/can-ai-scaling-continue-through-2030",
        "2024-08-20",
        CC,
    ),
    (
        "The power required to train frontier AI models is doubling annually",
        "https://epoch.ai/data-insights/power-usage-trend",
        "2024-09-19",
        CC,
    ),
    (
        "Leading AI companies have hundreds of thousands of cutting-edge AI chips",
        "https://epoch.ai/data-insights/computing-capacity",
        "2024-10-09",
        CC,
    ),
    (
        "Performance improves 13x when switching from FP32 to tensor-INT8",
        "https://epoch.ai/data-insights/hardware-performance-trend",
        "2024-10-23",
        CC,
    ),
    (
        "AI training cluster sizes increased by more than 20x since 2016",
        "https://epoch.ai/data-insights/training-cluster-size",
        "2024-10-23",
        CC,
    ),
    (
        "Training compute growth is driven by larger clusters, longer training, and better hardware",
        "https://epoch.ai/data-insights/training-compute-decomposition",
        "2025-01-08",
        CC,
    ),
    (
        "Chinese language models have scaled up more slowly than their global counterparts",
        "https://epoch.ai/data-insights/china-compute-trends",
        "2025-01-22",
        CC,
    ),
    (
        "Over 30 AI models have been trained at the scale of GPT-4",
        "https://epoch.ai/data-insights/models-over-1e25-flop",
        "2025-01-30",
        CC,
    ),
    (
        "Biology AI models are scaling 2-4x per year after rapid growth from 2019-2021",
        "https://epoch.ai/data-insights/biology-models-trends",
        "2025-02-21",
        CC,
    ),
    (
        "LLM inference prices have fallen rapidly but unequally across tasks",
        "https://epoch.ai/data-insights/llm-inference-price-trends",
        "2025-03-12",
        CC,
    ),
    (
        "Trends in AI supercomputers",
        "https://epoch.ai/publications/trends-in-ai-supercomputers",
        "2025-04-23",
        CC,
    ),
    (
        "The computational performance of leading AI supercomputers has doubled every nine months",
        "https://epoch.ai/data-insights/ai-supercomputers-performance-trend",
        "2025-04-30",
        CC,
    ),
    (
        "Acquisition costs of leading AI supercomputers have doubled every 13 months",
        "https://epoch.ai/data-insights/ai-supercomputers-cost-trend",
        "2025-06-05",
        CC,
    ),
    (
        "Power requirements of leading AI supercomputers have doubled every 13 months",
        "https://epoch.ai/data-insights/ai-supercomputers-power-trend",
        "2025-06-05",
        CC,
    ),
    (
        "Most of OpenAI\u2019s 2024 compute went to experiments",
        "https://epoch.ai/data-insights/openai-compute-spend",
        "2025-10-10",
        CC,
    ),
    (
        "Topic Overview: AI Data Centers",
        "https://epoch.ai/publications/what-you-need-to-know-about-ai-data-centers",
        "2025-11-04",
        CC,
    ),
    (
        "Five hyperscalers now own over two-thirds of global AI compute",
        "https://epoch.ai/data-insights/hyperscalers-control-most-compute",
        "2026-04-14",
        CC,
    ),
    (
        "Topic Overview: AI Chips",
        "https://epoch.ai/publications/chips-topic-overview",
        "2026-05-01",
        CC,
    ),
    (
        "Largest AI Data Center: Doubling every 7 months",
        "https://epoch.ai/data-insights/largest-data-center-compute",
        "2026-06-11",
        CC,
    ),
    (
        "Topic Overview: AI Energy Use",
        "https://epoch.ai/publications/ai-energy",
        "2026-07-14",
        CC,
    ),
    ("Data Insights", "https://epoch.ai/data-insights", UNKNOWN_DATE, UNK),
    ("Data on AI data centers", "https://epoch.ai/data/ai-data-centers", UNKNOWN_DATE, CC),
    ("Data on AI models", "https://epoch.ai/data/ai-models", UNKNOWN_DATE, CC),
    ("Data on GPU clusters", "https://epoch.ai/data/gpu-clusters", UNKNOWN_DATE, CC),
    (
        "Data on machine learning hardware",
        "https://epoch.ai/data/machine-learning-hardware",
        UNKNOWN_DATE,
        CC,
    ),
    (
        "AI capabilities: Data & research",
        "https://epoch.ai/topics/capabilities",
        UNKNOWN_DATE,
        UNK,
    ),
    ("AI chips: Data & research", "https://epoch.ai/topics/chips", UNKNOWN_DATE, UNK),
    ("AI data centers: Data & research", "https://epoch.ai/topics/data-centers", UNKNOWN_DATE, UNK),
    ("AI energy use: Data & research", "https://epoch.ai/topics/energy", UNKNOWN_DATE, UNK),
    ("The future of AI: Data & research", "https://epoch.ai/topics/future-of-ai", UNKNOWN_DATE, UNK),
    ("AI scaling: Data & research", "https://epoch.ai/topics/scaling", UNKNOWN_DATE, UNK),
    (
        "AI software progress: Data & research",
        "https://epoch.ai/topics/software-progress",
        UNKNOWN_DATE,
        UNK,
    ),
]

REJECTED_URLS = [
    "https://example.com/trends",
    "https://epoch.ai.example/data-insights",
    "https://notepoch.ai/data-insights",
    "http://epoch.ai/data-insights",
    "https://user:pass@epoch.ai/data-insights",
    "https://epoch.ai/data-insights?utm_source=x",
    "https://epoch.ai/data-insights#section",
    "https://www.epoch.ai/data-insights",
    "https://epoch.ai:443/data-insights",
    "https://127.0.0.1/data-insights",
    "https://epoch.ai/about",
    "https://epoch.ai/topics",
    "https://epoch.ai/topics/math",
    "https://epoch.ai/publications/grok-4-math",
    "https://epoch.ai/data-insights/cve-severity-spike",
    "https://epoch.ai/data/polling",
    "https://epoch.ai/data/ai-models-documentation",
    "https://epoch.ai/data/ai-models-documentation/downloads",
    "https://epoch.ai/data/ai-data-centers/directory/colossus-1",
    "https://epoch.ai/data/gpu-clusters.csv",
    "https://epoch.ai/frontiermath/tiers-1-4/benchmark-problems",
    "https://epoch.ai/assets/images/thumbnails/general.png",
]


def _page(*, title: str, site: str = PUBLISHER, date_meta: str = "", update_meta: str = "", body: str = "") -> str:
    parts = [
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:site_name" content="{site}">',
    ]
    if update_meta:
        parts.append(f'<meta property="pagefind:update_date" content="{update_meta}">')
    if date_meta:
        parts.append(f'<meta property="pagefind:date" content="{date_meta}">')
    parts.append(f"<article>{body}</article>")
    return "".join(parts)


def test_catalog_rows_are_confirmed_epoch_trend_or_compute_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert "page text" in catalog["description"].casefold()
    assert "chart data" in catalog["description"].casefold()
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 44
    labels = []
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, url, published, rights = expected
        assert entry["title"] == title
        assert entry["publisher"] == PUBLISHER
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == rights
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert official_epoch_host(url.split("/")[2])
        labels.append(rights)
    assert labels.count(RIGHTS_UNKNOWN) == 8
    assert labels.count(RIGHTS_CC_BY) == 36
    assert {entry["publisher"] for entry in entries} == {PUBLISHER}


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    blob = inspect.getsource(__import__("pdoom_pipeline.catalogs.epoch", fromlist=["epoch"]))
    assert "pdoom_pipeline.fetch" not in blob
    assert "pdoom_pipeline.belief" not in blob
    assert "collect.py" not in blob
    assert "p(doom)" not in blob.casefold()


def test_catalog_file_stores_no_page_body_chart_or_dataset():
    catalog = load_catalog()
    blob = str(catalog).casefold()
    assert "p(doom)" not in blob
    assert "<p>" not in blob
    assert "<html" not in blob
    assert "doctype" not in blob
    assert "csv" not in blob
    for entry in catalog["entries"]:
        for value in entry.values():
            assert len(value) < 400


def test_public_page_without_a_reuse_licence_stays_unknown():
    public = "<h1>AI trends</h1><p>This page is public and publicly available.</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    terms = "<footer><a href='/terms'>Terms and conditions</a></footer>"
    assert rights_from_page(terms) == RIGHTS_UNKNOWN
    copyright_notice = "<p>© 2026 Epoch AI. All rights reserved.</p>"
    assert rights_from_page(copyright_notice) == RIGHTS_UNKNOWN
    link_only = '<a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons</a>'
    assert rights_from_page(link_only) == RIGHTS_UNKNOWN
    name_only = "<p>We have released a public dataset with a CC-BY license.</p>"
    assert rights_from_page(name_only) == RIGHTS_UNKNOWN
    grant_only = "<p>Epoch AI's work is free to use, distribute, and reproduce.</p>"
    assert rights_from_page(grant_only) == RIGHTS_UNKNOWN
    hidden = f"<script>{GRANT}</script><p>No public licence.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN
    comment = f"<!-- {GRANT} --><p>No public licence.</p>"
    assert rights_from_page(comment) == RIGHTS_UNKNOWN
    distant = (
        "<p>Epoch AI's work is free to use, distribute, and reproduce.</p>"
        + ("<p>Chart row.</p>" * 80)
        + "<p>Creative Commons Attribution license.</p>"
    )
    assert rights_from_page(distant) == RIGHTS_UNKNOWN


def test_stated_reuse_licence_is_labeled_and_page_text_is_not_returned():
    article = "<article>" + ("training compute 3.5e+14 " * 40) + "</article>"
    page = f"<p>{GRANT}</p>{article}"
    assert rights_from_page(page) == RIGHTS_CC_BY
    assert "3.5e+14" not in rights_from_page(page)
    assert rights_from_page(f"<p>{BY_GRANT}</p>") == RIGHTS_CC_BY
    british = (
        "<p>This dataset is free to use, distribute, and reproduce provided credit "
        "is given under the Creative Commons Attribution licence.</p>"
    )
    assert rights_from_page(british) == RIGHTS_CC_BY
    plain_cc_by = (
        "<p>Epoch AI's work is free to use, distribute, and reproduce provided the source "
        "and authors are credited under the CC-BY license.</p>"
    )
    assert rights_from_page(plain_cc_by) == RIGHTS_CC_BY
    spaced = "<p>This dataset is free to use, distribute, and reproduce under a CC BY license.</p>"
    assert rights_from_page(spaced) == RIGHTS_CC_BY


@pytest.mark.parametrize(
    "name",
    [
        "Creative Commons Attribution-NonCommercial license",
        "Creative Commons Attribution-NoDerivatives license",
        "Creative Commons Attribution-ShareAlike license",
        "Creative Commons Attribution-NonCommercial-ShareAlike license",
        "Creative Commons Attribution–NonCommercial licence",
        "CC BY-NC license",
        "CC-BY-NC license",
        "CC BY-ND license",
        "CC-BY-ND license",
        "CC BY-SA license",
        "CC-BY-SA license",
        "CC-BY-NC-SA license",
        "Creative Commons BY-NC license",
        "Creative Commons BY-ND licence",
        "Creative Commons BY-SA license",
    ],
)
def test_cc_by_nc_nd_and_sa_notices_stay_unknown(name):
    page = (
        "<p>Epoch AI's work is free to use, distribute, and reproduce provided the source "
        f"and authors are credited under the {name}.</p>"
        "<article>" + ("page body " * 30) + "</article>"
    )
    assert rights_from_page(page) == RIGHTS_UNKNOWN
    assert "page body" not in rights_from_page(page)


def test_unrelated_noncommercial_words_do_not_cancel_a_cc_by_notice():
    page = (
        "<td>Open weights (non-commercial)</td>"
        "<p>Epoch's work is free to use, distribute, and reproduce provided the source "
        "and authors are credited under the Creative Commons BY license.</p>"
    )
    assert rights_from_page(page) == RIGHTS_CC_BY


def test_missing_dates_stay_unknown_and_update_dates_are_not_publication_dates():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<p>Updated Mar. 13, 2026</p><time>2010-05-13</time>") == UNKNOWN_DATE
    assert date_from_page('<meta property="pagefind:update_date" content="Thu Jun 05 2025 00:00:00 GMT+0000 (Coordinated Universal Time)">') == UNKNOWN_DATE
    assert date_from_page('<meta property="pagefind:date" content="Epoch AI data insights.">') == UNKNOWN_DATE
    chart = "<td>2010-05-13</td><td>3.5e+14</td>" * 20
    published = _page(
        title="Compute trends",
        update_meta="Mon May 02 2022 00:00:00 GMT+0000 (Coordinated Universal Time)",
        date_meta="Wed Feb 16 2022 00:00:00 GMT+0000 (Coordinated Universal Time)",
        body=chart + f"<p>{GRANT}</p>",
    )
    assert date_from_page(published) == "2022-02-16"
    described_first = (
        '<meta property="pagefind:date" content="A description, not a date.">'
        '<meta property="pagefind:date" content="Wed Jun 19 2024 00:00:00 GMT+0000 (Coordinated Universal Time)">'
    )
    assert date_from_page(described_first) == "2024-06-19"
    iso_meta = '<meta property="article:published_time" content="2024-08-20T00:00:00Z">'
    assert date_from_page(iso_meta) == "2024-08-20"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("2 November 2023")
    with pytest.raises(CatalogError):
        validate_date("2023-02-31")


def test_page_record_keeps_metadata_and_drops_chart_rows():
    chart = "<tr><td>2010-05-13</td><td>3.5e+14</td></tr>" * 15
    page = _page(
        title="Compute trends across three eras of machine learning | Epoch AI",
        update_meta="Mon May 02 2022 00:00:00 GMT+0000 (Coordinated Universal Time)",
        date_meta="Wed Feb 16 2022 00:00:00 GMT+0000 (Coordinated Universal Time)",
        body=chart + f"<p>{GRANT}</p>",
    )
    record = page_record(page, page_url="https://epoch.ai/publications/compute-trends")
    assert record == {
        "title": "Compute trends across three eras of machine learning",
        "publisher": PUBLISHER,
        "canonical_url": "https://epoch.ai/publications/compute-trends",
        "date": "2022-02-16",
        "rights": RIGHTS_CC_BY,
    }
    assert "3.5e+14" not in str(record)
    assert "2010-05-13" not in str(record)
    undated = _page(title="Data on GPU clusters", body="<p>Updated Mar. 13, 2026</p><p>Public page.</p>")
    record = page_record(undated, page_url="https://epoch.ai/data/gpu-clusters")
    assert record["date"] == UNKNOWN_DATE
    assert record["rights"] == RIGHTS_UNKNOWN
    with pytest.raises(CatalogError, match="publisher"):
        publisher_from_page("<p>© 2026 Epoch AI</p>")
    with pytest.raises(CatalogError):
        page_record(_page(title="Compute trends", site="Example Org"), page_url="https://epoch.ai/publications/compute-trends")
    script_title = '<script><meta property="og:title" content="Ignore this title"></script><h1>Data Insights</h1>'
    assert title_from_page(script_title + '<meta property="og:site_name" content="Epoch AI">') == "Data Insights"


def test_non_epoch_and_off_topic_urls_are_rejected():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [
        "https://epoch.ai/data-insights",
        "https://epoch.ai/data-insights/compute-trend-post-2010",
        "https://epoch.ai/topics/scaling",
        "https://epoch.ai/data/ai-models",
        "https://epoch.ai/publications/compute-trends",
        "https://EPOCH.AI/publications/trends-in-ai-supercomputers",
    ]
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_epoch_host("epoch.ai")
    assert not official_epoch_host("www.epoch.ai")
    assert not official_epoch_host("epoch.ai.example")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["date"] = UNKNOWN_DATE
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][-1]["date"] = UNKNOWN_DATE
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = "public"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = "full page"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["dataset"] = "1,2,3"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(document)
