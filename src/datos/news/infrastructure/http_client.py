"""The HTTP client every collector shares: honest identification and bounded downloads.

Everything downloaded is untrusted input: size-capped here, parsed by the readers, never
executed.
"""

import httpx

# An honest identification: outlets can see who reads them and contact us.
USER_AGENT = "datos-portfolio/0.1 (+https://github.com/JuanAntonioLeonOjeda/context-back; research)"
MAX_DOWNLOAD_BYTES = 5_000_000


class SourceUnavailableError(Exception):
    """A feed, sitemap or page could not be fetched or is not what was expected."""


def build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        transport=transport,
    )


def download(client: httpx.Client, url: str, *, accept: str = "*/*") -> bytes:
    """The response body, or `SourceUnavailableError` on an HTTP error or an oversized body."""
    try:
        with client.stream("GET", url, headers={"Accept": accept}) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_DOWNLOAD_BYTES:
                    raise SourceUnavailableError(f"{url}: larger than {MAX_DOWNLOAD_BYTES} bytes")
                chunks.append(chunk)
            return b"".join(chunks)
    except httpx.HTTPError as error:
        raise SourceUnavailableError(f"{url}: {type(error).__name__}") from error
