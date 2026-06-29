# DISCOVERY - mt-eli-mcp (Malta / legislation.mt)

Date: 2026-06-29. Source selection driven by Legal Data Hunter coverage data
(`worldwidelaw/legal-sources`): Malta's `MT/GovernmentGazette` source is legislation.mt, confirmed
clean by live probes.

## Why Malta, what's clean and what isn't

legislation.mt serves **server-rendered** pages (not a SPA) addressed by ELI coordinate. Each page
carries a rich schema.org/ELI **JSON-LD** block (clean metadata). The full text, however, is only
available as a **PDF** embedded via a viewer iframe - so text extraction needs a PDF reader. That
is the connector's one deficiency, flagged in `text_note`.

## Endpoints (keyless, open data)

| Purpose | Endpoint | Format |
|---|---|---|
| Document page (metadata) | `/eli/{coordinate}/eng` (or `/mlt`) | HTML + JSON-LD |
| Consolidated PDF | `/getpdf/{id}` (id from the page's viewer iframe) | PDF |

ELI coordinates: `cap/{number}` (Chapter), `const` (Constitution), `sl/{chapter}.{number}`
(subsidiary legislation), `act/{year}/{number}` (Act), `ln/{year}/{number}` (Legal Notice).

## Page shape (probed)

- The page is server-rendered (SemanticUI/jQuery), `<title> LEĠIŻLAZZJONI MALTA </title>`.
- One `application/ld+json` block with schema.org/ELI metadata: `name`, `legislationIdentifier`
  (e.g. `eli/cap/586`), `legislationType` (`{name:{value:"Chapter"}}`), `legislationDate`,
  `dateModified`, `legislationLegalForce`, `abstract`, etc.
- A PDF viewer iframe: `src=".../Pdf/web/viewer.html?file=https://legislation.mt/getpdf/{hex-id}"`.
  The id is a 24-char hex; `/getpdf/{hex-id}` returns `application/pdf`. (A bare numeric id does
  NOT - the hex id from the iframe is required.)

Example probed: `cap/586` (Data Protection Act) - JSON-LD `name="Data Protection Act"`,
`legislationIdentifier="eli/cap/586"`; the PDF is ~200 KB.

## Citation contract (Art. 4)

- `eli_uri` = `https://legislation.mt/eli/{coordinate}/{lang}`.
- `human_readable_citation` = name + the Maltese reference (e.g. "(Cap. 586)", "(Act 20 of 2018)").
- `source_url` = the same legislation.mt page.

## Tools (MVP)

- `mt_get_act(eli, lang?)` - metadata from JSON-LD.
- `mt_get_text(eli, lang?)` - downloads the official PDF (id from the page iframe) and extracts the
  text with `pypdf`.

## Deficiencies flagged (per WM's "some connectors may be deficient" steer)

- **Text only as PDF** - extraction via `pypdf`; layout artefacts possible. The first connector in
  the line with a PDF dependency.
- **No free-text search** - address by ELI coordinate only.

## Deferred

- **Case law** - Maltese court decisions (separate source).
- **On-site search / listing** - the site's datatable search is not exposed here.
- **Akoma Ntoso / XML** - not offered by the portal; PDF is the only full-text format.

## Licence / re-use

Maltese legislation is published as open data on legislation.mt. Read-only relay with attribution
+ `source_url`. No key, no ToS gate. Distribution as a public connector is in line with the
keyless tier.
