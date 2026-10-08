"""Original-byte Drive readback: real backend/transport, synthetic HTTP only."""
from dataclasses import replace
from http.client import IncompleteRead
import hashlib
import io
import json
import os
import re
from urllib import error, parse

import pytest

from test_collection_storage import FakeDrive, PIN, MockHTTP, registry
from test_collection_storage_continuous import item, producer, Clock
from pdoom_pipeline.collection_storage.bootstrap import synthetic_smoke
from pdoom_pipeline.collection_storage.continuous import (
    ContinuousQueue, ReviewedProfile, QueueLimits, RecoveryPin,
    JOURNAL, INDEX, PAYLOAD, SNAPSHOT,
)
from pdoom_pipeline.collection_storage.drive import (
    BASE, DRIVE_FILE_SCOPE, DriveHTTP, Response, UrllibTransport,
    MAX_DOWNLOAD_BYTES, MAX_DOWNLOAD_REQUESTS,
)
from pdoom_pipeline.collection_storage.scratch import BoundedScratch, CHUNK_BYTES, ScratchPaths, StorageStop
from pdoom_pipeline.collection_storage.supervisor import CHECKPOINT, DriveBackend


def partial(body=b"abc", *, start=0, total=None, etag='"fixture-v1"', **headers):
    total = start + len(body) if total is None else total
    values = {"content-range": f"bytes {start}-{start+len(body)-1}/{total}",
              "content-length": str(len(body)), **headers}
    if etag is not None:
        values["etag"] = etag
    return Response(206, values, body)


def read(drive, *, chunk=3, maximum=3, file_id="fixture_id"):
    return list(drive.download_chunks(file_id, chunk_bytes=chunk, max_bytes=maximum))


def test_original_bytes_are_lazy_bounded_and_etag_pinned():
    t = MockHTTP(partial(b"\x00\xffa", total=7), partial(b"b\x80c", start=3, total=7),
                 partial(b"d", start=6, total=7))
    stream = DriveHTTP(t).download_chunks("fixture_id", chunk_bytes=3, max_bytes=7)
    assert not t.calls
    assert next(stream) == b"\x00\xffa"
    assert len(t.calls) == 1
    assert list(stream) == [b"b\x80c", b"d"]
    assert [c[2]["Range"] for c in t.calls] == ["bytes=0-2", "bytes=3-5", "bytes=6-6"]
    assert all(c[0] == "GET" and c[1] == BASE + "files/fixture_id?alt=media"
               and c[2]["Accept-Encoding"] == "identity" and c[3] is None for c in t.calls)
    assert "If-Match" not in t.calls[0][2]
    assert [c[2]["If-Match"] for c in t.calls[1:]] == ['"fixture-v1"'] * 2


@pytest.mark.parametrize("chunk,maximum", [(0, 1), (-1, 1), (True, 1), (1.0, 1),
    (CHUNK_BYTES+1, 1), (1, 0), (1, -1), (1, True), (1, 1.0),
    (CHUNK_BYTES, MAX_DOWNLOAD_BYTES+1), (1, MAX_DOWNLOAD_REQUESTS+1)])
def test_invalid_limits_never_request(chunk, maximum):
    t = MockHTTP()
    with pytest.raises(StorageStop, match="limits"):
        read(DriveHTTP(t), chunk=chunk, maximum=maximum)
    assert not t.calls


@pytest.mark.parametrize("file_id", ["../escape", "a?alt=preview", "a/b", "a\n", "https://evil.example", "", None])
def test_file_id_is_validated_before_request(file_id):
    t = MockHTTP()
    with pytest.raises(StorageStop, match="file ID"):
        read(DriveHTTP(t), file_id=file_id)
    assert not t.calls


@pytest.mark.parametrize("status", [200, 201, 301, 302, 308, 401, 403, 404, 412, 416, 429, 500])
def test_non_partial_responses_stop_without_fallback_or_retry(status):
    t = MockHTTP(Response(status, {"location": "https://evil.example"}, b"PRIVATE_ERROR"))
    with pytest.raises(StorageStop) as failure:
        read(DriveHTTP(t))
    assert str(failure.value) == f"Drive ranged download stopped with HTTP {status}"
    assert len(t.calls) == 1


