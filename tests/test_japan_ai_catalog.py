"""Offline checks for the Japanese government AI page catalog. No network."""

from __future__ import annotations

import copy
import inspect
import socket

import pytest

from pdoom_pipeline.catalogs.japan_ai import (
    CATALOG_ID,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_PUBLIC_DATA,
    RIGHTS_STANDARD_TERMS,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    date_from_page,
    load_catalog,
    official_japan_host,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

EXPECTED = [
    (
        "「AI事業者ガイドライン案」に関する意見募集の結果及びガイドラインの公表",
        "総務省及び経済産業省",
        "https://www.soumu.go.jp/menu_news/s-news/01ryutsu20_02000001_00010.html",
        "2024-04-19",
        RIGHTS_UNKNOWN,
    ),
    (
        "ＡＩ法 全面施行 －次なるフェーズへ－",
        "内閣府",
        "https://www.cao.go.jp/press/new_wave/20251003",
        "2025-10-03",
        RIGHTS_UNKNOWN,
    ),
    (
        "人工知能関連技術の研究開発及び活用の適正性確保に関する指針",
        "内閣府",
        "https://www8.cao.go.jp/cstp/ai/ai_guideline/ai_guideline.html",
        "2025-12-19",
        RIGHTS_UNKNOWN,
    ),
    (
        "「行政の進化と革新のための生成AIの調達·利活用に係るガイドライン（第2.0版）」を策定しました",
        "デジタル庁",
        "https://www.digital.go.jp/news/decb64eb-f26e-41cb-8d37-f3dd173108b8",
        "2026-06-12",
        RIGHTS_UNKNOWN,
    ),
    (
        "人工知能基本計画",
        "内閣府",
        "https://www8.cao.go.jp/cstp/ai/ai_plan/ai_plan.html",
        "2026-07-14",
        RIGHTS_UNKNOWN,
    ),
    (
        "Government AI “GENAI”",
        "Digital Agency",
        "https://www.digital.go.jp/en/policies/genai",
        UNKNOWN_DATE,
        RIGHTS_UNKNOWN,
    ),
    (
        "ガバメントAI「源内」",
        "デジタル庁",
        "https://www.digital.go.jp/policies/genai",
        UNKNOWN_DATE,
        RIGHTS_UNKNOWN,
    ),
    (
        "「AI事業者ガイドライン」掲載ページ",
        "総務省",
        "https://www.soumu.go.jp/main_sosiki/kenkyu/ai_network/02ryutsu20_04000019.html",
        UNKNOWN_DATE,
        RIGHTS_UNKNOWN,
    ),
    (
        "人工知能関連技術の研究開発及び活用の推進に関する法律（ＡＩ法）",
        "内閣府",
        "https://www8.cao.go.jp/cstp/ai/ai_act/ai_act.html",
        UNKNOWN_DATE,
        RIGHTS_UNKNOWN,
    ),
    (
        "人工知能戦略本部",
        "内閣府",
        "https://www8.cao.go.jp/cstp/ai/ai_hq/ai_hq.html",
        UNKNOWN_DATE,
        RIGHTS_UNKNOWN,
    ),
    (
        "設置根拠：AI法",
        "内閣府",
        "https://www8.cao.go.jp/cstp/ai/ai_hq/konkyo.html",
        UNKNOWN_DATE,
        RIGHTS_UNKNOWN,
    ),
    (
        "AI戦略",
        "内閣府",
        "https://www8.cao.go.jp/cstp/ai/index.html",
        UNKNOWN_DATE,
        RIGHTS_UNKNOWN,
    ),
]

REJECTED_URLS = [
    "https://example.com/artificial-intelligence",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://digital.go.jp.example/ai",
    "https://notgo.jp/ai",
    "https://www.meti.go.jp.example/ai",
    "http://www.digital.go.jp/policies/genai",
    "https://user:pass@www.digital.go.jp/policies/genai",
    "https://www.digital.go.jp/policies/genai?utm_source=x",
    "https://www.digital.go.jp/policies/genai#section",
    "https://www.meti.go.jp/shingikai/ai_guidelines.pdf",
    "https://www.digital.go.jp/",
    "https://127.0.0.1/ai",
    "https://www.digital.go.jp/foo/../policies/genai",
]


def test_catalog_rows_are_confirmed_japan_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 12
    publishers = set()
    labels = []
    hosts = set()
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, publisher, url, published, rights = expected
        assert entry["title"] == title
        assert entry["publisher"] == publisher
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == rights
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        publishers.add(publisher)
        labels.append(rights)
        host = url.split("/")[2]
        hosts.add(host)
        assert official_japan_host(host)
    assert "デジタル庁" in publishers
    assert "Digital Agency" in publishers
    assert "内閣府" in publishers
    assert "総務省" in publishers
    assert any("経済産業省" in publisher for publisher in publishers)
    assert "www.digital.go.jp" in hosts
    assert all(host == "go.jp" or host.endswith(".go.jp") for host in hosts)
    assert labels.count(RIGHTS_UNKNOWN) == 12
    assert RIGHTS_STANDARD_TERMS not in labels
    assert RIGHTS_PUBLIC_DATA not in labels
    assert RIGHTS_CREATIVE_COMMONS not in labels
    assert "·" in entries[3]["title"]
    assert "\u201c" in entries[5]["title"] and "\u201d" in entries[5]["title"]


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    blob = inspect.getsource(__import__("pdoom_pipeline.catalogs.japan_ai", fromlist=["japan_ai"]))
    assert "pdoom_pipeline.fetch" not in blob
    assert "pdoom_pipeline.belief" not in blob
    assert "p(doom)" not in blob.casefold()


def test_catalog_file_stores_no_page_body():
    catalog = load_catalog()
    blob = str(catalog).casefold()
    assert "p(doom)" not in blob
    assert "<p>" not in blob
    assert "<html" not in blob
    assert "doctype" not in blob
    for entry in catalog["entries"]:
        for value in entry.values():
            assert len(value) < 400


def test_public_page_without_a_reuse_licence_stays_unknown():
    public = "<h1>人工知能</h1><p>このページは公開されています。</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    policy = "<footer><a href='/site-policy'>サイトポリシー</a></footer>"
    assert rights_from_page(policy) == RIGHTS_UNKNOWN
    digital = "<p>© Digital Agency, Government of Japan</p>"
    assert rights_from_page(digital) == RIGHTS_UNKNOWN
    cabinet = "<p>© Cabinet Office, Government of Japan</p>"
    assert rights_from_page(cabinet) == RIGHTS_UNKNOWN
    reserved = "<p>© 2009 Ministry of Internal Affairs and Communications All Rights Reserved.</p>"
    assert rights_from_page(reserved) == RIGHTS_UNKNOWN
    prohibited = "<p>無断転載を禁じます。</p>"
    assert rights_from_page(prohibited) == RIGHTS_UNKNOWN
    unnamed = "<p>政府標準利用規約の見直しを検討しています。</p>"
    assert rights_from_page(unnamed) == RIGHTS_UNKNOWN
    compatible = "<p>本利用ルールはCC BYと互換性があります。</p>"
    assert rights_from_page(compatible) == RIGHTS_UNKNOWN
    hidden = "<script>政府標準利用規約（第2.0版）に準拠し、自由に利用できます。</script><p>No public licence.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN
    comment = "<!-- 政府標準利用規約（第2.0版） --><p>No public licence.</p>"
    assert rights_from_page(comment) == RIGHTS_UNKNOWN


def test_stated_reuse_licence_is_labeled_and_page_text_is_not_returned():
    standard = (
        "<p>当ウェブサイトのコンテンツは、政府標準利用規約（第2.0版）に準拠した利用条件の下で、"
        "自由に利用できます。</p><article>" + ("page body " * 40) + "</article>"
    )
    assert rights_from_page(standard) == RIGHTS_STANDARD_TERMS
    assert "page body" not in rights_from_page(standard)
    english = "<p>Content on this website is available under the Government of Japan Standard Terms of Use (Version 2.0).</p>"
    assert rights_from_page(english) == RIGHTS_STANDARD_TERMS
    both = (
        "<p>政府標準利用規約（第2.0版）に準拠しています。"
        "クリエイティブ・コモンズ・ライセンスの表示4.0国際と互換性があります。"
        "複製、公衆送信、翻訳・変形等の翻案等、自由に利用できます。</p>"
    )
    assert rights_from_page(both) == RIGHTS_STANDARD_TERMS
    public_data = (
        "<p>本利用ルールは、「公共データ利用規約（第1.0版）」に準拠しています。"
        "コンテンツは、複製、公衆送信その他の利用ができます。</p>"
    )
    assert rights_from_page(public_data) == RIGHTS_PUBLIC_DATA
    creative_commons = "<p>This work is licensed under the Creative Commons Attribution 4.0 International license.</p>"
    assert rights_from_page(creative_commons) == RIGHTS_CREATIVE_COMMONS
    link = "<p>クリエイティブ・コモンズ 表示 4.0 https://creativecommons.org/licenses/by/4.0/</p>"
    assert rights_from_page(link) == RIGHTS_CREATIVE_COMMONS
    by_sa = "<p>https://creativecommons.org/licenses/by-sa/4.0/</p>"
    assert rights_from_page(by_sa) == RIGHTS_CREATIVE_COMMONS
    cc0 = "<p>https://creativecommons.org/publicdomain/zero/1.0/</p>"
    assert rights_from_page(cc0) == RIGHTS_CREATIVE_COMMONS


def test_noncommercial_or_noderivatives_creative_commons_stays_unknown():
    by_nc = "<p>https://creativecommons.org/licenses/by-nc/4.0/</p>"
    assert rights_from_page(by_nc) == RIGHTS_UNKNOWN
    by_nd = "<p>https://creativecommons.org/licenses/by-nd/4.0/</p>"
    assert rights_from_page(by_nd) == RIGHTS_UNKNOWN
    by_nc_sa = "<p>https://creativecommons.org/licenses/by-nc-sa/4.0/</p>"
    assert rights_from_page(by_nc_sa) == RIGHTS_UNKNOWN
    by_nc_nd = "<p>https://creativecommons.org/licenses/by-nc-nd/4.0/</p>"
    assert rights_from_page(by_nc_nd) == RIGHTS_UNKNOWN
    phrase = "<p>This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International license.</p>"
    assert rights_from_page(phrase) == RIGHTS_UNKNOWN
    noderivatives = "<p>licensed under the Creative Commons Attribution-NoDerivatives 4.0 license.</p>"
    assert rights_from_page(noderivatives) == RIGHTS_UNKNOWN
    generic = "<p>This work is licensed under a Creative Commons license. https://creativecommons.org/licenses/</p>"
    assert rights_from_page(generic) == RIGHTS_UNKNOWN
    japanese_nc = "<p>クリエイティブ・コモンズ 表示-非営利 4.0</p>"
    assert rights_from_page(japanese_nc) == RIGHTS_UNKNOWN
    japanese_nd = "<p>クリエイティブ・コモンズ 表示-改変禁止 4.0</p>"
    assert rights_from_page(japanese_nd) == RIGHTS_UNKNOWN
    mixed = (
        "<p>https://creativecommons.org/licenses/by/4.0/ "
        "https://creativecommons.org/licenses/by-nc/4.0/</p>"
    )
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN


def test_missing_dates_stay_unknown_and_labeled_dates_win():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<time>2017-08-24</time>") == UNKNOWN_DATE
    assert date_from_page('<meta name="dcterms.created" content="2017-03-30">') == UNKNOWN_DATE
    assert date_from_page("<p>令和七年法律第五十三号</p>") == UNKNOWN_DATE
    prose = "<h1>ＡＩ法</h1><p>生成ＡＩの発展は重要です。令和7年6月4日にＡＩ法が公布されました。</p>"
    assert date_from_page(prose) == UNKNOWN_DATE
    hidden = "<script>公開日: 1999年1月1日</script><p>No date.</p>"
    assert date_from_page(hidden) == UNKNOWN_DATE
    issued = (
        '<meta name="dcterms.issued" content="2024-07-02">'
        '<meta name="dcterms.modified" content="2025-06-24">'
        "<p>公開日: 2026年6月12日</p>"
    )
    assert date_from_page(issued) == "2024-07-02"
    empty_issued = (
        '<meta name="dcterms.issued" content="">'
        '<meta name="dcterms.modified" content="2026-07-30">'
    )
    assert date_from_page(empty_issued) == UNKNOWN_DATE
    published = "<p>公開日: 2026年6月12日</p><p>最終更新日: 2026年9月30日</p>"
    assert date_from_page(published) == "2026-06-12"
    modified = "<h1>ガバメントAI「源内」</h1><p>最終更新日: 2026年9月30日</p>"
    assert date_from_page(modified) == UNKNOWN_DATE
    english = "<h1>Government AI “GENAI”</h1><p>Last Updated: Jul 29, 2026</p>"
    assert date_from_page(english) == UNKNOWN_DATE
    listed = "<p>掲載日: 2025-03-04</p><p>最終更新日: 2026年9月30日</p>"
    assert date_from_page(listed) == "2025-03-04"
    date_published = "<p>Date published: 2024-04-19</p><p>Last updated: 2026-07-29</p>"
    assert date_from_page(date_published) == "2024-04-19"
    article = '<meta property="article:published_time" content="2026-06-12T01:02:03Z">'
    assert date_from_page(article) == "2026-06-12"
    schema = '<meta itemprop="datePublished" content="2025-10-03">'
    assert date_from_page(schema) == "2025-10-03"
    date_modified = (
        '<meta name="dateModified" content="2026-09-30">'
        '<meta property="article:modified_time" content="2026-08-01T00:00:00Z">'
        "<p>© 2024 Digital Agency, Government of Japan</p>"
        "<p>Copyright 2009</p>"
    )
    assert date_from_page(date_modified) == UNKNOWN_DATE
    decision = (
        "<h1>人工知能基本計画</h1><p>令和８年７月14日 閣議決定</p>"
        "<p>過去の計画 令和7年12月23日 閣議決定</p>"
    )
    assert date_from_page(decision) == "2026-07-14"
    headquarters = "<h1>指針</h1><p>令和7年12月19日 本部決定</p>"
    assert date_from_page(headquarters) == "2025-12-19"
    leading = "<h1>ＡＩ法 全面施行 －次なるフェーズへ－</h1><p>2025年10月3日</p>"
    assert date_from_page(leading) == "2025-10-03"
    press = "<h1>報道資料</h1><p>令和6年4月19日</p><p>総務省 経済産業省</p>"
    assert date_from_page(press) == "2024-04-19"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("2 November 2023")
    with pytest.raises(CatalogError):
        validate_date("2023-02-31")


def test_non_government_urls_are_rejected_and_official_hosts_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [
        "https://www.digital.go.jp/policies/genai",
        "https://www.digital.go.jp/en/policies/genai",
        "https://www.meti.go.jp/shingikai/mono_info_service/ai_shakai_jisso/20260331_report.html",
        "https://www8.cao.go.jp/cstp/ai/ai_plan/ai_plan.html",
        "https://www.soumu.go.jp/hiroshimaaiprocess/",
        "https://www.cao.go.jp/press/new_wave/20251003",
    ]
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_japan_host("digital.go.jp")
    assert official_japan_host("www.meti.go.jp")
    assert official_japan_host("www8.cao.go.jp")
    assert official_japan_host("go.jp")
    assert not official_japan_host("digital.go.jp.example")
    assert not official_japan_host("notgo.jp")
    assert not official_japan_host("www.meti.go.jp.example")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    document["entries"][1]["date"] = UNKNOWN_DATE
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["date"] = UNKNOWN_DATE
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = "public"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = "all_rights_reserved"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = "full page"
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
