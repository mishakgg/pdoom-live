"""Separate a show from a guest, and a speaker turn from the rest of a transcript."""

from __future__ import annotations

import re

from pdoom_pipeline.identity.names import same_person_name
from pdoom_pipeline.ingest.participants import mentioned

SPEAKER_LINE = re.compile(r"^([A-Z][^:\n]{1,80}):\s*(.*)$")
TIMESTAMPED_SPEAKER = re.compile(
    r"^([A-Z][A-Za-z .'\-]{1,60}?)\s*\(?(\d{1,2}):(\d{2})(?::(\d{2}))?\)?:\s*(.*)$"
)
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
        timed = TIMESTAMPED_SPEAKER.match(stripped)
        match = timed or SPEAKER_LINE.match(stripped)
        if match:
            if current:
                turns.append(current)
            if timed:
                speaker = timed.group(1).strip()
                text = timed.group(5).strip()
                start_ms = _clock_ms(timed.group(2), timed.group(3), timed.group(4) or "0")
            else:
                speaker = match.group(1).strip()
                text = match.group(2).strip()
                start_ms = _timestamp_ms(stripped)
            current = {"speaker": speaker, "text": text, "start_ms": start_ms}
            continue
        if current:
            current["text"] = (current["text"] + " " + stripped).strip()
    if current:
        turns.append(current)
    return turns


def turns_for_person(turns: list[dict], display_name: str) -> list[dict]:
    return [turn for turn in turns if same_person_name(turn["speaker"], display_name)]


def speaker_blocks(turns: list[dict], display_name: str) -> list[dict]:
    """Consecutive turns by one person. Another speaker starts a new block."""
    blocks: list[dict] = []
    current: dict | None = None
    for turn in turns:
        if same_person_name(turn.get("speaker") or "", display_name):
            if current is None:
                current = {"text": turn.get("text") or "", "start_ms": turn.get("start_ms")}
            else:
                current["text"] = f"{current['text']}\n{turn.get('text') or ''}".strip()
                if current.get("start_ms") is None:
                    current["start_ms"] = turn.get("start_ms")
            continue
        if current is not None:
            blocks.append(current)
            current = None
    if current is not None:
        blocks.append(current)
    return blocks


def _timestamp_ms(line: str) -> int | None:
    match = TIMESTAMP.search(line)
    if not match:
        return None
    return _clock_ms(match.group("h"), match.group("m"), match.group("s"))


def _clock_ms(hours: str, minutes: str, seconds: str) -> int:
    return ((int(hours) * 60) + int(minutes)) * 60 * 1000 + int(seconds) * 1000
