"""Offline checks for the public CNIL artificial-intelligence page catalog."""

from __future__ import annotations

import copy
import inspect
import socket
from pathlib import Path

import pytest

from pdoom_pipeline.catalogs.cnil_ai import (
    CATALOG_ID,
    MAX_FIELD_CHARS,
    PUBLISHER,
    RIGHTS_CC_BY_4_0,
    RIGHTS_CC_BY_NC_ND_4_0,
    RIGHTS_CC_BY_ND_4_0,
    RIGHTS_LICENCE_OUVERTE,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    canonical_url_from_page,
    catalog_path,
    date_from_page,
    load_catalog,
    official_cnil_host,
    page_record,
    rights_from_page,
    title_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

EXPECTED = [
    (
        'Intelligence artificielle, de quoi parle-t-on ?',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/intelligence-artificielle-de-quoi-parle-t-on',
        '2022-03-25',
        'unknown',
    ),
    (
        "Collecter et qualifier les données d'entraînement",
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/collecter-et-qualifier-les-donnees-dentrainement',
        '2022-03-28',
        'unknown',
    ),
    (
        'Conformité des systèmes d’IA : les autres guides, outils et bonnes pratiques',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/conformite-des-systemes-dia-les-autres-guides-outils-et-bonnes-pratiques',
        '2022-03-28',
        'unknown',
    ),
    (
        'Développer et entraîner un algorithme',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/developper-et-entrainer-un-algorithme',
        '2022-03-28',
        'unknown',
    ),
    (
        "Introduction au guide d'auto-évaluation pour les systèmes d'IA",
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/introduction',
        '2022-03-28',
        'unknown',
    ),
    (
        'Permettre le bon exercice de leurs droits par les personnes',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/permettre-le-bon-exercice-de-leurs-droits-par-les-personnes',
        '2022-03-28',
        'unknown',
    ),
    (
        'Se mettre en conformité',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/se-mettre-en-conformite',
        '2022-03-28',
        'unknown',
    ),
    (
        'Sécuriser le traitement',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/securiser-le-traitement',
        '2022-03-28',
        'unknown',
    ),
    (
        "Utiliser un système d'IA en production",
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/utiliser-un-systeme-dia-en-production',
        '2022-03-28',
        'unknown',
    ),
    (
        'Intelligence artificielle : la CNIL publie un ensemble de ressources pour le grand public et les professionnels',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/la-cnil-publie-ressources-grand-public-professionnels',
        '2022-03-29',
        'unknown',
    ),
    (
        "Se poser les bonnes questions avant d’utiliser un système d'intelligence artificielle",
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide/se-poser-les-bonnes-questions-avant-dutiliser-un-systeme-dintelligence-artificielle',
        '2022-04-05',
        'unknown',
    ),
    (
        'IA : comment être en conformité avec le RGPD ?',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/ia-comment-etre-en-conformite-avec-le-rgpd',
        '2022-04-05',
        'unknown',
    ),
    (
        'IA : Assurer que le traitement est licite - Définir une base légale',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/assurer-que-le-traitement-est-licite',
        '2024-04-08',
        'unknown',
    ),
    (
        'IA : Assurer que le traitement est licite - En cas de réutilisation des données, effectuer les tests et vérifications nécessaires',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/assurer-que-le-traitement-est-licite-reutilisation-des-donnees',
        '2024-04-08',
        'unknown',
    ),
    (
        'IA : Définir une finalité',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/definir-une-finalite-0',
        '2024-04-08',
        'unknown',
    ),
    (
        'Déterminer la qualification juridique des acteurs',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/determiner-la-qualification-juridique-des-fournisseurs-de-systemes-dia',
        '2024-04-08',
        'unknown',
    ),
    (
        'IA : Déterminer le régime juridique applicable',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/determiner-le-regime-juridique-applicable',
        '2024-04-08',
        'unknown',
    ),
    (
        'Quel est le périmètre des fiches pratiques sur l’IA ?',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/quel-est-le-perimetre-des-fiches-pratiques-sur-lia',
        '2024-04-08',
        'unknown',
    ),
    (
        'IA : Réaliser une analyse d’impact si nécessaire',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/realiser-une-analyse-dimpact-si-necessaire',
        '2024-04-08',
        'unknown',
    ),
    (
        'IA : Tenir compte de la protection des données dans la collecte et la gestion des données',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/tenir-compte-de-la-protection-des-donnees-dans-la-collecte-et-la-gestion-des-donnees',
        '2024-04-08',
        'unknown',
    ),
    (
        'IA : Tenir compte de la protection des données dans la conception du système',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/tenir-compte-de-la-protection-des-donnees-dans-la-conception-du-systeme',
        '2024-04-08',
        'unknown',
    ),
    (
        'Les questions-réponses de la CNIL sur l’utilisation d’un système d’IA générative',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/les-questions-reponses-de-la-cnil-sur-lutilisation-dun-systeme-dia-generative',
        '2024-07-18',
        'unknown',
    ),
    (
        'IA : Informer les personnes concernées',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/ia-informer-les-personnes-concernees',
        '2025-02-07',
        'unknown',
    ),
    (
        'IA : Respecter et faciliter l’exercice des droits des personnes concernées',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/ia-respecter-lexercice-des-droits-des-personnes',
        '2025-02-07',
        'unknown',
    ),
    (
        'IA : Mobiliser la base légale de l’intérêt légitime pour développer un système d’IA',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/base-legale-interet-legitime-developpement-systeme',
        '2025-06-19',
        'unknown',
    ),
    (
        'La base légale de l’intérêt légitime : fiche focus sur les mesures à prendre en cas de collecte des données par moissonnage (web scraping)',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/focus-interet-legitime-collecte-par-moissonnage',
        '2025-06-19',
        'unknown',
    ),
    (
        'Développement des systèmes d’IA : les recommandations de la CNIL pour respecter le RGPD',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/developpement-des-systemes-dia-les-recommandations-de-la-cnil-pour-respecter-le-rgpd',
        '2025-07-22',
        'unknown',
    ),
    (
        'IA : Analyser le statut d’un modèle d’IA au regard du RGPD',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/ia-analyser-le-statut-dun-modele-dia-au-regard-du-rgpd',
        '2025-07-22',
        'unknown',
    ),
    (
        'IA : Annoter les données',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/ia-annoter-les-donnees',
        '2025-07-22',
        'unknown',
    ),
    (
        'IA : Garantir la sécurité du développement d’un système d’IA',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/ia-garantir-la-securite-du-developpement',
        '2025-07-22',
        'unknown',
    ),
    (
        'IA et santé : développer et évaluer des systèmes d’IA en conformité avec la réglementation',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/ia-et-sante-developper-et-evaluer-des-systemes-ia-conformes',
        '2026-03-05',
        'unknown',
    ),
    (
        'IA - Comment se mettre en conformité ?',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/ia-comment-se-mettre-en-conformite',
        'unknown',
        'unknown',
    ),
    (
        "Guide d'auto-évaluation pour les systèmes d'intelligence artificielle (IA)",
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/intelligence-artificielle/guide',
        'unknown',
        'unknown',
    ),
    (
        'Les fiches pratiques IA',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/les-fiches-pratiques-ia',
        'unknown',
        'unknown',
    ),
    (
        'Intelligence artificielle (IA)',
        "Commission nationale de l'informatique et des libertés",
        'https://www.cnil.fr/fr/particulier-intelligence-artificielle-ia',
        'unknown',
        'unknown',
    ),
]

REJECTED_URLS = [
    "https://example.com/intelligence-artificielle",
    "https://en.wikipedia.org/wiki/CNIL",
    "https://www.cnil.fr.example/fr/ia",
    "https://notcnil.fr/fr/ia",
    "https://evil.cnil.fr/fr/ia",
    "http://www.cnil.fr/fr/les-fiches-pratiques-ia",
    "https://user:pass@www.cnil.fr/fr/les-fiches-pratiques-ia",
    "https://www.cnil.fr/fr/les-fiches-pratiques-ia?utm_source=x",
    "https://www.cnil.fr/fr/les-fiches-pratiques-ia#section",
    "https://www.cnil.fr/fr",
    "https://www.cnil.fr/sites/default/files/2025-07/ia_liste_de_verification.pdf",
    "https://www.cnil.fr/fr/ia-liste.pdf",
    "https://www.cnil.fr/fr/admin/intelligence-artificielle",
    "https://127.0.0.1/fr/ia",
    "https://www.cnil.fr/search/intelligence-artificielle",
]


def test_catalog_rows_are_confirmed_cnil_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert catalog_path().name == "cnil_ai_pages.json"
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 35
    labels = []
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, publisher, url, published, rights = expected
        assert entry["title"] == title
        assert entry["publisher"] == publisher == PUBLISHER
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == rights == RIGHTS_UNKNOWN
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert official_cnil_host(url.split("/")[2])
        assert url.startswith("https://www.cnil.fr/fr/")
        labels.append(rights)
    assert labels.count(RIGHTS_UNKNOWN) == 35
    assert sum(entry["date"] == UNKNOWN_DATE for entry in entries) == 4


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    source = inspect.getsource(__import__("pdoom_pipeline.catalogs.cnil_ai", fromlist=["cnil_ai"]))
    assert "pdoom_pipeline.fetch" not in source
    assert "pdoom_pipeline.belief" not in source
    assert "p(doom)" not in source.casefold()


def test_catalog_file_stores_no_page_body():
    catalog = load_catalog()
    blob = catalog_path().read_text(encoding="utf-8")
    folded = blob.casefold()
    assert "p(doom)" not in folded
    assert "<p>" not in folded
    assert "<html" not in folded
    assert "doctype" not in folded
    assert "photographies publiées" not in folded
    assert "ctn-gen-auteur" not in folded
    for entry in catalog["entries"]:
        for value in entry.values():
            assert isinstance(value, str)
            assert len(value) <= MAX_FIELD_CHARS
            assert "<" not in value


def test_collector_is_not_wired():
    root = Path(__file__).resolve().parents[1]
    init_text = (root / "pipeline/pdoom_pipeline/catalogs/__init__.py").read_text(encoding="utf-8")
    assert "cnil" not in init_text.casefold()
    collect_text = (root / "pipeline/pdoom_pipeline/belief/collect.py").read_text(encoding="utf-8")
    assert "cnil_ai" not in collect_text
    assert "cnil_ai_pages" not in collect_text


def test_public_page_without_a_reuse_licence_stays_unknown():
    public = "<h1>Intelligence artificielle</h1><p>Cette page est publique.</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    copyright_notice = "<p>© CNIL. Tous droits réservés.</p>"
    assert rights_from_page(copyright_notice) == RIGHTS_UNKNOWN
    legal_link = '<footer><a href="/fr/mentions-legales">Mentions légales</a> <a href="/fr/informations-publiques">Informations publiques</a></footer>'
    assert rights_from_page(legal_link) == RIGHTS_UNKNOWN
    photos = "<p>constitué à partir de photographies publiées en ligne en licence ouverte sur le réseau social.</p>"
    assert rights_from_page(photos) == RIGHTS_UNKNOWN
    dataset = "<p>une obligation contractuelle dans la licence de réutilisation du jeu de données.</p>"
    assert rights_from_page(dataset) == RIGHTS_UNKNOWN
    model = "<p>Ce modèle peut être librement réutilisé conformément à la licence associée.</p>"
    assert rights_from_page(model) == RIGHTS_UNKNOWN
    software = "<p>placement sous licence libre du code informatique.</p>"
    assert rights_from_page(software) == RIGHTS_UNKNOWN
    third_party = "<p>sources tierces sous licence.</p>"
    assert rights_from_page(third_party) == RIGHTS_UNKNOWN
    restrictive = "<p>Mettre en place des licences restreignant les usages visant à réidentifier une personne.</p>"
    assert rights_from_page(restrictive) == RIGHTS_UNKNOWN
    lawful = "<p>Assurer que le traitement est licite - Définir une base légale.</p>"
    assert rights_from_page(lawful) == RIGHTS_UNKNOWN
    bare_code = "<p>The model card says CC-BY-NC-ND 4.0.</p>"
    assert rights_from_page(bare_code) == RIGHTS_UNKNOWN
    hidden = (
        "<script>mises à disposition selon les termes de la licence CC-BY-NC-ND 4.0 FR</script>"
        "<p>Aucun texte de licence.</p>"
    )
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_stated_reuse_licence_is_labeled_and_page_text_is_not_returned():
    cc_nc_nd = (
        "<p>Les textes sont mises à disposition selon les termes de la licence CC-BY-NC-ND 4.0 FR.</p>"
        + ("<p>page body</p>" * 30)
    )
    assert rights_from_page(cc_nc_nd) == RIGHTS_CC_BY_NC_ND_4_0
    assert "page body" not in rights_from_page(cc_nc_nd)
    cc_nd = "<p>contenus mis à disposition selon les termes de licence CC-BY-ND 4.0 FR.</p>"
    assert rights_from_page(cc_nd) == RIGHTS_CC_BY_ND_4_0
    ouverte = "<p>Les données sont mises à disposition par défaut selon les termes de la Licence ouverte.</p>"
    assert rights_from_page(ouverte) == RIGHTS_LICENCE_OUVERTE
    etalab = "<p>Conditions de réutilisation : licence ouverte ETALAB</p>"
    assert rights_from_page(etalab) == RIGHTS_LICENCE_OUVERTE
    creative = (
        "<p>Unless otherwise indicated, reuse is authorised under the "
        "Creative Commons Attribution 4.0 International (CC BY 4.0) licence.</p>"
    )
    assert rights_from_page(creative) == RIGHTS_CC_BY_4_0
    short = "<p>licensed under CC-BY 4.0</p>"
    assert rights_from_page(short) == RIGHTS_CC_BY_4_0
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = RIGHTS_LICENCE_OUVERTE
    validate_catalog(document)


def test_missing_dates_stay_unknown_and_the_title_date_wins():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page('<p class="date">27 août 2026</p>') == UNKNOWN_DATE
    assert date_from_page("<p class='ctn-gen-auteur'>CNIL</p>") == UNKNOWN_DATE
    assert date_from_page("<p class='ctn-gen-auteur'>Mis à jour le 08 avril 2024</p>") == UNKNOWN_DATE
    hidden = "<script><p class='ctn-gen-auteur'>08 avril 2024</p></script><p>No date.</p>"
    assert date_from_page(hidden) == UNKNOWN_DATE
    stated = (
        '<p class="date">27 août 2026</p>'
        "<h1>Titre</h1>"
        "<p class='ctn-gen-auteur'>08 avril 2024</p>"
    )
    assert date_from_page(stated) == "2024-04-08"
    assert date_from_page("<p class='ctn-gen-auteur'>07 février 2025</p>") == "2025-02-07"
    assert date_from_page("<p class='ctn-gen-auteur'>22 juillet 2025</p>") == "2025-07-22"
    assert date_from_page("<p class='ctn-gen-auteur'>05 mars 2026</p>") == "2026-03-05"
    assert date_from_page("<p class='ctn-gen-auteur'>31 février 2024</p>") == UNKNOWN_DATE
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("08 avril 2024")
    with pytest.raises(CatalogError):
        validate_date("2024-04-31")


def test_page_record_stores_metadata_without_the_body():
    page = """
    <html><head>
      <meta property="og:title" content="Les fiches pratiques IA | CNIL" />
      <link rel="canonical" href="https://www.cnil.fr/fr/les-fiches-pratiques-ia" />
    </head><body>
      <p class="date">27 août 2026</p>
      <h1>Les fiches pratiques IA</h1>
      <p class="ctn-gen-auteur">08 avril 2024</p>
      <article>
    """ + ("full page text about artificial intelligence. " * 40) + """
      </article>
      <p>photographies publiées en ligne en licence ouverte sur le réseau social.</p>
    </body></html>
    """
    record = page_record(page, page_url="https://cnil.fr/fr/somewhere-else")
    assert record == {
        "title": "Les fiches pratiques IA",
        "publisher": PUBLISHER,
        "canonical_url": "https://www.cnil.fr/fr/les-fiches-pratiques-ia",
        "date": "2024-04-08",
        "rights": RIGHTS_UNKNOWN,
    }
    assert "full page text" not in str(record)
    assert title_from_page("<title>IA : Définir une finalité | CNIL</title>") == "IA : Définir une finalité"
    offsite = '<link rel="canonical" href="https://example.com/ai"><meta property="og:title" content="Titre">'
    fetched = "https://www.cnil.fr/fr/les-fiches-pratiques-ia"
    assert canonical_url_from_page(offsite, page_url=fetched) == fetched


def test_non_cnil_urls_are_rejected_and_official_hosts_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [
        "https://www.cnil.fr/fr/les-fiches-pratiques-ia",
        "https://cnil.fr/fr/les-fiches-pratiques-ia",
        "https://www.cnil.fr/en/artificial-intelligence",
    ]
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_cnil_host("www.cnil.fr")
    assert official_cnil_host("cnil.fr")
    assert not official_cnil_host("www.cnil.fr.example")
    assert not official_cnil_host("notcnil.fr")
    assert not official_cnil_host("evil.cnil.fr")


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
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["title"] = "x" * (MAX_FIELD_CHARS + 1)
    with pytest.raises(CatalogError, match="short plain-text"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["date"] = "08 avril 2024"
    with pytest.raises(CatalogError):
        validate_catalog(document)
