from typing import Any
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.orm_decl import (Tag, ArticleTag, IssueTag,
                          PersonTag, StoryTag, WorkTag)
from app.model import (TagBriefSchema, TagSchema)
from app.route_helpers import new_session
from .impl import ResponseType
from app import app


def TagFilter(query: str) -> ResponseType:
    session = new_session()

    try:
        tags = session.query(Tag)\
            .filter(Tag.name.ilike(query + '%'))\
            .order_by(Tag.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in TagFilter (query: {query}): ' + str(exp))
        return ResponseType('TagFilter: Tietokantavirhe.', 400)
    try:
        schema = TagSchema(many=True, only=('id', 'name'))
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'TagFilter schema error (query: {query}): ' + str(exp))
        return ResponseType('TagFilter: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def TagList() -> ResponseType:
    session = new_session()

    try:
        tags = session.query(Tag).order_by(Tag.name)
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagList: ' + str(exp))
        return ResponseType(f'TagList: Tietokantavirhe.', 400)

    try:
        schema = TagBriefSchema(many=True)
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error('TagList schema error: ' + str(exp))
        return ResponseType('TagList: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def TagInfo(id: int) -> ResponseType:
    session = new_session()

    try:
        tag = session.query(Tag).filter(Tag.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in TagInfo (id: {id}): ' + str(exp))
        return ResponseType(f'TagInfo: Tietokantavirhe.', 400)

    try:
        schema = TagSchema()
        retval = schema.dump(tag)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'TagInfo schema error (id: {id}): ' + str(exp))
        return ResponseType('TagInfo: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def TagSearch(query: str) -> ResponseType:
    session = new_session()

    try:
        tags = session.query(Tag)\
            .filter(Tag.name.ilike(query + '%'))\
            .order_by(Tag.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in TagSearch (query: {query}): ' + str(exp))
        return ResponseType(f'TagSearch: Tietokantavirhe.', 400)

    try:
        schema = TagBriefSchema(many=True)
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'TagSearch schema error (query: {query}): ' + str(exp))
        return ResponseType('TagSearch: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def _tagExists(session: Any, name: str) -> bool:

    try:
        count = session.query(Tag)\
            .filter(Tag.name.ilike(name))\
            .count()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in _tagExists (name: {name}): ' + str(exp))
        return False

    if count > 0:
        return True

    return False


def TagCreate(name: str) -> ResponseType:
    session = new_session()
    if _tagExists(session, name):
        app.logger.error(
            f'TagRename: Tag already exists. name = {name}.')
        return ResponseType('Asiasana on jo olemassa', 400)

    tag = Tag()
    tag.name = name
    session.add(tag)
    session.commit()

    return ResponseType({'id': tag.id}, 200)


def TagRename(id: int, name: str) -> ResponseType:
    """ See api_tagRename() in api.py. """
    session = new_session()

    if _tagExists(session, name):
        app.logger.error(
            f'TagRename: Tag already exists. Id = {id}, name = {name}.')
        return ResponseType('Asiasana on jo olemassa', 400)

    try:
        tag = session.query(Tag).filter(Tag.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in TagRename (id: {id}, name: {name}): ' + str(exp))
        return ResponseType(f'TagRename: Tietokantavirhe.', 400)

    if not tag:
        app.logger.error(f'TagRename: Tag not found. Id = {id}.')
        return ResponseType('Asiasanan tunnistetta ei löydy', 400)

    tag.name = name
    session.add(tag)
    session.commit()
    try:
        schema = TagSchema()
        retval = schema.dump(tag)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'TagSearch schema error (name: {name}): ' + str(exp))
        return ResponseType('TagSearch: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def TagDelete(id: int) -> ResponseType:
    """ See api_tagDelete in api.py. """
    retval = ResponseType('', 200)

    session = new_session()

    articleTags = session.query(ArticleTag).filter(
        ArticleTag.tag_id == id).all()
    if articleTags:
        app.logger.error(f'TagDelete: Tag is attached to articles. Id = {id}.')
        return ResponseType('Asiasanaa käytetään artikkeleiden kanssa.', 400)

    issueTags = session.query(IssueTag).filter(IssueTag.tag_id == id).all()
    if issueTags:
        app.logger.error(f'TagDelete: Tag is attached to issues. Id = {id}.')
        return ResponseType('Asiasanaa käytetään lehden numeroiden kanssa.', 400)

    personTags = session.query(PersonTag).filter(PersonTag.tag_id == id).all()
    if personTags:
        app.logger.error(f'TagDelete: Tag is attached to people. Id = {id}.')
        return ResponseType('Asiasanaa käytetään henkilöiden kanssa.', 400)

    storyTags = session.query(StoryTag).filter(StoryTag.tag_id == id).all()
    if storyTags:
        app.logger.error(f'TagDelete: Tag is attached to stories. Id = {id}.')
        return ResponseType('Asiasanaa käytetään novelleiden kanssa.', 400)

    workTags = session.query(WorkTag).filter(WorkTag.tag_id == id).all()
    if workTags:
        app.logger.error(f'TagDelete: Tag is attached to works. Id = {id}.')
        return ResponseType('Asiasanaa käytetään teosten kanssa.', 400)

    try:
        tag = session.query(Tag)\
            .filter(Tag.id == id)\
            .first()
        session.delete(tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagDelete: ' + str(exp))
        return ResponseType(f'TagDelete: Tietokantavirhe. id={id}', 400)

    if not tag:
        app.logger.error(f'TagDelete: Tag not found. id = {id}.')
        return ResponseType('Asiasanan tunnistetta ei löydy', 400)

    return retval


def TagMerge(idTo: int, idFrom: int) -> ResponseType:
    """ See api_tagMerge in api.py. """
    retval = ResponseType('', 200)
    session = new_session()

    try:
        tagTo = session.query(Tag).filter(Tag.id == idTo).first()
        tagFrom = session.query(Tag).filter(Tag.id == idFrom).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagMerge: ' + str(exp))
        return ResponseType(f'TagMerge: Tietokantavirhe. id={id}', 400)

    if not tagTo or not tagFrom:
        app.logger.error(
            f'TagMerge: Tag not found. To = {idTo}, From = {idFrom}.')
        return ResponseType('Tuntematon asiasanan tunniste', 400)

    # Update
    try:
        session.query(ArticleTag)\
            .filter(ArticleTag.tag_id == idFrom)\
            .update({ArticleTag.article_id: idTo}, synchronize_session=True)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagMerge: ' + str(exp))
        return ResponseType(f'TagMerge: Tietokantavirhe. id={id}', 400)

    return retval
