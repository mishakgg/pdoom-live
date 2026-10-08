"""Explicit POSIX configuration with real local files and synthetic remote I/O only."""
from dataclasses import replace
import os
from pathlib import Path, PureWindowsPath
import shutil
import stat
import subprocess
import sys

import pytest

from test_collection_storage import FakeDrive, PIN, artifact, registry
from pdoom_pipeline.collection_storage.bootstrap import synthetic_smoke
from pdoom_pipeline.collection_storage.pilot import run_metadata_pilot
from pdoom_pipeline.collection_storage.readiness import report
from pdoom_pipeline.collection_storage.scratch import (
    BoundedScratch, CHUNK_BYTES, HARD_MAX_BYTES, METADATA_RESERVE, ScratchPaths, StorageStop,
)
from pdoom_pipeline.collection_storage.supervisor import CHECKPOINT, PENDING, Supervisor

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX host layout")


@pytest.fixture
def paths(tmp_path):
    seed = tmp_path / "seed"
    seed.mkdir()
    return ScratchPaths(mode="posix", workspace_base=tmp_path,
                        collection_root=tmp_path / "collection", seed_root=seed)


def bounded(paths, **kwargs):
    return BoundedScratch(paths=paths, free_bytes=lambda p: 10**12, **kwargs)


def test_layout_and_readiness_are_read_only_and_no_implicit_posix_fallback(paths):
    assert paths.validate() == paths.collection_root
    result = report(paths)
    assert result["storage_mode"] == "posix"
    assert result["scratch_root"] == str(paths.collection_root)
    assert result["seed_root"] == str(paths.seed_root)
    assert result["hard_max_bytes"] == 25_000_000_000
    assert result["min_free_bytes"] == 5_000_000_000
    assert result["batch_max_bytes"] == 128 * 1024 * 1024
    assert result["batch_max_files"] == 32
    assert result["runner_write_hook_available"] is True
    assert result["status"] == "blocked_for_live_pilot"
    assert not result["continuous_collection_enabled"]
    assert not result["schedule_enabled"] and not result["public_import_enabled"]
    assert not paths.collection_root.exists()
    with pytest.raises(StorageStop, match="native absolute Windows"):
        BoundedScratch()
    with pytest.raises(StorageStop):
        ScratchPaths(mode="posix").validate()
    with pytest.raises(StorageStop):
        ScratchPaths(mode="windows", collection_root=paths.collection_root).validate()


@pytest.mark.parametrize("field,value", [
    ("mode", "auto"), ("workspace_base", Path("relative")),
    ("collection_root", Path("relative")), ("seed_root", Path("relative")),
    ("collection_root", Path("/outside/collection")),
    ("seed_root", Path("/outside/seed")), ("collection_root", Path("//server/collection")),
    ("collection_root", Path(r"F:\CodexTaskScratch\pdoom-live\collection")),
])
def test_invalid_or_uncontained_layouts_fail_before_creation(paths, field, value):
    with pytest.raises(StorageStop):
        replace(paths, **{field: value}).validate()
    assert not paths.collection_root.exists()


@pytest.mark.parametrize("shape", ["base", "same", "seed-in-scratch", "scratch-in-seed", "traversal", "missing-parent"])
def test_roots_are_distinct_dedicated_and_traversal_free(paths, shape):
    changed = {
        "base": replace(paths, collection_root=paths.workspace_base),
        "same": replace(paths, collection_root=paths.seed_root),
        "seed-in-scratch": replace(paths, seed_root=paths.collection_root / "seed"),
        "scratch-in-seed": replace(paths, collection_root=paths.seed_root / "scratch"),
        "traversal": replace(paths, collection_root=paths.workspace_base / "x/../collection"),
        "missing-parent": replace(paths, collection_root=paths.workspace_base / "absent/collection"),
    }[shape]
    with pytest.raises(StorageStop):
        changed.validate()
    assert not paths.collection_root.exists()


