"""API endpoints for fetching data from kirjasampo.fi."""

from flask import Response, request

from app import app
from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.impl_kirjasampo import kirjasampo_tags
from app.types import HttpResponseCode


@app.route("/api/kirjasampo/tags", methods=["GET"])
def api_kirjasampo_tags() -> Response:
    """
    Fetch all tags from a kirjasampo.fi work page.

    URL: GET /api/kirjasampo/tags

    Authentication: None required.

    Query parameters:
        url (str): Full URL of the kirjasampo.fi work page.

    Response 200 — JSON object mapping section label to tag list:
        {
          "Kirjallisuudenlaji": [
            "filosofiset romaanit",
            "maaginen realismi"
          ],
          "Aiheet ja teemat": [
            "elämän tarkoitus",
            "identiteetti",
            ...
          ],
          "Henkilöt, toimijat": ["kirjastonhoitajat", ...],
          "Päähenkilöt": ["Tamura, Kafka"],
          "Konkreettiset tapahtumapaikat": ["Japani", "Takamatsu"],
          "Asiasanayhdistelmät": ["katoaminen : äidit"],
          "Alkukieli": ["japani"],
          ...
        }

    Response 400 — Missing or invalid URL parameter.
    Response 500 — Remote fetch failed or unexpected error.

    Example:
        GET /api/kirjasampo/tags?url=https://www.kirjasampo.fi/fi/
            kulsa/kauno%3Aateos_11973
    """
    url = request.args.get("url", "").strip()
    if not url:
        return make_api_response(
            ResponseType(
                "Pakollinen parametri 'url' puuttuu.",
                HttpResponseCode.BAD_REQUEST,
            )
        )
    return make_api_response(kirjasampo_tags(url))
