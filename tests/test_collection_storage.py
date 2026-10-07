"""Deterministic fault injection; no credentials, network, or large allocations."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pdoom_pipeline.collection_storage import scratch as storage
from pdoom_pipeline.collection_storage.scratch import (
    BoundedScratch, CHUNK_BYTES, HARD_MAX_BYTES, METADATA_RESERVE, StorageStop,
    validate_windows_path,
)
from pdoom_pipeline.collection_storage.supervisor import (
    Artifact, CHECKPOINT, DrivePin, PENDING, Supervisor,
)
from pdoom_pipeline.collection_storage.drive import DriveHTTP, Response, UrllibTransport, DRIVE_FILE_SCOPE

PIN = DrivePin("runner@example.org", "owner1", "folder1")
RETENTION = {"admitted": True, "mode": "metadata", "decision_id": "fixture-reviewed-v1",
             "rights_basis": "synthetic metadata fixture", "source_url": "https://example.org/feed"}


@pytest.fixture
def root(tmp_path, monkeypatch):
    # Host mapping only in tests. Production has no root override or alternate-drive mode.
    monkeypatch.setattr(storage, "COLLECTION_ROOT", tmp_path / "collection")
    monkeypatch.setattr(storage, "validate_windows_path", lambda p: None)
    return tmp_path / "collection"


def scratch(**kwargs):
    return BoundedScratch(min_free_bytes=10, free_bytes=lambda p: 10**12, **kwargs)


def private_meta(file_id, **kwargs):
    return {"id": file_id, "trashed": False, "ownedByMe": True,
            "owners": [{"permissionId": PIN.permission_id, "emailAddress": PIN.email}],
            "permissions": [{"id": PIN.permission_id, "type": "user", "role": "owner"}], **kwargs}


class FakeDrive:
    def __init__(self):
        self.user = {"emailAddress": PIN.email, "permissionId": PIN.permission_id}
        self.quota = {"limit": str(5_000_000_000_000), "usage": "408200000000"}
        self.remote = {PIN.folder_id: private_meta(PIN.folder_id,
                       mimeType="application/vnd.google-apps.folder", capabilities={"canAddChildren": True})}
        self.sessions = {}
        self.allocated = 0
        self.begun = []
        self.offsets = []
        self.fail_chunk = False
        self.lose_final = False
        self.corrupt = False
        self.fail_manifest = False

    def about(self):
        return {"user": self.user, "storageQuota": self.quota}

    def get(self, file_id):
        return self.remote.get(file_id)

    def allocate_id(self):
        self.allocated += 1
        return f"id{self.allocated}"

    def begin(self, file_id, folder_id, metadata, size):
        if self.fail_manifest and metadata["name"].startswith("manifest-"):
            raise StorageStop("fixture manifest interruption")
        session = f"https://www.googleapis.com/upload/drive/v3/files?upload_id={len(self.begun)}"
        self.begun.append(file_id)
        self.sessions[session] = {"id": file_id, "parent": folder_id, "meta": metadata,
                                  "size": size, "data": b""}
        return session

    def probe(self, session, size):
        row = self.sessions.get(session)
        return None if row is None else len(row["data"])

    def chunk(self, session, offset, data, total):
        if self.fail_chunk:
            self.fail_chunk = False
            raise StorageStop("fixture network interruption")
        row = self.sessions[session]
        assert offset == len(row["data"])
        self.offsets.append(offset)
        row["data"] += data
        if len(row["data"]) == total:
            assert row["id"] not in self.remote
            self.quota["usage"] = str(int(self.quota["usage"]) + total)
            self.remote[row["id"]] = private_meta(row["id"], parents=[row["parent"]], size=str(total),
                appProperties=row["meta"]["appProperties"],
                md5Checksum="bad" if self.corrupt else hashlib.md5(row["data"], usedforsecurity=False).hexdigest(),
                sha256Checksum=hashlib.sha256(row["data"]).hexdigest())
            if self.lose_final:
                self.lose_final = False
                raise StorageStop("fixture response lost after remote commit")
        return len(row["data"])


def artifact(data=b"fixture", name="observations.json", retention=None):
    def chunks():
        for offset in range(0, len(data), CHUNK_BYTES):
            yield data[offset:offset+CHUNK_BYTES]
    return Artifact(name, len(data), hashlib.sha256(data).hexdigest(), retention or dict(RETENTION), chunks)


@pytest.mark.parametrize("path", [r"C:\scratch", r"F:relative", r"F:\other", r"\\server\share",
                                  r"F:\CodexTaskScratch\pdoom-live\..\escape",
                                  r"F:\CodexTaskScratch\pdoom-live\x:stream"])
def test_rejects_non_f_or_escaping_paths(path):
    with pytest.raises(StorageStop):
        validate_windows_path(path)


def test_accepts_only_task_f_path():
    validate_windows_path(r"F:\CodexTaskScratch\pdoom-live\collection")


def test_hard_cap_is_decimal_and_cannot_be_raised(root):
    assert HARD_MAX_BYTES == 25_000_000_000
    with pytest.raises(StorageStop):
        scratch(max_bytes=HARD_MAX_BYTES+1)


def test_cap_accounts_for_other_subdirectories_and_atomic_duplicate(root):
    with scratch(max_bytes=METADATA_RESERVE+100) as s:
        s.atomic_bytes("cache/old.bin", [b"x"*50], max_bytes=50)
        s.atomic_bytes("runner/state.json", [b"y"*30], max_bytes=30)
        with pytest.raises(StorageStop, match="cap"):
            s.atomic_bytes("runner/state.json", [b"z"*30], max_bytes=30)
        assert s.path("runner/state.json").read_bytes() == b"y"*30
        assert not s.path("runner/state.json.writing").exists()
        assert s.usage() <= s.max_bytes


def test_25gb_boundary_without_allocating_gigabytes(root, monkeypatch):
    with scratch() as s:
        monkeypatch.setattr(s, "usage", lambda: HARD_MAX_BYTES-METADATA_RESERVE-2)
        s.check_write(2)
        with pytest.raises(StorageStop):
            s.check_write(3)


def test_unbounded_stream_aborts_and_removes_only_partial(root):
    with scratch() as s:
        s.atomic_bytes("runner/good", [b"old"], max_bytes=3)
        with pytest.raises(StorageStop, match="admitted size"):
            s.atomic_bytes("runner/good", [b"aa", b"bb"], max_bytes=3)
        assert s.path("runner/good").read_bytes() == b"old"
        assert not s.path("runner/good.writing").exists()


def test_low_disk_stop_preserves_existing_target(root):
    with scratch() as s:
        s.atomic_bytes("runner/good", [b"old"], max_bytes=3)
        s.free_bytes = lambda p: 12
        with pytest.raises(StorageStop, match="low disk"):
            s.atomic_bytes("runner/good", [b"new"], max_bytes=3)
        assert s.path("runner/good").read_bytes() == b"old"


def test_second_writer_cannot_steal_live_lock(root):
    with scratch():
        with pytest.raises(StorageStop, match="another collection writer"):
            with scratch():
                pytest.fail("overlapping lease accepted")
    with scratch():
        pass


def test_link_and_reparse_guard(root, monkeypatch):
    original = Path.lstat
    def fake(p, *args, **kwargs):
        if p == root:
            return SimpleNamespace(st_mode=0, st_file_attributes=0x400)
        return original(p, *args, **kwargs)
    root.mkdir()
    monkeypatch.setattr(Path, "lstat", fake)
    with pytest.raises(StorageStop, match="reparse"):
        scratch()


def test_runtime_environment_and_paths_stay_within_root(root):
    with scratch() as s:
        env = s.runtime_environment()
        for key in ("TEMP", "TMP", "TMPDIR", "PIP_CACHE_DIR", "npm_config_cache", "XDG_CACHE_HOME"):
            assert Path(env[key]).is_relative_to(root)
        for name in ("../other", "C:/other", "x:stream", r"\\host\share"):
            with pytest.raises(StorageStop):
                s.path(name)


def test_complete_batch_has_private_manifest_then_checkpoint_and_cleanup(root):
    d = FakeDrive()
    with scratch() as s:
        s.atomic_bytes("runner/output.json", [b"fixture"], max_bytes=7)
        result = Supervisor(s, d, PIN).submit([artifact()], cursor_after={"feed": "next"},
                                            cleanup_inputs=["runner/output.json"])
        assert result["cursor_after"] == {"feed": "next"}
        manifest = next(row["data"] for row in d.sessions.values() if row["meta"]["name"].startswith("manifest-"))
        receipt = json.loads(manifest)
        assert receipt["files"][0]["retention"] == RETENTION
        assert receipt["files"][0]["sha256"] == artifact().sha256
        assert not s.path(PENDING).exists()
        assert not s.path("runner/output.json").exists()
        assert not list(s.path("staging").rglob("*.bin"))
        assert len(d.begun) == 2
        assert Supervisor(s, d, PIN).submit([artifact()], cursor_after={"feed": "next"}) == result
        assert len(d.begun) == 2


@pytest.mark.parametrize("fault", ["wrong_account", "unknown_quota", "full_quota", "shared_root", "wrong_owner"])
def test_remote_preflight_fails_before_staging_or_remote_mutation(root, fault):
    d = FakeDrive()
    if fault == "wrong_account": d.user = {"emailAddress": "other@example.org", "permissionId": "other"}
    if fault == "unknown_quota": d.quota = {"usage": "0"}
    if fault == "full_quota": d.quota = {"limit": "100", "usage": "99"}
    if fault == "shared_root": d.remote[PIN.folder_id]["permissions"].append({"type": "anyone"})
    if fault == "wrong_owner": d.remote[PIN.folder_id]["owners"][0]["permissionId"] = "other"
    with scratch() as s:
        with pytest.raises(StorageStop):
            Supervisor(s, d, PIN).submit([artifact()], cursor_after={})
        assert not s.path(PENDING).exists()
        assert d.allocated == 0


def test_disallowed_retention_never_stages(root):
    with scratch() as s:
        with pytest.raises(StorageStop, match="admission"):
            Supervisor(s, FakeDrive(), PIN).submit([artifact(retention={**RETENTION, "admitted": False})], cursor_after={})
        assert not s.path(PENDING).exists()


def test_checksum_mismatch_keeps_local_bytes_and_checkpoint_unchanged(root):
    d = FakeDrive()
    d.corrupt = True
    with scratch() as s:
        with pytest.raises(StorageStop, match="verification failed"):
            Supervisor(s, d, PIN).submit([artifact()], cursor_after={"cursor": "advanced"})
        assert not s.path(CHECKPOINT).exists()
        assert s.path(s.read_json(PENDING)["entries"][0]["local"]).exists()


def test_restarts_after_network_failure_without_duplicate_id(root):
    d = FakeDrive()
    d.fail_chunk = True
    with scratch() as s:
        with pytest.raises(StorageStop):
            Supervisor(s, d, PIN).submit([artifact(b"x"*(CHUNK_BYTES+9))], cursor_after={"n": 1})
        assert not s.path(CHECKPOINT).exists()
    with scratch() as s:
        result = Supervisor(s, d, PIN).resume()
        assert result["cursor_after"] == {"n": 1}
        assert d.begun == ["id1", "id2"]


def test_lost_final_response_reuses_remote_file(root):
    d = FakeDrive()
    d.lose_final = True
    with scratch() as s:
        with pytest.raises(StorageStop):
            Supervisor(s, d, PIN).submit([artifact()], cursor_after={"n": 1})
    with scratch() as s:
        Supervisor(s, d, PIN).resume()
        assert d.begun == ["id1", "id2"]
        assert d.allocated == 2


def test_resumes_from_server_offset_not_stale_local_offset(root):
    d = FakeDrive()
    original = d.chunk
    calls = 0
    def interrupt_after_first(session, offset, data, total):
        nonlocal calls
        n = original(session, offset, data, total)
        calls += 1
        if calls == 1:
            raise StorageStop("first acknowledged response lost")
        return n
    d.chunk = interrupt_after_first
    with scratch() as s:
        with pytest.raises(StorageStop):
            Supervisor(s, d, PIN).submit([artifact(b"x"*(CHUNK_BYTES+9))], cursor_after={})
    d.chunk = original
    with scratch() as s:
        Supervisor(s, d, PIN).resume()
        assert d.offsets[:2] == [0, CHUNK_BYTES]


def test_expired_session_restarts_same_preallocated_id(root):
    d = FakeDrive()
    d.fail_chunk = True
    with scratch() as s:
        with pytest.raises(StorageStop):
            Supervisor(s, d, PIN).submit([artifact()], cursor_after={})
    d.sessions.clear()
    with scratch() as s:
        Supervisor(s, d, PIN).resume()
        assert d.begun == ["id1", "id1", "id2"]


def test_manifest_failure_cannot_advance_checkpoint_or_delete_batch(root):
    d = FakeDrive()
    d.fail_manifest = True
    with scratch() as s:
        with pytest.raises(StorageStop):
            Supervisor(s, d, PIN).submit([artifact(), artifact(b"second", "other.json")], cursor_after={"n": 2})
        assert not s.path(CHECKPOINT).exists()
        assert len(list(s.path("staging").rglob("*.bin"))) == 2
        with pytest.raises(StorageStop, match="pending batch"):
            Supervisor(s, d, PIN).submit([artifact(b"different")], cursor_after={})
    d.fail_manifest = False
    with scratch() as s:
        Supervisor(s, d, PIN).resume()
        assert d.begun == ["id1", "id2", "id3"]


def test_crash_after_checkpoint_recovers_cleanup_idempotently(root, monkeypatch):
    d = FakeDrive()
    with scratch() as s:
        sup = Supervisor(s, d, PIN)
        monkeypatch.setattr(sup, "_cleanup", lambda p: (_ for _ in ()).throw(StorageStop("fixture crash")))
        with pytest.raises(StorageStop):
            sup.submit([artifact()], cursor_after={"n": 3})
        assert s.read_json(CHECKPOINT)["cursor_after"] == {"n": 3}
    with scratch() as s:
        Supervisor(s, d, PIN).resume()
        assert not s.path(PENDING).exists()
        assert len(d.begun) == 2


def test_state_account_cannot_be_rebound(root):
    d = FakeDrive()
    with scratch() as s:
        s.atomic_json(CHECKPOINT, {"pin": {"email": "other@example.org"}})
        with pytest.raises(StorageStop, match="another account"):
            Supervisor(s, d, PIN).preflight(1)


def test_mutated_pending_local_bytes_stop_resume(root):
    d = FakeDrive()
    d.fail_chunk = True
    with scratch() as s:
        with pytest.raises(StorageStop):
            Supervisor(s, d, PIN).submit([artifact()], cursor_after={})
        entry = s.read_json(PENDING)["entries"][0]
        s.atomic_bytes(entry["local"], [b"corrupt"], max_bytes=7)
        with pytest.raises(StorageStop, match="checksum"):
            Supervisor(s, d, PIN).resume()


class MockHTTP:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
    def send(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        return self.responses.pop(0)


def test_http_range_probe_and_expiry():
    t = MockHTTP(Response(308, {"range": "bytes=0-1048575"}), Response(404, {}))
    d = DriveHTTP(t)
    session = "https://www.googleapis.com/upload/drive/v3/files?upload_id=fixture"
    assert d.probe(session, 2*CHUNK_BYTES) == CHUNK_BYTES
    assert d.probe(session, 2*CHUNK_BYTES) is None
    assert t.calls[0][2]["Content-Range"] == f"bytes */{2*CHUNK_BYTES}"


@pytest.mark.parametrize("endpoint", ["http://www.googleapis.com/drive/v3/files", "https://evil.example/drive/v3/files",
                                        "https://www.googleapis.com.evil.example/upload/drive/v3/files",
                                        "https://user:password@www.googleapis.com/drive/v3/files"])
def test_http_rejects_token_leaking_endpoints(endpoint):
    t = MockHTTP()
    with pytest.raises(StorageStop, match="endpoint"):
        DriveHTTP(t).probe(endpoint, 1)
    assert not t.calls


def test_http_requires_exact_minimal_scope_and_has_no_credentials_discovery():
    with pytest.raises(StorageStop, match="drive.file"):
        UrllibTransport(lambda: "unused", granted_scopes=frozenset({"https://www.googleapis.com/auth/drive"}))
    UrllibTransport(lambda: "unused", granted_scopes=frozenset({DRIVE_FILE_SCOPE}))


def test_http_preallocated_id_and_chunk_headers():
    t = MockHTTP(Response(200, {}, b'{"ids":["known_id"]}'),
                 Response(200, {"location": "https://www.googleapis.com/upload/drive/v3/files?upload_id=fixture"}),
                 Response(308, {"range": "bytes=0-1048575"}))
    d = DriveHTTP(t)
    file_id = d.allocate_id()
    session = d.begin(file_id, PIN.folder_id, {"name": "test"}, CHUNK_BYTES+1)
    assert json.loads(t.calls[1][3])["id"] == file_id
    assert d.chunk(session, 0, b"x"*CHUNK_BYTES, CHUNK_BYTES+1) == CHUNK_BYTES
    assert t.calls[2][2]["Content-Range"] == f"bytes 0-{CHUNK_BYTES-1}/{CHUNK_BYTES+1}"


def test_http_redacts_error_bodies():
    t = MockHTTP(Response(403, {}, b'credential-or-private-error-text'))
    with pytest.raises(StorageStop) as exc:
        DriveHTTP(t).about()
    assert str(exc.value) == "Drive API stopped with HTTP 403"


def test_real_process_crash_releases_lock_and_preserves_checkpoint(root):
    import subprocess
    import sys
    code = f"""from pathlib import Path
