""" Functions related to articles. """
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl import (ResponseType)
from app.orm_decl import (Article, ArticleTag, Tag)
from app.model import (ArticleSchema, TagBriefSchema)
from app.route_helpers import new_session
from app import app
from app.types import HttpResponseCode


def article_tags(article_id: int) -> ResponseType:
    """
    Retrieves the tags associated with a given article ID.

    Parameters:
        article_id (int): The ID of the article.

    Returns:
        ResponseType: The response containing the tags associated with the
                      article.
    """
    session = new_session()

    try:
        tags = session.query(Tag).filter(Tag.id == ArticleTag.tag_id)\
            .filter(ArticleTag.article_id == article_id)\
            .order_by(Tag.name)
    except SQLAlchemyError as exp:
        app.logger.error({exp})
        return ResponseType('Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    schema = TagBriefSchema(many=True)
    retval = schema.dump(tags)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_article(article_id: int) -> ResponseType:
    """
    Retrieves an article from the database based on the provided article ID.

    Args:
        article_id (int): The ID of the article to retrieve.

    Returns:
        ResponseType: The retrieved article as a ResponseType object.

    Raises:
        SQLAlchemyError: If there is an error with the database query.
        exceptions.MarshmallowError: If there is an error with the schema
                                     conversion.
    """
    session = new_session()

    try:
        article = session.query(Article).filter(
            Article.id == article_id).first()
    except SQLAlchemyError as exp:
        app.logger.error({exp})
        return ResponseType('Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = ArticleSchema()
        retval = schema.dump(article)
    except exceptions.MarshmallowError as exp:
        app.logger.error('Schema error: ' + str(exp))
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def article_tag_add(article_id: int, tag_id: int) -> ResponseType:
    """
    Adds a tag to an article.

    Args:
        article_id (int): The ID of the article.
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: The response object indicating the success or failure of
                      the operation.
    """
    retval = ResponseType('', 200)
    session = new_session()

    try:
        article = session.query(Article).filter(
            Article.id == article_id).first()
        if not article:
            app.logger.error(
                f'Article not found. Id = {article_id}.')
            return ResponseType('Artikkelia ei löydy',
                                HttpResponseCode.BAD_REQUEST.value)

        article_tag = ArticleTag()
        article_tag.article_id = article_id
        article_tag.tag_id = tag_id
        session.add(article_tag)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error({exp})
        return ResponseType(f'Tietokantavirhe. \
                            article_id={article_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return retval


def article_tag_remove(article_id: int, tag_id: int) -> ResponseType:
    """
    Remove a tag from an article.

    Args:
        article_id (int): The ID of the article.
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: The response object containing the result of the
                      operation.
    """
    retval = ResponseType('', 200)
    session = new_session()

    try:
        article_tag = session.query(ArticleTag)\
            .filter(ArticleTag.article_id == article_id,
                    ArticleTag.tag_id == tag_id)\
            .first()
        if not article_tag:
            app.logger.error(
                f'Article has no such tag: \
                    article_id {article_id}, tag {tag_id}.'
            )
            return ResponseType(f'Tagia ei löydy \
                                artikkelilta. article_id={article_id}, \
                                tag_id={tag_id}.',
                                HttpResponseCode.BAD_REQUEST.value)
        session.delete(article_tag)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error({exp})
        return ResponseType(f'ArticleTagRemove: Tietokantavirhe. \
                            article_id={article_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return retval
