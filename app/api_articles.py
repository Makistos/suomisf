###
# Article related functions

from flask import Response, request
from app import app
from app.api_helpers import make_api_response, ResponseType
from app.impl_articles import (article_tag_add, article_tag_remove,
                               article_tags, get_article)
from app.types import HttpResponseCode
from app.api_jwt import jwt_admin_required


@app.route('/api/articles/<articleid>', methods=['get'])
def api_getarticle(articleid: str) -> Response:
    """
    Retrieves an article from the API based on the provided article ID.

    Parameters:
        articleId (str): The ID of the article to retrieve.

    Returns:
        Response: The response object containing the article data.

    Raises:
        ValueError: If the provided article ID is invalid.

    Example:
        api_getarticle('123')
    """

    try:
        int_id = int(articleid)
    except (TypeError, ValueError):
        app.logger.error('api_getarticle: Invalid id %s.', articleid)
        response = ResponseType(
            f'api_getarticle: Virheellinen tunniste {articleid}.',
            HttpResponseCode.BAD_REQUEST)
        return make_api_response(response)

    return make_api_response(get_article(int_id))


@app.route('/api/articles/<articleid>/tags', methods=['get'])
def api_getarticletags(articleid: int) -> Response:
    """
    Get the tags associated with a specific article.

    Parameters:
        articleId (int): The ID of the article.

    Returns:
        Response: The response object containing the tags associated with the
                  article.
    """

    try:
        int_id = int(articleid)
    except (TypeError, ValueError):
        app.logger.error('api_getarticletags: Invalid id %s.', articleid)
        response = ResponseType(
            f'api_getarticletags: Virheellinen tunniste {articleid}.',
            HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = article_tags(int_id)
    return make_api_response(retval)


@app.route('/api/articles/<articleid>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()  # type: ignore
def api_tagtoarticle(articleid: int, tagid: int) -> Response:
    """
    API endpoint for adding or removing a tag from an article.

    Args:
        id (int): The ID of the article.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response containing the result of the operation.
    """
    func = None
    if request.method == 'PUT':
        func = article_tag_add
    elif request.method == 'DELETE':
        func = article_tag_remove
    else:
        app.logger.error(
            f'api_tagtoarticle: Invalid method {request.method}.')
        response = ResponseType('Virheellinen metodin kutsu',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    try:
        int_id = int(articleid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={articleid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = func(int_id, tag_id)

    return make_api_response(retval)
