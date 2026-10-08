"""Drive REST transport. Credentials are supplied, never created or logged here."""
from __future__ import annotations

from dataclasses import dataclass
from http.client import HTTPException
import json
import re
from typing import Callable, Iterable, Protocol
from urllib import error, parse, request

from .scratch import CHUNK_BYTES, StorageStop

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
BASE = "https://www.googleapis.com/drive/v3/"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
MAX_DOWNLOAD_REQUESTS = 128
MAX_DOWNLOAD_BYTES = MAX_DOWNLOAD_REQUESTS * CHUNK_BYTES
FILE_FIELDS = ("id,size,md5Checksum,sha256Checksum,parents,trashed,mimeType,driveId,ownedByMe,"
               "owners(emailAddress,permissionId),permissions(id,type,role),appProperties,"
               "capabilities(canAddChildren)")


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes = b""


class Transport(Protocol):
    """Bound responses while reading, including when a server ignores Range."""
    def send(self, method: str, url: str, headers: dict, body: bytes | None) -> Response: ...


def _google_url(url: str) -> None:
    try:
        p = parse.urlsplit(url)
        valid = (p.scheme == "https" and p.hostname == "www.googleapis.com"
                 and p.port in (None, 443) and not p.username and not p.password and not p.fragment
                 and (p.path.startswith("/drive/v3/") or p.path == "/upload/drive/v3/files"))
    except ValueError:
        valid = False
    if not valid:
        raise StorageStop("Drive transport rejected endpoint")


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class UrllibTransport:
    def __init__(self, token_provider: Callable[[], str], *, granted_scopes: frozenset[str]):
        if granted_scopes != frozenset({DRIVE_FILE_SCOPE}):
            raise StorageStop("runner must use only the confirmed per-app drive.file scope")
        self._token = token_provider
        self._opener = request.build_opener(_NoRedirect())

    def send(self, method, url, headers, body):
        _google_url(url)
        # Preserve the metadata/upload cap; media reads have a tighter per-range
        # cap before materialization, not merely after DriveHTTP receives bytes.
        read_limit = CHUNK_BYTES
        requested_range = headers.get("Range")
        if requested_range is not None:
            match = re.fullmatch(r"bytes=([0-9]{1,10})-([0-9]{1,10})", requested_range)
            if (method != "GET" or not match
                    or not 0 <= int(match[1]) <= int(match[2]) < MAX_DOWNLOAD_BYTES
                    or not 1 <= int(match[2]) - int(match[1]) + 1 <= CHUNK_BYTES):
                raise StorageStop("invalid bounded Drive download range")
            read_limit = int(match[2]) - int(match[1]) + 1
        try:
            token = self._token()
        except Exception:
            raise StorageStop("secure credential provider unavailable") from None
        if not isinstance(token, str) or not token or "\n" in token or "\r" in token:
            raise StorageStop("secure credential provider returned invalid access token")
        req = request.Request(url, data=body, method=method,
                              headers={**headers, "Authorization": "Bearer " + token})
        try:
            response = self._opener.open(req, timeout=30)
        except error.HTTPError as exc:
            response = exc  # Inspect status only; never log API error bodies/URLs.
        except (error.URLError, OSError, HTTPException):
            raise StorageStop("Drive transport interrupted; retain pending batch and resume") from None
        try:
            with response:
                status = response.status
                response_headers = {k.lower(): v for k, v in response.headers.items()}
                if requested_range is not None:
                    # An ignored range, redirect or HTTP error is never read.
                    if status != 206:
                        return Response(status, response_headers)
                    length = response_headers.get("content-length")
                    if length is not None and (not re.fullmatch(r"[0-9]{1,10}", length)
                                               or int(length) > read_limit):
                        raise StorageStop("Drive download response exceeded bound or has invalid length")
                readable = status == 206 if requested_range is not None else status in (200, 201, 308)
                raw = response.read(read_limit + 1) if readable else b""
                if len(raw) > read_limit:
                    raise StorageStop("Drive response exceeded bound")
                return Response(status, response_headers, raw)
        except (error.URLError, OSError, HTTPException):
            raise StorageStop("Drive response read interrupted; retain pending batch and resume") from None


def _file_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value):
        raise StorageStop("invalid Drive file ID")
    return value


