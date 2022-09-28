from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl import (ResponseType)
from app.orm_decl import (Article, ArticleTag, Tag)
from app.model import (ArticleSchema, TagBriefSchema)

from app.route_helpers import new_session
from app import app


def ArticleTags(id: int) -> ResponseType:
    session = new_session()

    try:
        tags = session.query(Tag).filter(Tag.id == ArticleTag.tag_id)\
            .filter(ArticleTag.article_id == id)\
            .order_by(Tag.name)
    except SQLAlchemyError as exp:
        app.logger.error('ArticleTags exception: ' + str(exp))
        return ResponseType('Tietokantavirhe', 400)

    schema = TagBriefSchema(many=True)
    retval = schema.dump(tags)

    return ResponseType(retval, 200)


def GetArticle(id: int) -> ResponseType:
    session = new_session()

    try:
        article = session.query(Article).filter(
            Article.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error('GetArticle exception: ' + str(exp))
        return ResponseType('Tietokantavirhe', 400)

    try:
        schema = ArticleSchema()
        retval = schema.dump(article)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetArticle schema error: ' + str(exp))
        return ResponseType('GetArticle: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def ArticleTagAdd(article_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        article = session.query(Article).filter(
            Article.id == article_id).first()
        if not article:
            app.logger.error(
                f'ArticleTagAdd: Article not found. Id = {article_id}.')
            return ResponseType('Artikkelia ei löydy', 400)

        articleTag = ArticleTag()
        articleTag.article_id = article_id
        articleTag.tag_id = tag_id
        session.add(articleTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ArticleTagAdd(): ' + str(exp))
        return ResponseType(f'ArticleTagAdd: Tietokantavirhe. article_id={article_id}, tag_id={tag_id}.', 400)

    return retval


def ArticleTagRemove(article_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        articleTag = session.query(ArticleTag)\
            .filter(ArticleTag.article_id == article_id, ArticleTag.tag_id == tag_id)\
            .first()
        if not articleTag:
            app.logger.error(
                f'ArticleTagRemove: Article has no such tag: article_id {article_id}, tag {tag_id}.'
            )
            return ResponseType(f'ArticleTagRemove: Tagie ei löydy artikkelilta. article_id={article_id}, tag_id={tag_id}.', 400)
        session.delete(articleTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ArticleTagRemove(): ' + str(exp))
        return ResponseType(f'ArticleTagRemove: Tietokantavirhe. article_id={article_id}, tag_id={tag_id}.', 400)

    return retval