def test_new_scratch_files_and_nested_directories_are_private(paths):
    with bounded(paths) as scratch:
        scratch.atomic_bytes("runner/state/deep/value", [b"fixture"], max_bytes=7)
        for p in [scratch.root, *scratch.root.rglob("*")]:
            assert p.stat().st_uid == os.geteuid()
            assert stat.S_IMODE(p.stat().st_mode) == (0o700 if p.is_dir() else 0o600)
        assert all(Path(value).is_relative_to(scratch.root)
                   for key, value in scratch.runtime_environment().items()
                   if key not in {"PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE"})
        with pytest.raises(StorageStop, match="another collection writer"):
            with bounded(paths):
                pytest.fail("a second writer acquired the lease")
    with bounded(paths) as scratch:
        assert scratch.path("runner/state/deep/value").read_bytes() == b"fixture"


@pytest.mark.parametrize("target", ["workspace", "seed", "root", "nested", "file"])
def test_unsafe_existing_permissions_stop_without_chmod(paths, target):
    if target in {"nested", "file"}:
        with bounded(paths) as scratch:
            scratch.atomic_bytes("runner/value", [b"safe"], max_bytes=4)
        node = paths.collection_root / ("runner" if target == "nested" else "runner/value")
    elif target == "root":
        paths.collection_root.mkdir(mode=0o700)
        node = paths.collection_root
    else:
        node = paths.workspace_base if target == "workspace" else paths.seed_root
    mode = 0o777 if target in {"workspace", "seed"} else 0o755 if node.is_dir() else 0o644
    node.chmod(mode)
    with pytest.raises(StorageStop, match="private|writable"):
        with bounded(paths):
            pytest.fail("unsafe permissions accepted")
    assert stat.S_IMODE(node.stat().st_mode) == mode


def test_wrong_owner_stops_without_mutation(paths, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: paths.workspace_base.stat().st_uid + 1)
    with pytest.raises(StorageStop, match="owned"):
        bounded(paths)
    assert not paths.collection_root.exists()


@pytest.mark.parametrize("location", ["scratch-root", "scratch-child", "seed-root", "seed-child", "workspace-alias"])
def test_symlink_roots_and_children_are_rejected(paths, location):
    outside = paths.workspace_base / "unrelated"
    outside.mkdir()
    (outside / "sentinel").write_bytes(b"untouched")
    if location == "scratch-root":
        paths.collection_root.symlink_to(outside, target_is_directory=True)
    elif location == "scratch-child":
        paths.collection_root.mkdir(mode=0o700)
        (paths.collection_root / "escape").symlink_to(outside, target_is_directory=True)
    elif location == "seed-root":
        alias = paths.workspace_base / "seed-alias"
        alias.symlink_to(paths.seed_root, target_is_directory=True)
        paths = replace(paths, seed_root=alias)
    elif location == "seed-child":
        (paths.seed_root / "escape").symlink_to(outside, target_is_directory=True)
    else:
        alias = paths.workspace_base / "alias"
        alias.symlink_to(paths.seed_root, target_is_directory=True)
        paths = replace(paths, collection_root=alias / "collection")
    with pytest.raises(StorageStop, match="link"):
        with bounded(paths):
            paths.validate_seed(paths.seed_root)
    assert (outside / "sentinel").read_bytes() == b"untouched"


@pytest.mark.parametrize("location", ["writer.lock", "state/data", "state/data.writing", "seed"])
def test_hardlinks_are_rejected_before_write_or_cleanup(paths, location):
    original = paths.workspace_base / "outside"
    original.write_bytes(b"untouched")
    original.chmod(0o600)
    with bounded(paths) as scratch:
        target = paths.seed_root / "link" if location == "seed" else scratch.path(location)
        target.unlink(missing_ok=True)
        os.link(original, target)
        with pytest.raises(StorageStop, match="hard links"):
            if location == "seed":
                paths.validate_seed(paths.seed_root)
            else:
                scratch.atomic_bytes("state/data", [b"x"], max_bytes=1)
        assert original.read_bytes() == b"untouched"
        assert target.exists()


