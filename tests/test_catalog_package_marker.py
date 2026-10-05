"""The catalogs package stays a marker; its modules and JSON files stay reachable."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py"

FORBIDDEN_IMPORTS = ("congress_hearings", "uk_ogl", "us_federal")

CATALOG_LOADERS = {
    "pdoom_pipeline.catalogs.congress_hearings": "load_hearings",
    "pdoom_pipeline.catalogs.uk_ogl": "load_catalog",
    "pdoom_pipeline.catalogs.us_federal": "load_catalog",
}

CATALOG_FILES = (
    ROOT / "data" / "catalogs" / "us_congress_ai_hearings.json",
    ROOT / "data" / "catalogs" / "uk_ogl_ai_safety.json",
    ROOT / "data" / "catalogs" / "us_federal_ai_publications.json",
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


def test_catalogs_init_is_a_package_marker_without_catalog_imports():
    source = INIT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert ast.get_docstring(tree) == "Package marker."
    assert len(tree.body) == 1
    imported = _imported_names(tree)
    for name in FORBIDDEN_IMPORTS:
        assert name not in imported
        assert name not in source


def test_catalog_modules_import_directly_and_expose_loaders():
    for module_name, loader_name in CATALOG_LOADERS.items():
        module = importlib.import_module(module_name)
        assert Path(module.__file__).name == module_name.rsplit(".", 1)[-1] + ".py"
        loader = getattr(module, loader_name)
        assert callable(loader)


def test_catalog_json_files_are_present():
    for path in CATALOG_FILES:
        assert path.is_file()
        assert path.stat().st_size > 0
