"""Smoke tests - require internet, hit the live Maltese legislation.mt portal.

Run manually:

    pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import pytest

from mt_eli_mcp.server import mt_get_act, mt_get_text

# Cap. 586 - the Data Protection Act.
ELI = "cap/586"


@pytest.mark.asyncio
async def test_smoke_get_act() -> None:
    act = await mt_get_act(ELI)
    assert act.eli == "cap/586"
    assert act.title and "data protection" in act.title.lower()
    assert act.eli_uri == "https://legislation.mt/eli/cap/586/eng"
    assert act.human_readable_citation == "Data Protection Act (Cap. 586)"
    assert act.source_url and act.source_url.startswith("https://legislation.mt/")


@pytest.mark.asyncio
async def test_smoke_get_text() -> None:
    text = await mt_get_text(ELI)
    assert text.content and len(text.content) > 1000
    assert "data protection" in text.content.lower()
    assert text.eli_uri == "https://legislation.mt/eli/cap/586/eng"
    assert text.pdf_url and "/getpdf/" in text.pdf_url
    assert text.byte_size and text.byte_size > 1000
