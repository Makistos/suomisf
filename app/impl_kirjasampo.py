"""Fetch and parse tags from a kirjasampo.fi work page."""

from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.impl import ResponseType
from app.types import HttpResponseCode

ALLOWED_HOST = "www.kirjasampo.fi"
_HEADERS = {
    "User-Agent": (
        "SF-Bibliografia/1.0 (yp@sf-bibliografia.fi) Python requests"
    )
}


def _is_valid_kirjasampo_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ("http", "https")
            and parsed.netloc == ALLOWED_HOST
        )
    except Exception:
        return False


def kirjasampo_tags(
    url: str,
) -> ResponseType:
    """Fetch all tags from a kirjasampo.fi work page.

    Tags are organised in named sections such as
    "Kirjallisuudenlaji", "Aiheet ja teemat", etc. Each section
    that contains hyperlinked tag items is included in the result.

    Parameters
    ----------
    url:
        Full URL of the kirjasampo.fi work page
        (e.g. https://www.kirjasampo.fi/fi/kulsa/kauno%3Aateos_11973).

    Returns
    -------
    ResponseType
        On success: response value is a dict mapping section label
        (str) to a list of tag strings.
        On error: response with an appropriate HTTP error status.
    """
    if not url:
        return ResponseType(
            "URL puuttuu.",
            status=HttpResponseCode.BAD_REQUEST,
        )

    if not _is_valid_kirjasampo_url(url):
        return ResponseType(
            "Virheellinen URL. Sallittu vain kirjasampo.fi-osoitteet.",
            status=HttpResponseCode.BAD_REQUEST,
        )

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
    except requests.RequestException as exc:
        return ResponseType(
            f"Sivun haku epäonnistui: {exc}",
            status=HttpResponseCode.INTERNAL_SERVER_ERROR,
        )

    if resp.status_code != 200:
        return ResponseType(
            f"Kirjasampo palautti virhekoodin {resp.status_code}.",
            status=HttpResponseCode.INTERNAL_SERVER_ERROR,
        )

    soup = BeautifulSoup(resp.content, "html.parser")
    result: dict[str, list[str]] = {}

    for section in soup.select("div.kulsa-field"):
        heading = section.select_one("h2.kulsa-field-label")
        if not heading:
            continue
        label = heading.get_text(strip=True)
        items = [
            a.get_text(strip=True)
            for a in section.select("div.kulsa-field-item a")
        ]
        if items:
            result[label] = items

    if not result:
        return ResponseType(
            "Sivulta ei löytynyt tunnisteita.",
            status=HttpResponseCode.NOT_FOUND,
        )

    return ResponseType(result, HttpResponseCode.OK)
