"""Offline parse tests - JSON-LD, PDF-id and citation against a committed page fixture."""

from __future__ import annotations

import string
from pathlib import Path

from mt_eli_mcp.citations import (
    build_record,
    eli_uri,
    extract_pdf_id,
    is_valid_eli,
    normalize_eli,
    parse_jsonld,
)

FIX = Path(__file__).parent / "fixtures"


def _page() -> str:
    return (FIX / "eli_cap_586_eng.html").read_text(encoding="utf-8")


def test_normalize_and_validate_eli():
    assert normalize_eli("/eli/cap/586/") == "cap/586"
    assert normalize_eli("eli/cap/586") == "cap/586"
    assert is_valid_eli("cap/586")
    assert is_valid_eli("act/2018/20")
    assert is_valid_eli("const")
    assert not is_valid_eli("../etc/passwd")
    assert not is_valid_eli("random text")


def test_eli_uri():
    assert eli_uri("cap/586") == "https://legislation.mt/eli/cap/586/eng"
    assert eli_uri("cap/586", "mlt") == "https://legislation.mt/eli/cap/586/mlt"


def test_parse_jsonld_metadata():
    meta = parse_jsonld(_page())
    assert meta.get("name") == "Data Protection Act"
    assert meta.get("legislationIdentifier") == "eli/cap/586"


def test_extract_pdf_id_is_hex():
    pid = extract_pdf_id(_page())
    assert pid and len(pid) >= 8
    assert all(c in string.hexdigits for c in pid)


def test_build_record_citation():
    rec = build_record(_page(), "cap/586")
    assert rec["title"] == "Data Protection Act"
    assert rec["eli_uri"] == "https://legislation.mt/eli/cap/586/eng"
    assert rec["source_url"] == rec["eli_uri"]
    assert rec["human_readable_citation"] == "Data Protection Act (Cap. 586)"
    assert rec["pdf_id"]