def test_special_files_are_rejected(paths):
    with bounded(paths) as scratch:
        os.mkfifo(scratch.root / "fifo", mode=0o600)
        with pytest.raises(StorageStop, match="ordinary"):
            scratch.check_write(0)


def test_posix_keeps_cap_copy_accounting_reserve_and_stream_limits(paths):
    with pytest.raises(StorageStop, match="budget"):
        bounded(paths, max_bytes=HARD_MAX_BYTES + 1)
    with bounded(paths, max_bytes=METADATA_RESERVE + 15) as scratch:
        scratch.atomic_bytes("value", [b"12345678"], max_bytes=8)
        with pytest.raises(StorageStop, match="cap"):
            scratch.atomic_bytes("value", [b"12345678"], max_bytes=8)
        assert scratch.path("value").read_bytes() == b"12345678"
        scratch.free_bytes = lambda _: 5_000_000_002
        with pytest.raises(StorageStop, match="disk reserve"):
            scratch.atomic_bytes("other", [b"abc"], max_bytes=3)
        assert not scratch.path("other").exists()
    with bounded(paths) as scratch:
        with pytest.raises(StorageStop, match="memory bound"):
            scratch.atomic_bytes("large", [b"x" * (CHUNK_BYTES + 1)], max_bytes=CHUNK_BYTES + 1)
        assert not scratch.path("large.writing").exists()


def test_free_space_is_rechecked_between_disk_chunks(paths):
    with bounded(paths) as scratch:
        def chunks():
            yield b"first"
            scratch.free_bytes = lambda _: 5_000_000_000
            yield b"second"
        with pytest.raises(StorageStop, match="disk reserve"):
            scratch.atomic_bytes("value", chunks(), max_bytes=11)
        assert not scratch.path("value").exists()
        assert not scratch.path("value.writing").exists()


def test_seed_mismatch_fails_before_refresh_and_same_pilot_is_one_shot(paths):
    called = []
    def refresh(*, write_bytes, **kwargs):
        called.append(kwargs)
        assert kwargs["seed_dir"] == paths.seed_root
        assert kwargs["max_sources"] == len(kwargs["registry_sources"]) == 8
        assert kwargs["include_belief"] is False and kwargs["max_seconds"] == 300
        write_bytes(kwargs["collection_dir"] / "state/value.json", b'{"fixture":true}')
        return {"status": "partial", "counts": {"new": 7, "failed": 1}}
    drive = FakeDrive()
    with bounded(paths) as scratch:
        synthetic_smoke(scratch, drive, PIN)
        args = dict(scratch=scratch, drive=drive, pin=PIN, people=[], registry_sources=registry(),
                    refresh=refresh, released=True)
        with pytest.raises(StorageStop, match="configured seed"):
            run_metadata_pilot(seed_dir=paths.workspace_base, **args)
        assert not called
        result = run_metadata_pilot(seed_dir=paths.seed_root, **args)
        assert result["cursor_after"]["status"] == "partial"
        assert result["cursor_after"]["public_import"] is False
        assert run_metadata_pilot(seed_dir=paths.seed_root, **args) == result
        assert len(called) == 1
        assert not scratch.path(PENDING).exists()


