"""Pydantic v2 models for the Maltese legislation.mt connector + mt-eli-mcp."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

DATASET_NOTE = (
    "legislation.mt serves consolidated Maltese law addressed by ELI coordinate: chapters "
    "(cap/{number}), the Constitution (const), subsidiary legislation (sl/{chapter}.{number}), "
    "Acts (act/{year}/{number}) and Legal Notices (ln/{year}/{number}). Metadata comes from the "
    "page's schema.org/ELI JSON-LD; the full text is only available as a PDF. There is no "
    "free-text search here - address documents by their ELI coordinate. Languages: English (eng) "
    "and Maltese (mlt)."
)

TEXT_NOTE = (
    "Malta publishes the consolidated text only as PDF; mt_get_text downloads the official PDF and "
    "extracts the text with pypdf. Layout-dependent artefacts are possible - the PDF at source_url "
    "(via the page) is authoritative."
)


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Act(_Tolerant):
    """A Maltese legal document (metadata from JSON-LD)."""

    eli: str | None = None
    title: str | None = None
    legislation_identifier: str | None = None
    document_type: str | None = None
    legislation_date: str | None = None
    date_modified: str | None = None
    legal_force: str | None = None

    # Citation contract (Art. 4 CONSTITUTION).
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    dataset_note: str = DATASET_NOTE


class LawText(_Tolerant):
    """Result of ``mt_get_text`` (text extracted from the official PDF)."""

    eli: str | None = None
    title: str | None = None
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    pdf_url: str | None = None
    format: str = "text/plain (extracted from the official PDF)"
    content: str | None = None
    byte_size: int | None = None
    text_note: str = TEXT_NOTE
    dataset_note: str = DATASET_NOTE