import os
from pdoom_pipeline.collection_storage import scratch as s
s.COLLECTION_ROOT=Path({str(root)!r})
s.validate_windows_path=lambda p:None
with s.BoundedScratch(min_free_bytes=0) as lease:
    lease.atomic_json('state/crash-fixture.json', {{'complete':True}})
    os._exit(17)
"""
    import os
    environment = os.environ.copy()
    inherited = [str(Path(value).resolve()) for value in environment.get("PYTHONPATH", "").split(os.pathsep) if value]
    environment["PYTHONPATH"] = os.pathsep.join([str(Path(__file__).resolve().parents[1] / "pipeline"), *inherited])
    result = subprocess.run([sys.executable, '-s', '-B', '-X', 'utf8', '-c', code],
                            cwd=root.parent, env=environment, capture_output=True, timeout=30)
    assert result.returncode == 17, result.stderr.decode(errors='replace')
    with scratch() as s:
        assert s.read_json('state/crash-fixture.json') == {'complete': True}


def test_incomplete_preparation_can_be_retried_without_growing_archive(root):
    d = FakeDrive()
    data = b'fixture'
    good = artifact(data)
    def interrupted():
        yield b'fi'
        raise StorageStop('fixture interrupted staging')
    broken = Artifact(good.name, good.size, good.sha256, good.retention, interrupted)
    with scratch() as s:
        with pytest.raises(StorageStop):
            Supervisor(s, d, PIN).submit([broken], cursor_after={})
        assert d.allocated == 0
        with pytest.raises(StorageStop, match='incomplete preparation'):
            Supervisor(s, d, PIN).resume()
        Supervisor(s, d, PIN).submit([good], cursor_after={})
        assert not s.path(PENDING).exists()
        assert d.begun == ['id1','id2']


def test_remote_request_progress_budget_is_finite(root):
    d = FakeDrive()
    def trickle(session, offset, data, total):
        return offset+1
    d.chunk = trickle
    with scratch() as s:
        with pytest.raises(StorageStop, match='request budget'):
            Supervisor(s, d, PIN).submit([artifact(b'x'*50)], cursor_after={})
        assert not s.path(CHECKPOINT).exists()


def registry():
    from pdoom_pipeline.collection_storage.pilot import PIN_KEYS
    import pdoom_pipeline.collection_storage.pilot as pilot
    return json.loads(Path(pilot.__file__).with_name('pilot_sources.json').read_text())


def test_bootstrap_requires_confirmation_and_reuses_root_after_lost_response(root):
    from pdoom_pipeline.collection_storage.bootstrap import prepare_private_root
    d = FakeDrive()
    with scratch() as s:
        with pytest.raises(StorageStop, match='confirmation'):
            prepare_private_root(s, d, email=PIN.email, permission_id=PIN.permission_id)
        assert d.allocated == 0
        def create_folder(file_id):
            d.remote[file_id] = private_meta(file_id, mimeType='application/vnd.google-apps.folder',
                         capabilities={'canAddChildren':True}, appProperties={'pdoom_collection':'private-v1'})
            raise StorageStop('folder creation response lost')
        d.create_folder=create_folder
        with pytest.raises(StorageStop, match='response lost'):
            prepare_private_root(s, d, email=PIN.email, permission_id=PIN.permission_id, consent_confirmed=True)
        pin=prepare_private_root(s, d, email=PIN.email, permission_id=PIN.permission_id, consent_confirmed=True)
        assert pin.folder_id == 'id1'
        assert d.allocated == 1


def test_gateway_sink_routes_large_atomic_payload_and_blocks_external_target(root):
    from pdoom_pipeline.collection_storage.pilot import gateway_sink
    with scratch() as s:
        sink=gateway_sink(s)
        payload=b'x'*(CHUNK_BYTES+9)
        sink(s.path('runner/state/big.json'), payload)
        assert s.path('runner/state/big.json').read_bytes()==payload
        with pytest.raises(StorageStop, match='escapes'):
            sink(root.parent/'outside', b'never write')
        assert not (root.parent/'outside').exists()


def test_exact_eight_pins_preserve_original_scope_and_disallow_url_substitution():
    from pdoom_pipeline.collection_storage.pilot import admitted_sources
    rows=registry()
    chosen=admitted_sources(rows)
    assert len(chosen)==8
    assert any('victoria-krakovna' in s['id'] for s in chosen)
    assert not any('karpathy' in s['id'] for s in chosen)
    assert all(s['collection_policy']['extraction'] is False for s in chosen)
    chosen[0]['canonical_url']='https://other.example/feed'
    with pytest.raises(StorageStop, match='differs'):
        admitted_sources(chosen)


def test_pilot_requires_release_smoke_and_write_hook_before_fetch(root):
    from pdoom_pipeline.collection_storage.pilot import run_metadata_pilot
    from pdoom_pipeline.collection_storage.bootstrap import synthetic_smoke
    d=FakeDrive()
    def old_refresh():
        pytest.fail('runner must never be called')
    with scratch() as s:
        args=dict(scratch=s,drive=d,pin=PIN,seed_dir=root,people=[],registry_sources=registry(),refresh=old_refresh)
        with pytest.raises(StorageStop, match='release'):
            run_metadata_pilot(**args)
        with pytest.raises(StorageStop, match='smoke'):
            run_metadata_pilot(**args,released=True)
        synthetic_smoke(s,d,PIN)
        with pytest.raises(StorageStop, match='write hook'):
            run_metadata_pilot(**args,released=True)


def test_pilot_keeps_truthful_partial_status_and_never_imports(root):
    from pdoom_pipeline.collection_storage.pilot import run_metadata_pilot
    from pdoom_pipeline.collection_storage.bootstrap import synthetic_smoke
    called=[]
    def fake_refresh(*,write_bytes,**kwargs):
        called.append(kwargs)
        assert kwargs['include_belief'] is False and kwargs['leads']==[]
        assert kwargs['max_sources']==8 and kwargs['max_seconds']==300
        assert len(kwargs['registry_sources'])==8
        assert Path(__import__('os').environ['TEMP']).is_relative_to(root)
        write_bytes(kwargs['collection_dir']/'state'/'observations.json', b'{"metadata":true}')
        return {'status':'partial','counts':{'new':7,'failed':1},'cursor':'reviewed-source'}
    d=FakeDrive()
    with scratch() as s:
        synthetic_smoke(s,d,PIN)
        result=run_metadata_pilot(scratch=s,drive=d,pin=PIN,seed_dir=root,people=[],
                    registry_sources=registry(),refresh=fake_refresh,released=True)
        assert result['cursor_after']['status']=='partial'
        assert result['cursor_after']['public_import'] is False
        assert not list(s.path('runner').rglob('*.json'))
        assert len(called)==1
        run_metadata_pilot(scratch=s,drive=d,pin=PIN,seed_dir=root,people=[],
                    registry_sources=registry(),refresh=fake_refresh,released=True)
        assert len(called)==1


@pytest.mark.parametrize("name", ["runner/CON", "runner/com1.txt", "runner/LPT²", "runner/file.", "runner/file ", "runner/*.bin"])
def test_gateway_rejects_windows_device_and_alias_names(root, name):
    with scratch() as s:
        with pytest.raises(StorageStop, match="Windows scratch filename"):
            s.path(name)


def test_credential_provider_failure_is_redacted_before_network():
    def unavailable():
        raise RuntimeError("private credential text must never escape")
    transport=UrllibTransport(unavailable,granted_scopes=frozenset({DRIVE_FILE_SCOPE}))
    with pytest.raises(StorageStop) as exc:
        transport.send("GET","https://www.googleapis.com/drive/v3/about",{},None)
    assert str(exc.value)=="secure credential provider unavailable"


@pytest.mark.parametrize("change", [{"collection_policy":{"admitted":False}},
                                    {"collection_policy":{"admitted":True,"raw_retention":{"license":"CC0"}}},
                                    {"allowed_fetch_origins":["https://unreviewed.example"]}])
def test_pilot_does_not_override_new_structured_rights_or_expand_origins(change):
    from pdoom_pipeline.collection_storage.pilot import admitted_sources
    rows=registry()
    rows[0].update(change)
    with pytest.raises(StorageStop, match="new reviewed pin"):
        admitted_sources(rows)


@pytest.mark.parametrize("recovery", ["resume", "submit"])
def test_committed_cleanup_and_replay_need_zero_new_drive_quota(root, monkeypatch, recovery):
    d = FakeDrive()
    data = b"x" * (2 * CHUNK_BYTES)
    with scratch() as s:
        sup = Supervisor(s, d, PIN)
        monkeypatch.setattr(sup, "_cleanup", lambda p: (_ for _ in ()).throw(StorageStop("crash after commit")))
        with pytest.raises(StorageStop, match="crash after commit"):
            sup.submit([artifact(data)], cursor_after={"n": 4})
        committed = s.read_json(CHECKPOINT)
        assert int(d.quota["usage"]) > 408200000000 + len(data)
        # The upload fills the account, but committed cleanup is still possible.
        d.quota["limit"] = d.quota["usage"]
    with scratch() as s:
        sup = Supervisor(s, d, PIN)
        result = sup.resume() if recovery == "resume" else sup.submit([artifact(data)], cursor_after={"n": 4})
        assert result == committed
        assert not s.path(PENDING).exists()
        assert len(d.begun) == 2
        assert sup.submit([artifact(data)], cursor_after={"n": 4}) == committed


def test_manifest_resume_reserves_only_uncommitted_bytes_after_quota_usage_increases(root):
    d = FakeDrive()
    d.fail_manifest = True
    data = b"x" * (2 * CHUNK_BYTES)
    with scratch() as s:
        sup = Supervisor(s, d, PIN)
        with pytest.raises(StorageStop, match="manifest interruption"):
            sup.submit([artifact(data)], cursor_after={})
        pending = s.read_json(PENDING)
        remaining = pending["manifest"]["size"]
        assert int(d.quota["usage"]) == 408200000000 + len(data)
        # Only the manifest can still consume quota; the data file is verified.
        d.quota["limit"] = str(int(d.quota["usage"]) + remaining)
        d.fail_manifest = False
        sup.resume()
        assert int(d.quota["usage"]) == int(d.quota["limit"])
        assert not s.path(PENDING).exists()
        assert d.begun == ["id1", "id2"]


def test_lost_completed_manifest_response_can_commit_at_full_drive_quota(root):
    d = FakeDrive()
    original = d.chunk
    def lose_manifest(session, offset, data, total):
        if d.sessions[session]["meta"]["name"].startswith("manifest-"):
            d.lose_final = True
        return original(session, offset, data, total)
    d.chunk = lose_manifest
    with scratch() as s:
        with pytest.raises(StorageStop, match="response lost"):
            Supervisor(s, d, PIN).submit([artifact()], cursor_after={})
        assert not s.path(CHECKPOINT).exists()
        d.quota["limit"] = d.quota["usage"]
        d.chunk = original
        Supervisor(s, d, PIN).resume()
        assert s.read_json(CHECKPOINT)
        assert d.begun == ["id1", "id2"]


def test_manifest_bytes_are_reserved_before_staging(root):
    d = FakeDrive()
    d.quota = {"limit": "10", "usage": "0"}
    with scratch() as s:
        with pytest.raises(StorageStop, match="quota"):
            Supervisor(s, d, PIN).submit([artifact()], cursor_after={})
        assert not s.path(PENDING).exists()
        assert not list(s.path("staging").iterdir())
        assert d.allocated == 0
