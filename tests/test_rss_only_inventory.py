"""Belief collection stays on RssCollector.

The belief module imports that class from its own module. The belief job does
not import collector classes. Bluesky, ForumMagnum, and the metadata collectors
stay out of both files, and runner_wired stays false.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
BELIEF_COLLECT = ROOT / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py"
COLLECT_BELIEFS = ROOT / "pipeline" / "pdoom_pipeline" / "jobs" / "collect_beliefs.py"
COLLECTORS = ROOT / "pipeline" / "pdoom_pipeline" / "collectors"
COHORT_WRITER = ROOT / "pipeline" / "pdoom_pipeline" / "seed" / "cohort_2026_10.py"
COHORT_SOURCES = ROOT / "data" / "seed" / "cohort" / "v2026-10" / "sources.jsonl"
BELIEF_FILES = (BELIEF_COLLECT, COLLECT_BELIEFS)


class ImportBinding(NamedTuple):
    module: str
    name: str
    bound: str


def _collector_classes() -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(COLLECTORS.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module = f"pdoom_pipeline.collectors.{path.stem}"
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name.endswith("Collector"):
                found[node.name] = module
    return found


def _bindings(path: Path) -> list[ImportBinding]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[ImportBinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = f"{'.' * node.level}{node.module or ''}"
            for alias in node.names:
                found.append(ImportBinding(module, alias.name, alias.asname or alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.append(ImportBinding(alias.name, "", alias.asname or alias.name.rsplit(".", 1)[-1]))
    return found


def _touches_collectors(binding: ImportBinding) -> bool:
    return "collectors" in binding.module.split(".")


def _is_true(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _runner_wired_true_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines: list[int] = []
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        if targets and _is_true(value):
            for target in targets:
                named = isinstance(target, ast.Name) and target.id == "runner_wired"
                attributed = isinstance(target, ast.Attribute) and target.attr == "runner_wired"
                if named or attributed:
                    lines.append(node.lineno)
        if isinstance(node, ast.keyword) and node.arg == "runner_wired" and _is_true(node.value):
            lines.append(node.lineno)
        if isinstance(node, ast.Dict):
            for key, item in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "runner_wired" and _is_true(item):
                    lines.append(node.lineno)
    return lines


def test_belief_collection_imports_rss_collector_from_its_module():
    bindings = _bindings(BELIEF_COLLECT)
    rss = [row for row in bindings if row.module == "pdoom_pipeline.collectors.rss" and row.name == "RssCollector"]
    assert rss == [ImportBinding("pdoom_pipeline.collectors.rss", "RssCollector", "RssCollector")]
    collector_imports = [row for row in bindings if _touches_collectors(row)]
    assert collector_imports == rss

    import pdoom_pipeline.belief.collect as belief_collect
    from pdoom_pipeline.collectors.rss import RssCollector

    assert belief_collect.RssCollector is RssCollector


def test_belief_files_do_not_import_other_collectors():
    classes = _collector_classes()
    assert classes["RssCollector"] == "pdoom_pipeline.collectors.rss"
    forbidden = set(classes) - {"RssCollector"}
    assert "BlueskyCollector" in forbidden
    assert "ForumMagnumCollector" in forbidden
    metadata = forbidden - {"BlueskyCollector", "ForumMagnumCollector"}
    assert metadata

    import pdoom_pipeline.belief.collect as belief_collect
    import pdoom_pipeline.jobs.collect_beliefs as collect_beliefs

    for path in BELIEF_FILES:
        bindings = _bindings(path)
        collector_imports = [row for row in bindings if _touches_collectors(row)]
        if path == BELIEF_COLLECT:
            assert collector_imports == [ImportBinding("pdoom_pipeline.collectors.rss", "RssCollector", "RssCollector")]
        else:
            assert collector_imports == []
        imported = {row.name for row in bindings} | {row.bound for row in bindings}
        overlap = sorted(imported & forbidden)
        assert overlap == [], f"{path.name} imports {overlap}"

    for name in sorted(forbidden):
        assert not hasattr(belief_collect, name)
        assert not hasattr(collect_beliefs, name)


def test_runner_wired_stays_false():
    for path in (*BELIEF_FILES, COHORT_WRITER, *sorted(COLLECTORS.glob("*.py"))):
        assert _runner_wired_true_lines(path) == [], path.relative_to(ROOT).as_posix()
    writer = COHORT_WRITER.read_text(encoding="utf-8")
    assert '"runner_wired": False' in writer
    rows = [json.loads(line) for line in COHORT_SOURCES.read_text(encoding="utf-8").splitlines() if line.strip()]
    flagged = [row for row in rows if "runner_wired" in row]
    assert flagged
    assert all(row["runner_wired"] is False for row in flagged)
