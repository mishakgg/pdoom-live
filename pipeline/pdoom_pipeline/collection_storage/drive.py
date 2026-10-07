"""Drive REST transport. Credentials are supplied, never created or logged here."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Callable, Protocol
from urllib import error, parse, request

from .scratch import CHUNK_BYTES, StorageStop

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
BASE = "https://www.googleapis.com/drive/v3/"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FILE_FIELDS = ("id,size,md5Checksum,sha256Checksum,parents,trashed,mimeType,driveId,ownedByMe,"
               "owners(emailAddress,permissionId),permissions(id,type,role),appProperties,"
               "capabilities(canAddChildren)")


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes = b""


class Transport(Protocol):
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
        except (error.URLError, OSError):
            raise StorageStop("Drive transport interrupted; retain pending batch and resume") from None
        with response:
            status = response.status
            raw = response.read(1024 * 1024 + 1) if status in (200, 201, 308) else b""
            if len(raw) > 1024 * 1024:
                raise StorageStop("Drive metadata response exceeded bound")
            return Response(status, {k.lower(): v for k, v in response.headers.items()}, raw)


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
