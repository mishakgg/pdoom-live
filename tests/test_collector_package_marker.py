"""The collectors package stays a marker; collector modules stay importable directly."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "pipeline" / "pdoom_pipeline" / "collectors" / "__init__.py"

COLLECTOR_MODULES = (
    "arxiv",
    "base",
    "bluesky",
    "cordis",
    "crossref",
    "dblp",
    "forum_magnum",
    "github",
    "huggingface",
    "internet_archive",
    "medrxiv",
    "nsf_awards",
    "oecd_ai",
    "openalex_works",
    "openreview",
    "rss",
    "semantic_scholar",
    "youtube_metadata",
    "zenodo",
)

COLLECTOR_CLASSES = (
    "ArxivCollector",
    "BlueskyCollector",
    "CordisCollector",
    "CrossrefCollector",
    "DblpCollector",
    "ForumMagnumCollector",
    "GitHubCollector",
    "HuggingFaceCollector",
    "InternetArchiveCollector",
    "MedrxivCollector",
    "NsfAwardsCollector",
    "OecdAiCollector",
    "OpenAlexWorksCollector",
    "OpenReviewCollector",
    "RssCollector",
    "SemanticScholarCollector",
    "YouTubeMetadataCollector",
    "ZenodoCollector",
)


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
                names.add(alias.asname or "")
                names.update(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
                names.update(node.module.split("."))
            for alias in node.names:
                names.add(alias.name)
                names.add(alias.asname or "")
    names.discard("")
    return names


def test_collectors_init_is_a_package_marker_without_collector_imports():
    source = INIT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert ast.get_docstring(tree) == "Package marker."
    assert len(tree.body) == 1
    imported = _imported_names(tree)
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
    for name in COLLECTOR_MODULES:
        assert name not in imported
        assert name not in source


def test_importing_collectors_does_not_reexport_classes():
    found = {path.stem for path in INIT.parent.glob("*.py") if path.name != "__init__.py"}
    assert found == set(COLLECTOR_MODULES)
    collectors = importlib.import_module("pdoom_pipeline.collectors")
    assert not hasattr(collectors, "__all__")
    bound_collectors = sorted(
        name
        for name, value in vars(collectors).items()
        if isinstance(value, type) and name.endswith("Collector")
    )
    assert bound_collectors == []
    for name in COLLECTOR_CLASSES:
        assert not hasattr(collectors, name)


def test_rss_collector_imports_directly():
    module = importlib.import_module("pdoom_pipeline.collectors.rss")
    assert Path(module.__file__).name == "rss.py"
    assert callable(module.RssCollector)