def test_posix_actual_runner_manifest_failure_resume_and_full_quota_cleanup(paths, monkeypatch):
    from test_collection_storage_runner import NOW, REGISTRY, SEED
    from pdoom_pipeline.fetch import FetchResult, SafeFetcher
    from pdoom_pipeline.refresh.runner import run_refresh
    shutil.copytree(SEED, paths.seed_root, dirs_exist_ok=True)
    called = []
    def transport(url, headers):
        called.append(url)
        return FetchResult(url=url, status=200, headers={"content-type": "application/rss+xml"},
                           body=b'<rss version="2.0"><channel><title>Synthetic</title></channel></rss>')
    client = SafeFetcher(transport=transport, sleep=lambda _: None)
    drive = FakeDrive()
    args = dict(drive=drive, pin=PIN, seed_dir=paths.seed_root, people=[], registry_sources=REGISTRY,
                refresh=run_refresh, fetcher=client, released=True, now=NOW)
    with bounded(paths) as scratch:
        smoke = synthetic_smoke(scratch, drive, PIN)
        drive.fail_manifest = True
        with pytest.raises(StorageStop, match="manifest interruption"):
            run_metadata_pilot(scratch=scratch, **args)
        assert scratch.read_json(CHECKPOINT) == smoke
        assert len(called) == 8
        assert list(scratch.path("runner").rglob("*.json"))
    drive.fail_manifest = False
    with bounded(paths) as scratch:
        def fail_cleanup(self, pending):
            raise StorageStop("synthetic cleanup crash")
        with monkeypatch.context() as fault:
            fault.setattr(Supervisor, "_cleanup", fail_cleanup)
            with pytest.raises(StorageStop, match="cleanup crash"):
                run_metadata_pilot(scratch=scratch, **args)
        assert scratch.read_json(CHECKPOINT)["cursor_after"]["kind"] == "metadata-pilot"
    drive.quota["usage"] = drive.quota["limit"]
    with bounded(paths) as scratch:
        result = run_metadata_pilot(scratch=scratch, **args)
        assert result["cursor_after"]["kind"] == "metadata-pilot"
        assert not scratch.path(PENDING).exists()
        assert not list(scratch.path("runner").rglob("*.json"))
        assert len(called) == 8
        assert scratch.usage() < METADATA_RESERVE


@pytest.mark.parametrize("target", ["seed", "scratch-child"])
def test_unreadable_directories_cannot_escape_validation_or_accounting(paths, target):
    with bounded(paths) as scratch:
        directory = paths.seed_root if target == "seed" else scratch.path("state")
        directory.chmod(0o000)
        try:
            with pytest.raises(StorageStop, match="owner access"):
                scratch.check_write(0)
        finally:
            directory.chmod(0o700)


def test_failed_directory_scan_is_fail_closed(paths, monkeypatch):
    original_walk = os.walk
    with bounded(paths) as scratch:
        def denied_scan(*args, onerror=None, **kwargs):
            onerror(PermissionError("synthetic scan failure"))
            return original_walk(*args, **kwargs)
        monkeypatch.setattr(os, "walk", denied_scan)
        with pytest.raises(StorageStop, match="safely account"):
            scratch.check_write(0)
        with pytest.raises(StorageStop, match="safely account"):
            paths.validate_seed(paths.seed_root)


def lease_contender(paths):
    """An independent interpreter, with no inherited lease object or lock fd."""
    code = """
from pathlib import Path
import sys
from pdoom_pipeline.collection_storage.scratch import BoundedScratch, ScratchPaths, StorageStop
base = Path(sys.argv[1])
paths = ScratchPaths(mode='posix', workspace_base=base,
                     collection_root=base/'collection', seed_root=base/'seed')
try:
    with BoundedScratch(paths=paths, free_bytes=lambda _: 10**12):
        print('acquired')
except StorageStop as error:
    if str(error) != 'another collection writer holds the lease':
        raise
    print('blocked')
"""
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "pipeline"))
    result = subprocess.run([sys.executable, "-s", "-B", "-c", code, str(paths.workspace_base)],
                            cwd=paths.workspace_base, env=environment, capture_output=True,
                            text=True, timeout=30, check=True)
    return result.stdout.strip()


