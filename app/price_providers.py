"""Registry of second-hand book price sources.

This is the single extension point for price scraping. Each source is described
by a :class:`PriceProvider` that wires together its capabilities:

* ``search``        — automatic search (query -> list of products/listings)
* ``fetch``         — automatic bulk scrape (product/listing URLs -> price rows)
* ``scrape_single`` — manual single-URL scrape (one URL -> one price row)

Adding a new source (e.g. antikvariaatti.net's automatic search) means:
implement its ``*_search`` / ``*_fetch_products`` functions in
:mod:`app.impl_pricing`, then register them here. No endpoint or frontend
change is required beyond that — the source shows up automatically.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from app import impl_pricing as ip


@dataclass(frozen=True)
class PriceProvider:
    """Capabilities of a single price source. Missing callables = unsupported."""
    name: str                                          # must match PriceSource.name
    domains: Tuple[str, ...] = field(default_factory=tuple)
    search: Optional[Callable[..., Any]] = None        # (q, isbn) -> ResponseType
    fetch: Optional[Callable[..., Any]] = None         # (urls, work_id, cond) -> ResponseType
    scrape_single: Optional[Callable[[str], Dict[str, Any]]] = None  # (url) -> dict


PROVIDERS: Dict[str, PriceProvider] = {
    'Antikvaari': PriceProvider(
        name='Antikvaari',
        domains=('antikvaari.fi',),
        search=ip.antikvaari_search,
        fetch=ip.antikvaari_fetch_products,
    ),
    'Antikka': PriceProvider(
        name='Antikka',
        domains=('antikka.net',),
        search=ip.antikka_search,
        fetch=ip.antikka_fetch_products,
        scrape_single=ip._scrape_antikka,
    ),
    'Antikvariaatti': PriceProvider(
        name='Antikvariaatti',
        domains=('antikvariaatti.net',),
        scrape_single=ip._scrape_antikvariaatti,
    ),
    'Huuto.net': PriceProvider(
        name='Huuto.net',
        domains=('huuto.net',),
    ),
}

# Sources that don't yet have a dedicated automatic pipeline fall back to
# Antikvaari's behaviour when addressed by name.
DEFAULT_PROVIDER = 'Antikvaari'


def get_provider(name: Optional[str]) -> Optional[PriceProvider]:
    """Return the provider for a source name (defaults to Antikvaari)."""
    return PROVIDERS.get(name or DEFAULT_PROVIDER)


def provider_for_url(url: str) -> Optional[PriceProvider]:
    """Return the provider whose domain matches a URL, if any."""
    for provider in PROVIDERS.values():
        if any(domain in url for domain in provider.domains):
            return provider
    return None


def search_capable_names() -> List[str]:
    """Names of sources that support automatic search."""
    return [p.name for p in PROVIDERS.values() if p.search]
