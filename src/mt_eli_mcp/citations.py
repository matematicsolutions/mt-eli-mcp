"""Maltese legislation.mt parsing + citation helpers.

legislation.mt serves consolidated Maltese law as server-rendered pages addressed by ELI
coordinate (e.g. ``/eli/cap/586/eng``). Each page embeds a schema.org/ELI **JSON-LD** block
(metadata) and a PDF viewer iframe; the full text is only in that PDF (``/getpdf/{hex-id}``).

Citation contract:
- ``eli_uri``: the canonical legislation.mt ELI URL (built from the coordinate, confirmed against
  the page's ``legislationIdentifier``). NEVER invented.
- ``human_readable_citation``: the Maltese convention (e.g. "Data Protection Act (Cap. 586)").
- ``source_url``: the same legislation.mt page.
"""

from __future__ import annotations

import json
import re
from io import BytesIO
from typing import Any

BASE_URL = "https://legislation.mt"
_JSONLD_RE = re.compile(
    r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
)
_PDF_ID_RE = re.compile(r"getpdf/([0-9a-fA-F]{8,})")
_ELI_RE = re.compile(r"^(cap|const|sl|act|ln|legalnotice)(?:/[\w.\-]+)*$", re.IGNORECASE)


def normalize_eli(eli: str) -> str:
    """Normalise a user-supplied ELI coordinate (strip leading 'eli/' and slashes)."""
    e = eli.strip().strip("/")
    if e.lower().startswith("eli/"):
        e = e[4:]
    return e


def is_valid_eli(eli: str) -> bool:
    return bool(_ELI_RE.match(normalize_eli(eli)))


def eli_uri(eli: str, lang: str = "eng") -> str:
    return f"{BASE_URL}/eli/{normalize_eli(eli)}/{lang}"


def parse_jsonld(html: str) -> dict[str, Any]:
    """Extract the schema.org/ELI JSON-LD metadata block from a legislation.mt page."""
    m = _JSONLD_RE.search(html)
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def extract_pdf_id(html: str) -> str | None:
    """Extract the PDF id used by /getpdf/{id} from the viewer iframe."""
    m = _PDF_ID_RE.search(html)
    return m.group(1) if m else None


def _legislation_type(meta: dict[str, Any]) -> str | None:
    lt = meta.get("legislationType")
    if isinstance(lt, dict):
        name = lt.get("name")
        if isinstance(name, dict):
            return name.get("value")
        if isinstance(name, str):
            return name
    if isinstance(lt, str):
        return lt
    return None


def _legal_force(meta: dict[str, Any]) -> str | None:
    lf = meta.get("legislationLegalForce")
    if isinstance(lf, dict):
        return lf.get("@id") or lf.get("name")
    if isinstance(lf, str):
        return lf
    return None


def _citation(name: str | None, eli: str) -> str | None:
    parts = normalize_eli(eli).split("/")
    kind = parts[0].lower() if parts else ""
    rest = parts[1:]
    label = None
    if kind == "cap" and rest:
        label = f"Cap. {rest[0]}"
    elif kind == "const":
        return name or "Constitution of Malta"
    elif kind == "sl" and rest:
        label = f"S.L. {rest[0]}"
    elif kind == "act" and len(rest) >= 2:
        label = f"Act {rest[1]} of {rest[0]}"
    elif kind in ("ln", "legalnotice") and len(rest) >= 2:
        label = f"L.N. {rest[1]} of {rest[0]}"
    if name and label:
        return f"{name} ({label})"
    return name or label


def build_record(html: str, eli: str, lang: str = "eng") -> dict[str, Any]:
    """Build a citation-bearing record from a legislation.mt page's JSON-LD."""
    meta = parse_jsonld(html)
    name = meta.get("name") or meta.get("alternativeHeadline")
    if isinstance(name, dict):
        name = name.get("value")
    legislation_id = meta.get("legislationIdentifier")  # e.g. "eli/cap/586"
    return {
        "eli": normalize_eli(eli),
        "title": name,
        "legislation_identifier": legislation_id,
        "document_type": _legislation_type(meta),
        "legislation_date": meta.get("legislationDate") or meta.get("legislationDateVersion"),
        "date_modified": meta.get("dateModified"),
        "legal_force": _legal_force(meta),
        "eli_uri": eli_uri(eli, lang),
        "human_readable_citation": _citation(name, eli),
        "source_url": eli_uri(eli, lang),
        "pdf_id": extract_pdf_id(html),
    }


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from a legislation PDF using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt.strip():
            parts.append(txt.strip())
    text = "\n".join(parts)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