@pytest.mark.parametrize("header,value", [
    ("content-range", ""), ("content-range", "bytes 0-2/*"),
    ("content-range", "bytes 1-3/4"), ("content-range", "bytes 0-1/3"),
    ("content-range", "bytes 0-2/4"), ("content-range", "bytes 0-2/0"),
    ("content-range", "bytes 0-2/999999999999999999999"),
    ("content-length", "2"), ("content-length", "4"), ("content-length", "-1"),
    ("content-length", "3,3"), ("content-length", "nan"),
    ("content-encoding", "gzip"), ("content-encoding", "br"),
    ("etag", 'W/"weak"'), ("etag", '"bad\r\nheader"'), ("etag", '"' + 'x'*201 + '"'),
])
def test_invalid_response_headers_fail_closed(header, value):
    r = partial()
    t = MockHTTP(replace(r, headers={**r.headers, header: value}))
    with pytest.raises(StorageStop):
        read(DriveHTTP(t))
    assert len(t.calls) == 1


@pytest.mark.parametrize("body", [b"", b"ab", b"abcd", bytearray(b"abc"), "abc"])
def test_response_body_must_exactly_match_range(body):
    t = MockHTTP(replace(partial(), body=body))
    with pytest.raises(StorageStop, match="incomplete or oversized"):
        read(DriveHTTP(t))


def test_single_range_without_etag_and_total_below_maximum_is_valid():
    assert read(DriveHTTP(MockHTTP(partial(etag=None))), chunk=10, maximum=10) == [b"abc"]


def test_missing_multi_range_etag_fails_before_first_yield():
    t = MockHTTP(partial(total=6, etag=None))
    with pytest.raises(StorageStop, match="strong ETag"):
        read(DriveHTTP(t), maximum=6)
    assert len(t.calls) == 1


@pytest.mark.parametrize("second", [partial(b"def", start=3, total=6, etag='"changed"'),
    partial(b"def", start=3, total=6, etag=None),
    partial(b"def", start=3, total=7), partial(b"def", start=2, total=6),
    Response(412, {}, b"PRIVATE_ERROR")])
def test_changed_object_or_total_stops_before_yielding_later_chunk(second):
    t = MockHTTP(partial(total=6), second)
    stream = DriveHTTP(t).download_chunks("fixture_id", chunk_bytes=3, max_bytes=7)
    assert next(stream) == b"abc"
    with pytest.raises(StorageStop):
        next(stream)
    assert len(t.calls) == 2 and t.calls[1][2]["If-Match"] == '"fixture-v1"'


def test_stop_consuming_makes_no_more_requests():
    t = MockHTTP(partial(total=6))
    stream = DriveHTTP(t).download_chunks("fixture_id", chunk_bytes=3, max_bytes=6)
    assert next(stream) == b"abc"
    stream.close()
    assert len(t.calls) == 1


def test_custom_transport_exception_text_is_redacted():
    class Broken:
        def send(self, *args):
            raise RuntimeError("PRIVATE_TOKEN")
    with pytest.raises(StorageStop) as failure:
        read(DriveHTTP(Broken()))
    assert "PRIVATE_TOKEN" not in str(failure.value)
    assert failure.value.__suppress_context__


class HTTPResponse:
    def __init__(self, result, *, read_error=None):
        self.status, self.headers = result.status, result.headers
        self.body = io.BytesIO(result.body)
        self.reads, self.closed = [], False
        self.read_error = read_error
    def read(self, size):
        self.reads.append(size)
        if self.read_error:
            raise self.read_error
        return self.body.read(size)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.closed = True
        self.body.close()


class Opener:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []
    def open(self, req, timeout):
        self.calls.append((req, timeout))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def transport(opener, token=lambda: "synthetic-access-token"):
    t = UrllibTransport(token, granted_scopes=frozenset({DRIVE_FILE_SCOPE}))
    t._opener = opener
    return t


def test_concrete_transport_bounds_media_read_and_closes_before_yield():
    response = HTTPResponse(partial())
    opener = Opener(response)
    assert read(DriveHTTP(transport(opener))) == [b"abc"]
    assert response.reads == [4] and response.closed
    req, timeout = opener.calls[0]
    assert req.get_header("Authorization") == "Bearer synthetic-access-token"
    assert req.get_header("Accept-encoding") == "identity"
    assert timeout == 30


@pytest.mark.parametrize("status", [200, 302, 308, 403, 412, 416, 500])
def test_ignored_range_and_error_bodies_are_not_read(status):
    response = HTTPResponse(Response(status, {"content-length": str(10**15)}),
                            read_error=AssertionError("must not read huge body"))
    with pytest.raises(StorageStop):
        read(DriveHTTP(transport(Opener(response))))
    assert response.reads == [] and response.closed


