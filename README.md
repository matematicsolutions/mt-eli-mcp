# mt-eli-mcp

<!-- mcp-name: io.github.matematicsolutions/mt-eli-mcp -->

An MCP server for the Maltese legislation portal **legislation.mt**, the official source of
consolidated Maltese law. It fetches document metadata and full text, with verifiable citations.

Part of the MateMatic `eu-legal-mcp` production line - after PL, DE, AT, ES, FI, IE, NL, SE, FR,
LU, DK, CZ, HR, LT, SK and RO. Same citation contract, legislation.mt source. Malta is ELI-native;
each page carries schema.org/ELI JSON-LD.

> **Scope.** This MVP fetches a document's metadata (from JSON-LD) and full text by ELI coordinate
> (chapters, the Constitution, subsidiary legislation, Acts, Legal Notices). There is no free-text
> search; address documents by their ELI coordinate. Languages: English (`eng`) and Maltese
> (`mlt`). Every response carries a `dataset_note`.
>
> **Text comes from PDF.** Malta publishes the consolidated text only as PDF. `mt_get_text`
> downloads the official PDF and extracts the text with `pypdf`; layout-dependent artefacts are
> possible. Every text response carries a `text_note`.

## The tools

| Tool | What it does |
|---|---|
| `mt_get_act` | Metadata for a document by ELI coordinate (JSON-LD). |
| `mt_get_text` | Full text by ELI coordinate (extracted from the official PDF). |
| `mt_coverage` | Declare what this connector covers, when each family was captured, and - explicitly - what it does NOT cover. Every gap carries a fallback. |

ELI coordinates (`eli`): `cap/586` (Chapter), `const` (Constitution), `sl/586.01` (subsidiary
legislation), `act/2018/20` (Act), `ln/2018/123` (Legal Notice).

Every response carries the contract: `eli_uri` (the legislation.mt URL, e.g.
`https://legislation.mt/eli/cap/586/eng`), `human_readable_citation` (e.g.
`Data Protection Act (Cap. 586)`), and `source_url`.

## Install

Run it with no install step (once published to PyPI):

```bash
uvx mt-eli-mcp
```

Or from source:

```bash
cd mt-eli-mcp
pip install -e .
```

## Configure (Claude Code / any MCP client)

```json
{
  "mcpServers": {
    "mt-eli-mcp": { "command": "mt-eli-mcp" }
  }
}
```

### Windows 11 with Smart App Control

Smart App Control blocks unsigned executables, which covers `uvx.exe`, `pip.exe`
and the `mt-eli-mcp.exe` launcher that pip writes at install time. The `python.exe` and
`py.exe` from the python.org installer are signed by the Python Software
Foundation, so running the module through the interpreter works:

```bash
python -m pip install mt-eli-mcp
python -m mt_eli_mcp
```

`pip.exe` is blocked for the same reason, so install with `python -m pip`, not
`pip install`. If `python` is not on PATH, use the Windows launcher: `py -3 -m mt_eli_mcp`.

```json
{ "mcpServers": { "mt-eli-mcp": { "command": "python", "args": ["-m", "mt_eli_mcp"] } } }
```

Do not turn Smart App Control off to work around this - it cannot be re-enabled
without reinstalling Windows.

Environment:

- `MT_ELI_BASE_URL` - default `https://legislation.mt`
- `MT_ELI_CACHE_DIR` - default `~/.matematic/cache/mt-eli`
- `MT_ELI_AUDIT_DIR` - default `~/.matematic/audit`

No API key. legislation.mt is open data.

## Governance

- **Public data only** - read-only against legislation.mt; no client data leaves the machine.
- **Audit log** - every tool call appends one JSON line to `~/.matematic/audit/mt-eli-mcp.jsonl`.
- **Vendor-neutral** - talks only to `legislation.mt`; no LLM provider, no telemetry.
- **Verifiable citations** - every response is independently checkable via `source_url`.

See `CONSTITUTION.md` and `DISCOVERY.md`.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/test_instructions_drift.py tests/test_parse.py -v   # offline
pytest tests/test_smoke.py -v                                    # hits live legislation.mt
```

## Licence

Apache-2.0. © Matematic Solutions / Wieslaw Mazur.
