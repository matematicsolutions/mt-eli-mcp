"""Async httpx client for the Maltese legislation portal (legislation.mt) with cache.

Keyless. The ELI page is server-rendered HTML (JSON-LD metadata + a PDF viewer iframe); the full
text is the PDF at /getpdf/{id}. We keep our own backoff + cache.
"""

from __future__ import annotations

import anyio
import httpx

from .cache import HttpCache
from .citations import normalize_eli

DEFAULT_BASE_URL = "https://legislation.mt"
DEFAULT_TIMEOUT = httpx.Timeout(90.0, connect=15.0)
USER_AGENT = "mt-eli-mcp/0.1.0 (+https://github.com/matematicsolutions/mt-eli-mcp)"

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3


class MaltaClient:
    """Async client. Use as ``async with MaltaClient() as c: ...``."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        cache: HttpCache | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._cache = cache or HttpCache()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    async def __aenter__(self) -> MaltaClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
        self._cache.close()

    async def _request(self, url: str, *, accept: str) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = await self._http.get(url, headers={"Accept": accept})
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRY_STATUS or attempt == _MAX_ATTEMPTS - 1:
                    raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            await anyio.sleep(0.5 * (2**attempt))
        assert last_exc is not None
        raise last_exc

    async def get_eli_page(self, eli: str, lang: str = "eng") -> str:
        """Fetch the server-rendered ELI page (HTML with JSON-LD + PDF iframe)."""
        url = f"{self.base_url}/eli/{normalize_eli(eli)}/{lang}"
        cached = self._cache.get(url)
        if cached is not None and isinstance(cached, str):
            return cached
        resp = await self._request(url, accept="text/html")
        text = resp.text
        self._cache.set(url, text, ttl=HttpCache.ttl_for("act"))
        return text

    async def get_pdf(self, pdf_id: str) -> bytes:
        """Download the official consolidated PDF by its id."""
        url = f"{self.base_url}/getpdf/{pdf_id}"
        cached = self._cache.get(url)
        if cached is not None and isinstance(cached, bytes):
            return cached
        resp = await self._request(url, accept="application/pdf")
        data = resp.content
        self._cache.set(url, data, ttl=HttpCache.ttl_for("act"))
        return data
