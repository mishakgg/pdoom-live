"""XML parsing that prefers defusedxml and does not require it at import time."""

from __future__ import annotations

from xml.etree import ElementTree as ElementTreeModule


class XmlParseError(Exception):
    pass


def fromstring(payload: bytes) -> ElementTreeModule.Element:
    """Parse XML. A missing defusedxml install uses a stdlib parse that rejects DTD and entities."""
    try:
        import defusedxml.ElementTree as ET
    except ImportError:
        return fromstring_without_defusedxml(payload)
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:
        raise XmlParseError(str(exc)) from exc


def fromstring_without_defusedxml(payload: bytes) -> ElementTreeModule.Element:
    """Stdlib parse used only when defusedxml is not installed. DTD and entities are rejected."""
    if declares_xml_type(payload):
        raise XmlParseError("xml type declaration")
    try:
        return ElementTreeModule.fromstring(payload)
    except ElementTreeModule.ParseError as exc:
        raise XmlParseError(str(exc)) from exc


def declares_xml_type(payload: bytes) -> bool:
    lowered = payload.lower()
    return any(token in lowered for token in (b"<!doctype", b"<!entity", b"<!element", b"<!attlist", b"<!notation"))
