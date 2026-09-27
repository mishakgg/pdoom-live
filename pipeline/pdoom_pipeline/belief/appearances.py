"""Separate a show from a guest, and a speaker turn from the rest of a transcript."""

from __future__ import annotations

import re

from pdoom_pipeline.identity.names import same_person_name
from pdoom_pipeline.ingest.participants import mentioned

SPEAKER_LINE = re.compile(r"^([A-Z][^:\n]{1,80}):\s*(.*)$")
TIMESTAMP = re.compile(r"\[?(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})\]?")


def guest_from_title(title: str, people: list[dict]) -> dict | None:
    """High-distinctiveness full name in the episode title. Two matches stay unresolved."""
    hits = [
        person
        for person in people
        if person.get("name_distinctiveness") == "high" and mentioned(title or "", person["display_name"])
    ]
    if len(hits) != 1:
        return None
    return hits[0]


def speaker_turns(transcript: str) -> list[dict]:
    """Group lines under a `Name:` label. Unlabeled text is not a turn."""
    turns: list[dict] = []
    current: dict | None = None
    for line in (transcript or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = SPEAKER_LINE.match(stripped)
        if match:
            if current:
                turns.append(current)
            current = {"speaker": match.group(1).strip(), "text": match.group(2).strip(), "start_ms": _timestamp_ms(stripped)}
            continue
        if current:
            current["text"] = (current["text"] + " " + stripped).strip()
    if current:
        turns.append(current)
    return turns


def turns_for_person(turns: list[dict], display_name: str) -> list[dict]:
    return [turn for turn in turns if same_person_name(turn["speaker"], display_name)]


def _timestamp_ms(line: str) -> int | None:
    match = TIMESTAMP.search(line)
    if not match:
        return None
    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    return ((hours * 60) + minutes) * 60 * 1000 + seconds * 1000
