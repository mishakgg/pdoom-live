"""Explicitly invoked post-consent root setup and synthetic smoke; no OAuth flow."""
from dataclasses import asdict
import hashlib

from .scratch import BoundedScratch, StorageStop
from .supervisor import Artifact, DrivePin, Supervisor


def prepare_private_root(scratch: BoundedScratch, drive, *, email: str,
                         permission_id: str, consent_confirmed: bool = False) -> DrivePin:
    if not consent_confirmed:
        raise StorageStop("action-time OAuth confirmation and secure handoff are required")
    # Persistent credentials themselves are provisioned outside this module.
    info = drive.about()
    user = info.get("user") or {}
    if (user.get("emailAddress", "").lower() != email.lower()
            or user.get("permissionId") != permission_id):
        raise StorageStop("bootstrap account does not match intended owner")
    try:
        q = info["storageQuota"]
        remaining = int(q["limit"]) - int(q["usage"])
    except (KeyError, TypeError, ValueError):
        raise StorageStop("bootstrap requires an actual quota read") from None
    if remaining < 1024 * 1024:
        raise StorageStop("bootstrap requires remote quota headroom")
    existing = scratch.read_json("state/root-pin.json")
    if existing:
        pin = DrivePin(**existing)
        if pin.email.lower() != email.lower() or pin.permission_id != permission_id:
            raise StorageStop("root pin belongs to another owner")
    else:
        pin = DrivePin(email, permission_id, drive.allocate_id())
        scratch.atomic_json("state/root-pin.json", asdict(pin))
    meta = drive.get(pin.folder_id)
    if not meta:
        drive.create_folder(pin.folder_id)  # Lost response reuses durable generated ID next invocation.
        meta = drive.get(pin.folder_id)
    if not meta or meta.get("appProperties", {}).get("pdoom_collection") != "private-v1":
        raise StorageStop("bootstrap root lacks expected app ownership marker")
    Supervisor(scratch, drive, pin).preflight(1)
    return pin


def synthetic_smoke(scratch: BoundedScratch, drive, pin: DrivePin) -> dict:
    payload = b'pdoom-live synthetic private storage smoke v1\n'
    retention = {"admitted": True, "mode": "metadata", "decision_id": "synthetic-smoke-v1",
                 "rights_basis": "task-created synthetic test bytes"}
    item = Artifact("synthetic-smoke.txt", len(payload), hashlib.sha256(payload).hexdigest(),
                    retention, lambda: iter([payload]))
    return Supervisor(scratch, drive, pin).submit([item],
                   cursor_after={"kind": "drive-smoke", "synthetic": True})