@pytest.mark.parametrize("relative", [
    "writer.lock", "./writer.lock", "././writer.lock", "writer.lock/child",
    "writer.lock.writing", "./writer.lock.writing", "writer.lock.writing/child",
])
@pytest.mark.parametrize("method", ["bytes", "json"])
def test_normalized_lock_mutation_namespace_is_reserved(paths, relative, method):
    with bounded(paths) as scratch:
        lock = scratch.path("writer.lock")
        before = (lock.stat().st_dev, lock.stat().st_ino, lock.read_bytes())
        with pytest.raises(StorageStop, match="lock namespace"):
            if method == "bytes":
                scratch.atomic_bytes(relative, [b"replacement"], max_bytes=11)
            else:
                scratch.atomic_json(relative, {"replacement": True})
        assert (lock.stat().st_dev, lock.stat().st_ino, lock.read_bytes()) == before
        assert not (scratch.root / "writer.lock.writing").exists()


def test_rejected_lock_replacement_keeps_real_subprocess_excluded_until_release(paths):
    with bounded(paths) as scratch:
        lock = scratch.path("writer.lock")
        before = (lock.stat().st_dev, lock.stat().st_ino)
        assert lease_contender(paths) == "blocked"
        with pytest.raises(StorageStop, match="lock namespace"):
            scratch.atomic_bytes("./writer.lock", [b"replacement"], max_bytes=11)
        assert (lock.stat().st_dev, lock.stat().st_ino) == before
        assert lease_contender(paths) == "blocked"
    assert lease_contender(paths) == "acquired"


@pytest.mark.parametrize("relative", ["WRITER.LOCK", "./Writer.Lock", "WRITER.LOCK.WRITING", "WRITER.LOCK/child"])
def test_reserved_lock_comparison_retains_windows_case_aliases(paths, monkeypatch, relative):
    # PureWindowsPath verifies native name comparison without claiming Windows I/O coverage.
    with bounded(paths) as scratch:
        root = PureWindowsPath(r"F:\CodexTaskScratch\pdoom-live\collection")
        monkeypatch.setattr(scratch, "root", root)
        monkeypatch.setattr(scratch, "path", lambda relative: root / relative)
        with pytest.raises(StorageStop, match="lock namespace"):
            scratch._mutation_path(relative)


@pytest.mark.parametrize("relative", ["", "."])
def test_collection_root_cannot_be_an_atomic_target(paths, relative):
    with bounded(paths) as scratch:
        before = sorted(p.relative_to(scratch.root) for p in scratch.root.rglob("*"))
        with pytest.raises(StorageStop, match="root is not a mutation target"):
            scratch.atomic_bytes(relative, [b"x"], max_bytes=1)
        assert sorted(p.relative_to(scratch.root) for p in scratch.root.rglob("*")) == before


@pytest.mark.parametrize("method", ["bytes", "json", "mkdir"])
def test_mutating_entrypoints_cannot_create_a_root_without_a_lease(paths, method):
    scratch = bounded(paths)
    with pytest.raises(StorageStop, match="writer lease is required"):
        if method == "bytes":
            scratch.atomic_bytes("new/deep/value", [b"x"], max_bytes=1)
        elif method == "json":
            scratch.atomic_json("new/deep/value", {"x": 1})
        else:
            scratch._mkdir(scratch.root / "new/deep")
    assert not scratch.root.exists()


@pytest.mark.parametrize("state", ["never-entered", "released", "closed"])
@pytest.mark.parametrize("method", ["bytes", "json"])
def test_unleased_writes_preserve_another_writers_partial_and_create_no_parents(paths, state, method):
    dormant = bounded(paths)
    if state != "never-entered":
        dormant.__enter__()
        if state == "closed":
            dormant._lock.close()  # A non-None closed handle is not a live lease.
        else:
            dormant.__exit__(None, None, None)
    with bounded(paths) as active:
        partial = active.path("state/value.writing")
        active.atomic_bytes("state/value.writing", [b"active partial"], max_bytes=14)
        before = (partial.stat().st_ino, partial.read_bytes())
        for relative in ("state/value", "unexpected/new/value"):
            with pytest.raises(StorageStop, match="writer lease is required"):
                if method == "bytes":
                    dormant.atomic_bytes(relative, [b"x"], max_bytes=1)
                else:
                    dormant.atomic_json(relative, {"x": 1})
        assert (partial.stat().st_ino, partial.read_bytes()) == before
        assert not (active.root / "unexpected").exists()
    dormant.__exit__(None, None, None)


