"""One explicitly released metadata pilot under the guarded refresh write seam."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import inspect
import json
import os
from pathlib import Path

from .scratch import BoundedScratch, CHUNK_BYTES, StorageStop
from .supervisor import Artifact, CHECKPOINT, PENDING, DrivePin, Supervisor

PIN_KEYS = ("id", "canonical_url", "collection_method", "review_state", "rights_notes",
            "verification_method", "owner_person_id", "enabled", "continuously_collectible")


def admitted_sources(registry_sources: list[dict]) -> list[dict]:
    pins = json.loads(Path(__file__).with_name("pilot_sources.json").read_text(encoding="utf-8"))
    by_id = {}
    for source in registry_sources:
        if source["id"] in by_id:
            raise StorageStop("duplicate registry source identity")
        by_id[source["id"]] = source
    selected = []
    for pin in pins:
        row = by_id.get(pin["id"])
        if not row or {k: row.get(k) for k in PIN_KEYS} != pin:
            raise StorageStop("pilot identity, URL, method or rights policy differs from reviewed pin")
        if row.get("collection_policy") is not None or row.get("allowed_fetch_origins") not in (None, []):
            raise StorageStop("pilot structured rights/origin policy requires a new reviewed pin")
        selected.append({**row, "collection_policy": {"admitted": True, "rights_basis": row["rights_notes"],
                                                        "evidence": False, "extraction": False}})
    if len(selected) != 8:
        raise StorageStop("pilot requires exactly eight admitted feeds")
    return selected


def gateway_sink(scratch: BoundedScratch):
    runner = scratch.path("runner")
    def write_bytes(target: Path, payload: bytes) -> None:
        target = Path(target)
        if not target.is_absolute():
            raise StorageStop("runner sink requires an absolute target")
        # Lexical check first so an escaping caller does not trigger unrelated path reads.
        if not target.is_relative_to(runner):
            raise StorageStop("runner write target escapes collection/runner")
        relative = target.relative_to(scratch.root).as_posix()
        scratch.path(relative)
        if not isinstance(payload, bytes):
            raise StorageStop("runner sink payload must be serialized bytes")
        chunks = (payload[i:i+CHUNK_BYTES] for i in range(0, len(payload), CHUNK_BYTES))
        scratch.atomic_bytes(relative, chunks, max_bytes=len(payload))
    return write_bytes


@contextmanager
def _environment(scratch):
    values = scratch.runtime_environment()
    saved = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _snapshot(scratch: BoundedScratch, sources: list[dict]) -> tuple[list[Artifact], list[str]]:
    decision = json.dumps([{k: source[k] for k in PIN_KEYS} for source in sources], sort_keys=True).encode()
    retention = {"admitted": True, "mode": "metadata", "decision_id": hashlib.sha256(decision).hexdigest(),
                 "rights_basis": {source["id"]: source["rights_notes"] for source in sources},
                 "evidence": False, "extraction": False, "public_import": False}
    paths = sorted(p for p in scratch.path("runner").rglob("*") if p.is_file())
    artifacts, clean = [], []
    for index, p in enumerate(paths):
        relative = p.relative_to(scratch.root).as_posix()
        scratch.path(relative)
        if p.name.endswith((".writing", ".tmp")) or "bodies" in p.parts:
            raise StorageStop("pilot contains incomplete or disallowed raw cache files")
        if not p.stat().st_size:
            # Empty JSONL contains no material; exclude from upload but clean after verified commit.
            clean.append(relative)
            continue
        sha = hashlib.sha256()
        with p.open("rb") as handle:
            while data := handle.read(CHUNK_BYTES):
                sha.update(data)
        def chunks(path=p):
            with path.open("rb") as handle:
                while data := handle.read(CHUNK_BYTES):
                    yield data
        artifacts.append(Artifact(f"{index:02d}-{p.name}", p.stat().st_size, sha.hexdigest(),
                                  {**retention, "runner_relative_path": relative}, chunks))
        clean.append(relative)
    return artifacts, clean


def run_metadata_pilot(*, scratch: BoundedScratch, drive, pin: DrivePin, seed_dir: Path,
                       people: list[dict], registry_sources: list[dict], released: bool = False,
                       refresh=None, fetcher=None, cancelled=None, now=None) -> dict:
    """No scheduler/import. Caller must hold lease, supply OAuth and release proof."""
    if not released:
        raise StorageStop("parent release is required for the one-time metadata pilot")
    sources = admitted_sources(registry_sources)
    supervisor = Supervisor(scratch, drive, pin)
    supervisor.preflight(128 * 1024 * 1024)
    checkpoint = scratch.read_json(CHECKPOINT)
    if checkpoint and checkpoint.get("cursor_after", {}).get("kind") == "metadata-pilot":
        return supervisor.resume()
    if scratch.read_json(PENDING):
        pending = scratch.read_json(PENDING)
        if pending["phase"] != "preparing":
            return supervisor.resume()
        artifacts, clean = _snapshot(scratch, sources)
        return supervisor.submit(artifacts, cursor_after=pending["cursor_after"], cleanup_inputs=clean)
    if not checkpoint or checkpoint.get("cursor_after") != {"kind": "drive-smoke", "synthetic": True}:
        raise StorageStop("verified synthetic Drive smoke checkpoint is required before fetching")
    if refresh is None:
        from pdoom_pipeline.refresh.runner import run_refresh
        refresh = run_refresh
    if "write_bytes" not in inspect.signature(refresh).parameters:
        raise StorageStop("refresh runner lacks required bounded write hook")
    seed_dir = Path(seed_dir)
    from .scratch import validate_windows_path, _plain
    validate_windows_path(str(seed_dir))
    _plain(seed_dir)
    sink = gateway_sink(scratch)
    def stop():
        if cancelled and cancelled():
            return True
        try:
            scratch.check_write(0)
        except StorageStop:
            return True
        return False
    with _environment(scratch):
        result = refresh(seed_dir=seed_dir, collection_dir=scratch.path("runner"),
                         people=people, leads=[], registry_sources=sources, fetcher=fetcher,
                         include_belief=False, include_adapters=True, max_sources=8, max_seconds=300,
                         cancelled=stop, now=now, write_bytes=sink)
    if result.get("status") not in {"succeeded", "partial", "failed", "interrupted", "skipped"}:
        raise StorageStop("runner returned an unknown outcome")
    # Even a failed run may have useful bounded diagnostics; never relabel it success.
    publication = result.get("publication", {"imported": False, "public_revocations_applied": False})
    if publication.get("imported") is not False or publication.get("public_revocations_applied") is not False:
        raise StorageStop("pilot runner crossed the private publication boundary")
    outcome = {"kind": "metadata-pilot", "status": result["status"], "counts": result["counts"],
               "cursor": result.get("cursor"), "public_import": False, "publication": publication,
               "policy_decisions": result.get("policy_decisions", [])}
    sink(scratch.path("runner/pilot-outcome.json"), json.dumps(outcome, sort_keys=True).encode())
    artifacts, clean = _snapshot(scratch, sources)
    return supervisor.submit(artifacts, cursor_after=outcome, cleanup_inputs=clean)
