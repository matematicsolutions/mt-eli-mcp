"""FastMCP entry point - Maltese legislation.mt tools.

Run:

    python -m mt_eli_mcp.server

Configuration via env:

- ``MT_ELI_CACHE_DIR`` (default ``~/.matematic/cache/mt-eli``)
- ``MT_ELI_AUDIT_DIR`` (default ``~/.matematic/audit``)
- ``MT_ELI_BASE_URL`` (default ``https://legislation.mt``)
"""

from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .audit import AuditLogger, hash_input, timer
from .citations import build_record, extract_pdf_text, is_valid_eli, normalize_eli
from . import runtime
from .client import DEFAULT_BASE_URL, MaltaClient
from .models import Act, LawText
from .coverage import Coverage, build_coverage

INSTRUCTIONS = """\
This MCP server exposes the Maltese legislation portal (legislation.mt), the official source of consolidated Maltese law. Documents are addressed by ELI coordinate. Every response carries a stable `eli_uri`, a `human_readable_citation` and a `source_url` (the citation contract).

## ELI coordinates

Pass `eli` as the path after `/eli/`:
- `cap/586` - a Chapter of the Laws of Malta (e.g. the Data Protection Act).
- `const` - the Constitution.
- `sl/586.01` - subsidiary legislation (S.L.).
- `act/2018/20` - an Act by year + number.
- `ln/2018/...` - a Legal Notice by year + number.

## Call order

1. `mt_get_act` - metadata for a document by `eli` (e.g. `cap/586`): title, ELI, type, dates, legal force. Sourced from the page's JSON-LD.
2. `mt_get_text` - the full text by `eli`. Malta publishes the consolidated text only as PDF, so this downloads the official PDF and extracts the text.

## Hard constraints

- **Do not answer past the edge of this corpus** - when a search comes back empty, or the question touches material this connector does not carry, call `mt_coverage` and relay what it says is missing. Absence here is not absence in the law.
- **Address by ELI coordinate, not keywords** - there is no free-text search here. A Maltese citation gives the coordinate (e.g. "Cap. 586"). Relay the `dataset_note`.
- **ELI is the key to citability** - `eli_uri` is the legislation.mt/eli/... URL; do not invent it. It is confirmed against the page's `legislationIdentifier`.
- **Text comes from the PDF** - `mt_get_text` extracts text from the official PDF; layout artefacts are possible. Relay the `text_note`.
- **Every response has `human_readable_citation` + `source_url`** - cite both to the user.
- **Audit log JSONL** - every tool call appends to `~/.matematic/audit/mt-eli-mcp.jsonl`.

## Error iteration

Tools return a structured error with a `[code]` prefix:
- `invalid_arg` - the `eli` coordinate is missing or malformed (expected e.g. `cap/586`, `act/2018/20`).
- `not_found` - no document/PDF exists for that coordinate.
- `upstream_error` - a legislation.mt error (HTTP, timeout, unreadable PDF). Retry once before surfacing.

## Response style

- Cite as `human_readable_citation` with the ELI URL: "Data Protection Act (Cap. 586), https://legislation.mt/eli/cap/586/eng".
- NEVER invent an ELI coordinate, a title or a URL - take each from the tool output.
"""


class ToolError(Exception):
    """Structured error for mt-eli MCP tools - visible to the LLM with a [code] prefix."""

    VALID_CODES = frozenset({"invalid_arg", "not_found", "upstream_error"})

    def __init__(self, code: str, message: str):
        if code not in self.VALID_CODES:
            raise ValueError(f"Unknown ToolError code: {code}. Valid: {sorted(self.VALID_CODES)}")
        self.code = code
        super().__init__(f"[{code}] {message}")


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
    openWorldHint=True,
)

mcp: FastMCP = FastMCP(name="mt-eli-mcp", instructions=INSTRUCTIONS)


def _base_url() -> str:
    return os.environ.get("MT_ELI_BASE_URL", runtime.base_url("eli", DEFAULT_BASE_URL)).rstrip("/")


def _audit() -> AuditLogger:
    return AuditLogger()


def _map_upstream(exc: Exception) -> Exception:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return ToolError("not_found", "No document found on legislation.mt for that ELI coordinate.")
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException)):
        return ToolError("upstream_error", f"legislation.mt error: {type(exc).__name__}: {exc}")
    return exc


