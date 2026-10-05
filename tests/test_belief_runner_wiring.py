"""Source contract for the belief runner in collect.py.

collect_beliefs references RssCollector. That function does not reference the
ForumMagnum, Bluesky, YouTube, OpenReview, Hugging Face, Crossref, Semantic
Scholar, arXiv, GitHub, or OpenAlex collectors. The file does not assign
runner_wired true.
"""

from __future__ import annotations

import ast
from pathlib import Path

COLLECT_PY = Path(__file__).resolve().parents[1] / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py"

# Names as they appear in collector classes and in prose inside the function.
_OTHER_COLLECTORS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ForumMagnum", ("forummagnum",)),
    ("Bluesky", ("bluesky",)),
    ("YouTube", ("youtube",)),
    ("OpenReview", ("openreview",)),
    ("Hugging Face", ("hugging face", "huggingface")),
    ("Crossref", ("crossref",)),
    ("Semantic Scholar", ("semantic scholar", "semanticscholar")),
    ("arXiv", ("arxiv",)),
    ("GitHub", ("github",)),
    ("OpenAlex", ("openalex",)),
)


def _function_source(source: str, name: str) -> str | None:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name and node.end_lineno is not None:
            return "".join(lines[node.lineno - 1 : node.end_lineno])
    return None


def _other_collector_references(function_source: str) -> list[str]:
    found = []
    for label, needles in _OTHER_COLLECTORS:
        hits = [line.strip() for line in function_source.splitlines() if any(needle in line.casefold() for needle in needles)]
        if hits:
            found.append(f"{label} ({'; '.join(hits[:3])})")
    return found


def _runner_wired_true_assignments(source: str) -> list[str]:
    """Lines that assign runner_wired the boolean True. Comments are not assignments."""
    tree = ast.parse(source)
    lines = source.splitlines()
    found: list[str] = []

    def record(node: ast.AST) -> None:
        found.append(lines[node.lineno - 1].strip())

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(_targets_runner_wired(target) for target in node.targets) and _is_true(node.value):
                record(node)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            if _targets_runner_wired(node.target) and _is_true(node.value):
                record(node)
        elif isinstance(node, ast.keyword) and node.arg == "runner_wired" and _is_true(node.value):
            record(node)
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "runner_wired" and _is_true(value):
                    record(node)
    return found


def _targets_runner_wired(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "runner_wired"
    if isinstance(node, ast.Attribute):
        return node.attr == "runner_wired"
    if isinstance(node, ast.Subscript):
        return _targets_runner_wired(node.value)
    if isinstance(node, (ast.Tuple, ast.List)):
        return any(_targets_runner_wired(element) for element in node.elts)
    return False


def _is_true(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _violations(source: str) -> list[str]:
    violations: list[str] = []
    try:
        function_source = _function_source(source, "collect_beliefs")
    except SyntaxError as exc:
        return [
            f"pipeline/pdoom_pipeline/belief/collect.py does not parse ({exc}). "
            "collect_beliefs cannot be checked for RssCollector."
        ]
    if function_source is None:
        violations.append("collect_beliefs is missing, so the function does not reference RssCollector.")
    else:
        if "RssCollector" not in function_source:
            violations.append("collect_beliefs does not reference RssCollector.")
        referenced = _other_collector_references(function_source)
        if referenced:
            violations.append(
                "collect_beliefs references unwired collectors: " + ", ".join(referenced) + "."
            )
    try:
        assigned = _runner_wired_true_assignments(source)
    except SyntaxError:
        assigned = []
    if assigned:
        violations.append(
            "runner_wired is assigned true in pipeline/pdoom_pipeline/belief/collect.py: "
            + "; ".join(assigned)
        )
    return violations


def test_collect_beliefs_references_rss_only_and_runner_wired_is_not_true():
    source = COLLECT_PY.read_text(encoding="utf-8")
    violations = _violations(source)
    assert not violations, (
        "Current violation in pipeline/pdoom_pipeline/belief/collect.py. "
        "Production was not changed.\n- " + "\n- ".join(violations)
    )