@pytest.mark.parametrize("length", ["4", str(10**15), "-1", "bad"])
def test_oversized_declared_response_is_rejected_before_body_read(length):
    response = HTTPResponse(partial(**{"content-length": length}))
    with pytest.raises(StorageStop):
        read(DriveHTTP(transport(Opener(response))))
    assert response.reads == [] and response.closed


def test_unadvertised_oversized_response_reads_only_range_plus_one():
    response = HTTPResponse(Response(206, {"content-range": "bytes 0-2/3"}, b"x"*100))
    with pytest.raises(StorageStop, match="bound"):
        read(DriveHTTP(transport(Opener(response))))
    assert response.reads == [4] and response.closed


@pytest.mark.parametrize("problem", [OSError("PRIVATE_TOKEN"), TimeoutError("PRIVATE_TOKEN"),
    IncompleteRead(b"PRIVATE_TOKEN", 30), error.URLError("PRIVATE_TOKEN")])
def test_response_read_errors_are_redacted_and_closed(problem):
    response = HTTPResponse(partial(), read_error=problem)
    with pytest.raises(StorageStop) as failure:
        read(DriveHTTP(transport(Opener(response))))
    assert "PRIVATE_TOKEN" not in str(failure.value) and failure.value.__suppress_context__
    assert response.closed


@pytest.mark.parametrize("problem", [OSError("PRIVATE_TOKEN"), error.URLError("PRIVATE_TOKEN")])
def test_open_errors_are_redacted(problem):
    with pytest.raises(StorageStop) as failure:
        read(DriveHTTP(transport(Opener(problem))))
    assert "PRIVATE_TOKEN" not in str(failure.value) and failure.value.__suppress_context__


def test_http_error_body_is_not_read():
    body = io.BytesIO(b"PRIVATE_TOKEN")
    response = error.HTTPError(BASE + "files/fixture_id?alt=media", 403, "PRIVATE_TOKEN", {}, body)
    with pytest.raises(StorageStop, match="HTTP 403"):
        read(DriveHTTP(transport(Opener(response))))
    assert body.closed


def test_metadata_and_upload_response_behavior_stays_bounded():
    about = HTTPResponse(Response(200, {}, b'{"user":{}}'))
    upload = HTTPResponse(Response(308, {"range": "bytes=0-2"}))
    t = transport(Opener(about, upload))
    assert DriveHTTP(t).about() == {"user": {}}
    assert DriveHTTP(t).probe("https://www.googleapis.com/upload/drive/v3/files?upload_id=fixture", 4) == 3
    assert about.reads == upload.reads == [CHUNK_BYTES+1]
    huge = HTTPResponse(Response(200, {}, b"x"*(CHUNK_BYTES+1)))
    with pytest.raises(StorageStop, match="bound"):
        DriveHTTP(transport(Opener(huge))).about()
    assert huge.closed


class DriveServer:
    """Translate mocked HTTP into fixture storage; never replace DriveHTTP methods."""
    def __init__(self):
        self.store = FakeDrive()
        self.calls, self.responses, self.media_ids = [], [], []
        self.media_fault = None
    def open(self, req, timeout):
        self.calls.append((req.get_method(), req.full_url, dict(req.header_items()), req.data))
        assert timeout == 30
        assert req.get_header("Authorization") == "Bearer synthetic-access-token"
        p, method = parse.urlsplit(req.full_url), req.get_method()
        query = parse.parse_qs(p.query)
        headers = {k.lower(): v for k, v in req.header_items()}
        result = None
        if p.path == "/drive/v3/about":
            result = Response(200, {}, json.dumps(self.store.about()).encode())
        elif p.path == "/drive/v3/files/generateIds":
            result = Response(200, {}, json.dumps({"ids": [self.store.allocate_id()]}).encode())
        elif p.path.startswith("/drive/v3/files/"):
            file_id = p.path.rsplit("/", 1)[-1]
            if query.get("alt") == ["media"]:
                self.media_ids.append(file_id)
                row = next(r for r in self.store.sessions.values() if r["id"] == file_id)
                raw = row["data"]
                start, end = map(int, re.fullmatch(r"bytes=(\d+)-(\d+)", headers["range"]).groups())
                etag = '"' + hashlib.sha256(raw).hexdigest() + '"'
                assert headers.get("if-match", etag) == etag
                result = partial(raw[start:end+1], start=start, total=len(raw), etag=etag)
                if self.media_fault:
                    result = self.media_fault(result)
            else:
                meta = self.store.get(file_id)
                result = Response(200, {}, json.dumps(meta).encode()) if meta else Response(404, {})
        elif p.path == "/upload/drive/v3/files" and method == "POST":
            body = json.loads(req.data)
            session = self.store.begin(body["id"], body["parents"][0], body,
                                       int(headers["x-upload-content-length"]))
            result = Response(200, {"location": session})
        elif p.path == "/upload/drive/v3/files" and method == "PUT":
            total = int(headers["content-range"].rsplit("/", 1)[1])
            if headers["content-range"].startswith("bytes */"):
                offset = self.store.probe(req.full_url, total)
                if offset is None:
                    result = Response(404, {})
            else:
                offset = int(headers["content-range"].split(" ")[1].split("-")[0])
                offset = self.store.chunk(req.full_url, offset, req.data, total)
            if result is None:
                result = Response(200, {}) if offset == total else Response(
                    308, {"range": f"bytes=0-{offset-1}"} if offset else {})
        assert result is not None, (method, p.path)
        response = HTTPResponse(result)
        self.responses.append(response)
        return response


