"""Zepsuty JSON-LD to awaria zrodla, nie brak aktu (2026-09-24)."""
from __future__ import annotations

import pytest

import mt_eli_mcp.server as srv
from mt_eli_mcp.citations import build_record

ZEPSUTY = '<script type="application/ld+json">{"name": "Civil Code", </script>'
BRAK = "<html><body>no metadata here</body></html>"


def test_status_w_rekordzie():
    assert build_record(ZEPSUTY, "cap/16")["metadata_status"] == "unparseable"
    assert build_record(BRAK, "cap/16")["metadata_status"] == "absent"


@pytest.mark.asyncio
async def test_zepsuty_jsonld_to_upstream_error(monkeypatch):
    class Atrapa:
        def __init__(self, base_url=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get_eli_page(self, eli, lang):
            return ZEPSUTY

    monkeypatch.setattr(srv, "MaltaClient", Atrapa)
    with pytest.raises(srv.ToolError) as e:
        await srv.mt_get_act("cap/16")
    assert e.value.code == "upstream_error"
