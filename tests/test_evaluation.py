"""The fixed corpus must improve every error class without rewarding volume."""

import json
from pathlib import Path

from pdoom_pipeline.belief.evaluate import CLASSES, evaluate_corpus

BASELINE = Path("data/fixtures/evaluation/baseline.json")
RESULTS = Path("data/fixtures/evaluation/results.json")


def test_evaluation_reduces_every_error_class():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    saved = json.loads(RESULTS.read_text(encoding="utf-8"))
    improved = evaluate_corpus()
    assert set(CLASSES) <= set(baseline["errors_by_class"])
    assert improved["error_total"] < baseline["error_total"]
    assert improved["error_total"] == 0
    for name in CLASSES:
        assert improved["errors_by_class"][name] == 0
        assert improved["errors_by_class"][name] <= baseline["errors_by_class"][name]
        assert saved["errors_by_class"][name] == 0
    assert saved["error_total"] == 0
    assert baseline["error_total"] == 30