@pytest.fixture
def http_queue(tmp_path):
    if os.name != "posix":
        pytest.skip("real POSIX scratch fixture")
    seed = tmp_path / "seed"
    seed.mkdir()
    paths = ScratchPaths(mode="posix", workspace_base=tmp_path,
                         collection_root=tmp_path / "collection", seed_root=seed)
    server, clock = DriveServer(), Clock()
    drive = DriveHTTP(transport(server))
    rows = registry()
    profile = ReviewedProfile("fixture-http", "1", (rows[0],), 3)
    limits = QueueLimits(shard_bytes=16384, record_bytes=4096, state_bytes=65536,
                         index_entries=20, records_per_shard=8)
    with BoundedScratch(paths=paths, free_bytes=lambda _: 10**12) as scratch:
        synthetic_smoke(scratch, drive, PIN)
        queue = ContinuousQueue(scratch=scratch, drive=drive, pin=PIN, profile=profile,
                                stream_id="fixture-http", limits=limits, clock=clock)
        yield queue, server, rows, paths


def cycle(queue, rows, title="Title"):
    return queue.run_cycle(registry=rows, producer=producer(item(title=title)), released=True)


def test_actual_backend_supports_full_protocol_cycles_and_fresh_restore(http_queue):
    queue, server, rows, paths = http_queue
    required = {name for name in DriveBackend.__dict__ if not name.startswith("_")}
    assert required == {"about", "get", "allocate_id", "begin", "probe", "chunk"}
    assert all(callable(getattr(queue.drive, name)) for name in required | {"download_chunks"})
    first = cycle(queue, rows)
    second = cycle(queue, rows)
    assert (first["generation"], second["generation"]) == (1, 2)
    assert server.media_ids and all(r.closed for r in server.responses)
    head = queue.scratch.read_json(JOURNAL)
    original_index = queue.scratch.path(INDEX).read_bytes()
    new_paths = replace(paths, collection_root=paths.workspace_base / "restored")
    with BoundedScratch(paths=new_paths, free_bytes=lambda _: 10**12) as restored:
        q = ContinuousQueue(scratch=restored, drive=queue.drive, pin=PIN, profile=queue.profile,
                            stream_id=queue.stream_id, limits=queue.limits, clock=queue.clock)
        q.restore(RecoveryPin(head["manifest_id"], head["manifest_sha256"], 2), sole_coordinator_confirmed=True)
        assert restored.path(INDEX).read_bytes() == original_index
        assert cycle(q, rows)["generation"] == 3
    assert len([r for r in server.store.sessions.values() if r["meta"]["name"].endswith("-metadata.jsonl")]) == 1


@pytest.mark.parametrize("fault", ["checksum", "truncated", "oversized", "http_error"])
def test_actual_queue_failed_readback_retains_inputs_and_resumes_same_ids(http_queue, fault):
    queue, server, rows, _ = http_queue
    if fault == "checksum":
        server.media_fault = lambda r: replace(r, body=r.body[:-1] + bytes([r.body[-1] ^ 1]))
    elif fault == "truncated":
        server.media_fault = lambda r: replace(r, body=r.body[:-1])
    elif fault == "oversized":
        server.media_fault = lambda r: replace(r, body=r.body + b"x")
    else:
        server.media_fault = lambda r: Response(503, {}, b"PRIVATE_ERROR")
    with pytest.raises(StorageStop):
        cycle(queue, rows)
    assert queue.scratch.path(PAYLOAD).exists() and queue.scratch.path(SNAPSHOT).exists()
    assert not queue.scratch.path(INDEX).exists()
    assert queue.scratch.read_json(CHECKPOINT)["cursor_after"]["generation"] == 1
    ids = list(server.store.begun)
    server.media_fault = None
    queue.clock.advance()
    cycle(queue, rows)
    assert server.store.begun == ids
    assert queue.scratch.path(INDEX).exists() and not queue.scratch.path(PAYLOAD).exists()