def _validate(eli: str) -> str:
    if not eli or not eli.strip():
        raise ToolError("invalid_arg", "eli must be a coordinate like 'cap/586' or 'act/2018/20'.")
    if not is_valid_eli(eli):
        raise ToolError(
            "invalid_arg",
            f"eli={eli!r} is malformed; expected e.g. 'cap/586', 'const', 'sl/586.01', "
            "'act/2018/20', 'ln/2018/123'.",
        )
    return normalize_eli(eli)


# ---------------------------------------------------------------------------
# mt_get_act
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def mt_get_act(eli: str, lang: str = "eng") -> Act:
    """Fetch Maltese document metadata by ELI coordinate.

    Args:
        eli: the coordinate after ``/eli/`` (e.g. ``"cap/586"``, ``"act/2018/20"``, ``"const"``).
        lang: ``"eng"`` (default) or ``"mlt"``.

    Returns:
        ``Act`` with ``eli_uri``, ``human_readable_citation``, ``source_url``.
    """
    audit = _audit()
    eli = _validate(eli)
    if lang not in ("eng", "mlt"):
        raise ToolError("invalid_arg", "lang must be 'eng' or 'mlt'.")
    input_hash = hash_input({"eli": eli, "lang": lang})

    with timer() as t:
        try:
            async with MaltaClient(base_url=_base_url()) as client:
                html = await client.get_eli_page(eli, lang)
        except Exception as exc:
            audit.log(tool="mt_get_act", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    rec = build_record(html, eli, lang)
    if not rec.get("title") and not rec.get("legislation_identifier"):
        raise ToolError("not_found", f"No document metadata for eli={eli!r} on legislation.mt.")
    act = Act.model_validate(rec)
    audit.log(tool="mt_get_act", input_hash=input_hash, output_count_or_size=1,
              duration_ms=t.duration_ms, status="ok")
    return act


# ---------------------------------------------------------------------------
# mt_get_text
@mcp.tool(annotations=READ_ONLY)
async def mt_coverage() -> Coverage:
    """Declare what this connector covers, how it is sourced, and what it does NOT cover.

    Call this before telling a user that the law "does not contain" something, and whenever
    a search comes back empty: the absence may be a gap in this connector rather than in the
    law. Every gap carries a fallback saying where to look instead.

    Returns:
        ``Coverage`` with families, an as-of note, and a non-empty list of known gaps.
    """
    return build_coverage()


# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def mt_get_text(eli: str, lang: str = "eng") -> LawText:
    """Fetch the full text of a Maltese document by ELI coordinate (from the official PDF).

    Args:
        eli: the coordinate after ``/eli/`` (e.g. ``"cap/586"``).
        lang: ``"eng"`` (default) or ``"mlt"``.

    Returns:
        ``LawText`` with the citation contract and ``content`` (text extracted from the PDF).
    """
    audit = _audit()
    eli = _validate(eli)
    if lang not in ("eng", "mlt"):
        raise ToolError("invalid_arg", "lang must be 'eng' or 'mlt'.")
    input_hash = hash_input({"eli": eli, "lang": lang})

    with timer() as t:
        try:
            async with MaltaClient(base_url=_base_url()) as client:
                html = await client.get_eli_page(eli, lang)
                rec = build_record(html, eli, lang)
                pdf_id = rec.get("pdf_id")
                if not pdf_id:
                    raise ToolError("not_found", f"No PDF found on the page for eli={eli!r}.")
                pdf_bytes = await client.get_pdf(pdf_id)
        except ToolError:
            audit.log(tool="mt_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error="not_found")
            raise
        except Exception as exc:
            audit.log(tool="mt_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    try:
        text = extract_pdf_text(pdf_bytes)
    except Exception as exc:
        raise ToolError("upstream_error", f"Could not extract text from the PDF: {exc}") from exc
    if not text:
        raise ToolError("not_found", f"The PDF for eli={eli!r} yielded no extractable text.")

    result = LawText(
        eli=rec["eli"],
        title=rec.get("title"),
        eli_uri=rec.get("eli_uri"),
        human_readable_citation=rec.get("human_readable_citation"),
        source_url=rec.get("source_url"),
        pdf_url=f"{_base_url()}/getpdf/{pdf_id}",
        content=text,
        byte_size=len(text.encode("utf-8")),
    )
    audit.log(tool="mt_get_text", input_hash=input_hash, output_count_or_size=result.byte_size or 0,
              duration_ms=t.duration_ms, status="ok")
    return result


def main() -> None:
    """Run the MCP server over stdio (default for Claude Code)."""
    mcp.run()


if __name__ == "__main__":
    main()
