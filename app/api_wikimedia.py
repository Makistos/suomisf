import asyncio

from flask import jsonify, request
from app import app
from .impl_wikimedia import find_person_images


@app.route("/api/person/<personid>/images", methods=["GET"])
def person_images(personid: int):
    """
    Search Wikimedia Commons for free images of a person.

    URL: GET /api/person/<personid>/images

    Authentication: None required.

    Path parameters:
        personid (int): ID of the person in the database.

    Query parameters:
        limit (int): Maximum number of images to return. Default: 20.

    Response 200 — JSON array of image objects, sorted by score
    (best match first):
        [
          {
            "url": "https://upload.wikimedia.org/...",
            "description_url": "https://commons.wikimedia.org/...",
            "credit": "Author name or attribution string",
            "license": "CC BY-SA 4.0",
            "score": 14,
            "dimensions": { "width": 800, "height": 1200 }
          },
          ...
        ]

    Fields:
        url             Direct URL to the image file.
        description_url URL to the Commons file description page.
        credit          Attribution string (artist, credit line, or
                        uploader name).
        license         SPDX-style short license name, e.g. "CC BY-SA 4.0"
                        or "Public domain". Only free-license images are
                        returned.
        score           Heuristic relevance score (higher is better).
                        Factors: filename contains person name (+10 each),
                        portrait/headshot keyword (+6), image larger than
                        400 px (+2), portrait orientation (+2), year in
                        filename between 1800 and current year (+1).
                        Negative: book/poster/cover/logo/scan/plaque etc.
        dimensions      Object with "width" and "height" in pixels,
                        or null if unavailable.
        scoring         Information on how image score was calculated

    Example:
        GET /api/person/42/images?limit=5
    """
    data = request.args.to_dict()
    limit = 20
    if 'limit' in data:
        try:
            limit = int(data['limit'])
        except (TypeError, ValueError) as exp:
            app.logger.error(exp)

    images = asyncio.run(find_person_images(personid, limit))
    return jsonify([img.to_dict() for img in images])