def test_queue_cancellation_before_next_range_makes_no_extra_request(http_queue):
    queue, _, _, _ = http_queue
    t = MockHTTP(partial(b"x"*CHUNK_BYTES, total=CHUNK_BYTES+1))
    queue.drive = DriveHTTP(t)
    stream = queue._download("fixture_id", CHUNK_BYTES+1)
    assert next(stream) == b"x"*CHUNK_BYTES
    queue._stop = lambda: True
    with pytest.raises(StorageStop, match="cancelled"):
        next(stream)
    assert len(t.calls) == 1


def test_source_contract_revocation_stops_before_mutation_or_producer(http_queue):
    queue, server, rows, _ = http_queue
    rows[0] = {**rows[0], "rights_notes": "revoked"}
    count = len(server.calls)
    with pytest.raises(StorageStop, match="rights"):
        queue.run_cycle(registry=rows, producer=lambda *args: pytest.fail("source requested"), released=True)
    # Existing account/root preflight reads remain ahead of source admission.
    assert len(server.calls) == count + 2
    assert all(method == "GET" and "/generateIds" not in url
               for method, url, _, _ in server.calls[count:])


@pytest.mark.parametrize("change", ["account", "quota", "root"])
def test_actual_backend_preflight_still_blocks_before_source_or_mutation(http_queue, change):
    queue, server, rows, _ = http_queue
    if change == "account":
        server.store.user["emailAddress"] = "other@example.org"
    elif change == "quota":
        server.store.quota = {"usage": "0"}
    else:
        server.store.remote[PIN.folder_id]["permissions"].append({"type": "anyone"})
    count, ids = len(server.calls), list(server.store.begun)
    with pytest.raises(StorageStop):
        queue.run_cycle(registry=rows, producer=lambda *args: pytest.fail("source requested"), released=True)
    assert server.store.begun == ids
    assert all(method == "GET" and "/generateIds" not in url
               for method, url, _, _ in server.calls[count:])


def test_actual_queue_mid_read_exception_preserves_then_recovers(http_queue):
    queue, server, rows, _ = http_queue
    original_open = server.open
    def interrupted(req, timeout):
        response = original_open(req, timeout)
        if parse.parse_qs(parse.urlsplit(req.full_url).query).get("alt") == ["media"]:
            response.read_error = IncompleteRead(b"PRIVATE_TOKEN", 1)
        return response
    queue.drive.transport._opener = type("Interrupted", (), {"open": staticmethod(interrupted)})()
    with pytest.raises(StorageStop) as failure:
        cycle(queue, rows)
    assert "PRIVATE_TOKEN" not in str(failure.value)
    assert queue.scratch.path(PAYLOAD).exists() and queue.scratch.path(SNAPSHOT).exists()
    assert not queue.scratch.path(INDEX).exists()
    assert all(r.closed for r in server.responses)
    ids = list(server.store.begun)
    queue.drive.transport._opener = server
    queue.clock.advance()
    cycle(queue, rows)
    assert server.store.begun == ids
    assert queue.scratch.path(INDEX).exists()


def test_queue_cancellation_during_response_preserves_state(http_queue):
    queue, server, rows, _ = http_queue
    stopped = False
    def cancel(response):
        nonlocal stopped
        stopped = True
        return response
    server.media_fault = cancel
    with pytest.raises(StorageStop, match="cancelled"):
        queue.run_cycle(registry=rows, producer=producer(item()), released=True,
                        cancelled=lambda: stopped)
    assert not queue.scratch.path(INDEX).exists()
    assert queue.scratch.path(PAYLOAD).exists() and queue.scratch.path(SNAPSHOT).exists()
    assert all(r.closed for r in server.responses)


@pytest.mark.parametrize("token", ["", "bad\ntoken", "bad\rtoken", None])
def test_media_uses_existing_token_validation_without_request(token):
    opener = Opener()
    with pytest.raises(StorageStop, match="invalid access token"):
        read(DriveHTTP(transport(opener, token=lambda: token)))
    assert not opener.calls
