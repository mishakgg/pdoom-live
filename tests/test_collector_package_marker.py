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
    "crossref",
    "forum_magnum",
    "github",
    "huggingface",
    "openalex_works",
    "openreview",
    "rss",
    "semantic_scholar",
    "youtube_metadata",
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


def test_rss_collector_imports_directly():
    module = importlib.import_module("pdoom_pipeline.collectors.rss")
    assert Path(module.__file__).name == "rss.py"
    assert callable(module.RssCollector)