@pytest.mark.parametrize("final_chunk", [False, True])
def test_lease_loss_during_stream_cannot_replace_or_remove_partial(paths, final_chunk):
    with bounded(paths) as scratch:
        scratch.atomic_bytes("state/value", [b"old"], max_bytes=3)
        def chunks():
            yield b"partial"
            scratch.__exit__(None, None, None)
            if final_chunk:
                yield b"new"
        with pytest.raises(StorageStop, match="writer lease is required"):
            scratch.atomic_bytes("state/value", chunks(), max_bytes=10)
        assert scratch.path("state/value").read_bytes() == b"old"
        assert scratch.path("state/value.writing").read_bytes() == b"partial"
    # The next legitimate holder can recover that partial through the gateway.
    with bounded(paths) as scratch:
        scratch.atomic_bytes("state/value", [b"new"], max_bytes=3)
        assert scratch.path("state/value").read_bytes() == b"new"
        assert not scratch.path("state/value.writing").exists()


def test_reentering_the_same_lease_does_not_drop_its_lock_handle(paths):
    with bounded(paths) as scratch:
        with pytest.raises(StorageStop, match="already active"):
            scratch.__enter__()
        scratch.atomic_json("state/value", {"held": True})
        assert lease_contender(paths) == "blocked"
    assert lease_contender(paths) == "acquired"


def test_inherited_process_identity_is_not_a_writable_lease(paths, monkeypatch):
    with bounded(paths) as scratch:
        parent_pid = os.getpid()
        with monkeypatch.context() as child:
            child.setattr(os, "getpid", lambda: parent_pid + 1)
            with pytest.raises(StorageStop, match="writer lease is required"):
                scratch.atomic_bytes("unexpected/value", [b"x"], max_bytes=1)
        assert not (scratch.root / "unexpected").exists()


def test_free_space_callback_cannot_release_lease_and_then_open_a_partial(paths):
    with bounded(paths) as scratch:
        scratch.atomic_bytes("state/value", [b"old"], max_bytes=3)
        def released(_):
            scratch.__exit__(None, None, None)
            return 10**12
        scratch.free_bytes = released
        with pytest.raises(StorageStop, match="writer lease is required"):
            scratch.atomic_bytes("state/value", [b"new"], max_bytes=3)
        assert scratch.path("state/value").read_bytes() == b"old"
        assert not scratch.path("state/value.writing").exists()


@pytest.mark.parametrize("operation", ["resume", "submit"])
def test_public_supervisor_recovery_checks_lease_before_cleanup_or_drive(paths, monkeypatch, operation):
    drive = FakeDrive()
    admitted = artifact()
    with bounded(paths) as scratch:
        supervisor = Supervisor(scratch, drive, PIN)
        with monkeypatch.context() as interrupted:
            def stopped_cleanup(pending):
                raise StorageStop("synthetic cleanup crash")
            interrupted.setattr(supervisor, "_cleanup", stopped_cleanup)
            with pytest.raises(StorageStop, match="cleanup crash"):
                supervisor.submit([admitted], cursor_after={})
        assert scratch.read_json(CHECKPOINT)
        assert scratch.read_json(PENDING)
    before = {str(p.relative_to(scratch.root)): p.read_bytes()
              for p in scratch.root.rglob("*") if p.is_file()}
    def unexpected_drive():
        pytest.fail("unleased recovery reached Drive")
    monkeypatch.setattr(drive, "about", unexpected_drive)
    with pytest.raises(StorageStop, match="writer lease is required"):
        if operation == "resume":
            supervisor.resume()
        else:
            supervisor.submit([admitted], cursor_after={})
    after = {str(p.relative_to(scratch.root)): p.read_bytes()
             for p in scratch.root.rglob("*") if p.is_file()}
    assert before == after