class DriveHTTP:
    def __init__(self, transport: Transport):
        self.transport = transport

    def _send(self, method: str, url: str, headers: dict | None = None,
              body: bytes | None = None) -> Response:
        _google_url(url)
        return self.transport.send(method, url, headers or {}, body)

    @staticmethod
    def _json(response: Response) -> dict:
        if response.status not in (200, 201):
            raise StorageStop(f"Drive API stopped with HTTP {response.status}")
        try:
            value = json.loads(response.body)
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, UnicodeError):
            raise StorageStop("Drive returned invalid metadata") from None

    def about(self):
        fields = "user(emailAddress,permissionId),storageQuota(limit,usage,usageInDrive)"
        return self._json(self._send("GET", BASE + "about?" + parse.urlencode({"fields": fields})))

    def get(self, file_id):
        response = self._send("GET", BASE + "files/" + _file_id(file_id) + "?" +
                              parse.urlencode({"fields": FILE_FIELDS}))
        return None if response.status == 404 else self._json(response)

    def download_chunks(self, file_id: str, *, chunk_bytes: int,
                        max_bytes: int) -> Iterable[bytes]:
        """Read original blob bytes in bounded ranges; never export or preview.

        Hash/ownership verification remains the caller's responsibility. A
        multi-range read additionally pins the first strong HTTP ETag. No socket
        stays open across a yield, so interruption cannot strand a response.
        """
        url = BASE + "files/" + _file_id(file_id) + "?alt=media"
        if (type(chunk_bytes) is not int or not 1 <= chunk_bytes <= CHUNK_BYTES
                or type(max_bytes) is not int or not 1 <= max_bytes <= MAX_DOWNLOAD_BYTES
                or max_bytes > chunk_bytes * MAX_DOWNLOAD_REQUESTS):
            raise StorageStop("invalid bounded Drive download limits")
        offset, total, etag = 0, None, None
        while total is None or offset < total:
            end = min(offset + chunk_bytes, total or max_bytes) - 1
            headers = {"Range": f"bytes={offset}-{end}", "Accept-Encoding": "identity"}
            if etag is not None:
                headers["If-Match"] = etag
            try:
                response = self._send("GET", url, headers)
            except StorageStop:
                raise
            except Exception:
                raise StorageStop("Drive download interrupted; retained state requires reconciliation") from None
            if response.status != 206:
                raise StorageStop(f"Drive ranged download stopped with HTTP {response.status}")
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise StorageStop("Drive download returned encoded bytes")
            match = re.fullmatch(r"bytes ([0-9]{1,10})-([0-9]{1,10})/([0-9]{1,10})",
                                 response.headers.get("content-range", ""))
            if not match:
                raise StorageStop("Drive download returned invalid Content-Range")
            start, last, advertised = map(int, match.groups())
            if (not 0 < advertised <= max_bytes or start != offset
                    or last != min(end, advertised - 1) or last < start
                    or (total is not None and advertised != total)):
                raise StorageStop("Drive download range or total changed or exceeded bound")
            block = response.body
            length = response.headers.get("content-length")
            if (not isinstance(block, bytes) or len(block) != last - start + 1
                    or len(block) > chunk_bytes
                    or (length is not None and (not re.fullmatch(r"[0-9]{1,10}", length)
                                               or int(length) != len(block)))):
                raise StorageStop("Drive download returned an incomplete or oversized range")
            current_etag = response.headers.get("etag")
            if total is None:
                if current_etag is not None and not re.fullmatch(r'"[\x21\x23-\x7e]{1,200}"', current_etag):
                    raise StorageStop("Drive download returned invalid strong ETag")
                if last + 1 < advertised and current_etag is None:
                    raise StorageStop("Drive multi-range download requires a strong ETag")
                etag, total = current_etag, advertised
            elif current_etag != etag:
                raise StorageStop("Drive download object changed during read")
            offset = last + 1
            yield block

    def allocate_id(self):
        payload = self._json(self._send("GET", BASE + "files/generateIds?count=1&space=drive&type=files"))
        ids = payload.get("ids") or []
        if len(ids) != 1:
            raise StorageStop("Drive did not allocate exactly one file ID")
        return _file_id(ids[0])

    def create_folder(self, file_id: str):
        payload = {"id": _file_id(file_id), "name": "pdoom-live-data",
                   "mimeType": "application/vnd.google-apps.folder", "parents": ["root"],
                   "appProperties": {"pdoom_collection": "private-v1"}}
        self._json(self._send("POST", BASE + "files?fields=id", {"Content-Type": "application/json"},
                              json.dumps(payload).encode()))

    def begin(self, file_id, folder_id, metadata, size):
        payload = {**metadata, "id": _file_id(file_id), "parents": [_file_id(folder_id)]}
        response = self._send("POST", UPLOAD + "?uploadType=resumable&fields=id",
                              {"Content-Type": "application/json", "X-Upload-Content-Length": str(size),
                               "X-Upload-Content-Type": "application/octet-stream"},
                              json.dumps(payload).encode())
        if response.status not in (200, 201):
            raise StorageStop(f"Drive upload initialization stopped with HTTP {response.status}")
        session = response.headers.get("location", "")
        _google_url(session)
        if parse.urlsplit(session).path != "/upload/drive/v3/files":
            raise StorageStop("Drive returned invalid upload session")
        return session

    @staticmethod
    def _offset(response: Response, total: int) -> int:
        if response.status in (200, 201):
            return total
        if response.status != 308:
            raise StorageStop(f"Drive resumable upload stopped with HTTP {response.status}")
        acknowledged = response.headers.get("range")
        if not acknowledged:
            return 0
        match = re.fullmatch(r"bytes=0-(\d+)", acknowledged)
        if not match or not 0 <= int(match[1]) < total:
            raise StorageStop("Drive returned invalid acknowledged range")
        return int(match[1]) + 1

    def probe(self, session, size):
        response = self._send("PUT", session, {"Content-Length": "0",
                              "Content-Range": f"bytes */{size}"}, b"")
        return None if response.status == 404 else self._offset(response, size)

    def chunk(self, session, offset, data, total):
        if (not data or len(data) > CHUNK_BYTES or not 0 <= offset < total
                or offset + len(data) > total
                or (offset + len(data) < total and len(data) % (256 * 1024))):
            raise StorageStop("invalid bounded resumable chunk")
        return self._offset(self._send("PUT", session, {"Content-Length": str(len(data)),
                            "Content-Range": f"bytes {offset}-{offset + len(data)-1}/{total}"}, data), total)
