""" Issue related functions. """
from cgi import FieldStorage
import os
from typing import Any, Dict, Union
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from werkzeug.utils import secure_filename
from app.api_helpers import allowed_image
from app.impl import ResponseType, check_int
from app.impl_contributors import update_issue_contributors
from app.impl_logs import log_changes
from app.route_helpers import new_session
from app.orm_decl import (Article, Issue, IssueContent, IssueEditor, IssueTag,
                          PublicationSize, ShortStory, Tag)
from app.model import (ArticleBriefSchema, IssueSchema,
                       PublicationSizeBriefSchema,
                       ShortBriefestSchema, TagSchema)

from app import app
from app.types import HttpResponseCode


def get_issue(issue_id: int) -> ResponseType:
    """
    Retrieves an issue from the database based on the provided ID.

    Args:
        id (int): The ID of the issue to retrieve.

    Returns:
        ResponseType: The response object containing the retrieved issue.

    Raises:
        SQLAlchemyError: If there is an error querying the database.
        exceptions.MarshmallowError: If there is an error serializing the
                                     issue.

    """
    session = new_session()

    try:
        issue = session.query(Issue)\
            .filter(Issue.id == issue_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error('get_issue: ' + str(exp))
        return ResponseType(f'get_issue: Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = IssueSchema()
        retval = schema.dump(issue)
    except exceptions.MarshmallowError as exp:
        app.logger.error('get_issue schema error: ' + str(exp))
        return ResponseType('get_issue: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def editors_changed(new_editors: Any, old_editors: Any) -> bool:
    """
    Compares two sets of editors (new_editors and old_editors) to determine if
    they are different.

    Args:
        new_editors (any): The new set of editors.
        old_editors (any): The old set of editors.

    Returns:
        bool: True if the sets are different, False otherwise.

    """
    new_ids = sorted([x['id'] for x in new_editors])
    old_ids = sorted([x.id for x in old_editors])
    # retval = new_ids != old_ids
    return new_ids != old_ids


def issue_add(params: Dict[str, Any]) -> ResponseType:
    """
    Adds a new issue to the database.

    Args:
        issue_data (dict): The issue data to add.

    Returns:
        ResponseType: The response object containing the added issue.

    Raises:
        SQLAlchemyError: If there is an error executing the database query.
        exceptions.MarshmallowError: If there is an error serializing the
                                     issue object.
    """
    session = new_session()
    issue = params

    new_issue = Issue()

    if 'magazine_id' not in issue:
        app.logger.error('Missing magazine_id.')
        return ResponseType('Lehnde tunniste puuttuu.',
                            HttpResponseCode.BAD_REQUEST.value)
    try:
        magazine_id_int = int(issue['magazine_id'])
    except ValueError:
        app.logger.error('Invalid magazine_id.')
        return ResponseType('Lehnde tunniste on virheellinen.',
                            HttpResponseCode.BAD_REQUEST.value)

    new_issue.magazine_id = magazine_id_int

    new_issue.number = issue['number'] if 'number' in issue else None
    new_issue.number_extra = issue['number_extra']\
        if 'number_extra' in issue else None
    new_issue.cover_number = issue['cover_number']\
        if 'cover_number' in issue else None
    new_issue.count = issue['count'] if 'count' in issue else None
    new_issue.year = issue['year'] if 'year' in issue else None
    new_issue.cover_number = issue['cover_number']\
        if 'cover_number' in issue else None
    new_issue.image_attr = issue['image_attr']\
        if 'image_attr' in issue else None
    new_issue.image_src = issue['image_src']\
        if 'image_src' in issue else None
    new_issue.pages = issue['pages'] if 'pages' in issue else None
    if 'size' in issue and issue['size'] and 'id' in issue['size']:
        try:
            size_id_int = check_int(issue['size']['id'])
        except ValueError:
            app.logger.error('Invalid size_id.')
            return ResponseType('Julkaisukoko on virheellinen.',
                                HttpResponseCode.BAD_REQUEST.value)

        pub_size = session.query(PublicationSize)\
            .filter(PublicationSize.id == size_id_int)\
            .first()
        if not pub_size:
            app.logger.error('Invalid size_id.')
            return ResponseType('Julkaisukoko on virheellinen: {size_id}.',
                                HttpResponseCode.BAD_REQUEST.value)

        new_issue.size_id = size_id_int
    new_issue.link = issue['link'] if 'link' in issue else None
    new_issue.notes = issue['notes'] if 'notes' in issue else None
    new_issue.title = issue['title'] if 'title' in issue else None

    session.add(new_issue)
    session.commit()

    if 'contributors' in issue:
        contributors_result = update_issue_contributors(session,
                                                        new_issue.id,
                                                        issue['contributors'])
        if contributors_result.status != HttpResponseCode.OK.value:
            session.rollback()
            return ResponseType('NOK',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_changes(session, obj=new_issue, action='Uusi')
    session.commit()

    return ResponseType(str(new_issue.id), HttpResponseCode.CREATED.value)


def issue_update(params: Dict[str, Any]) -> ResponseType:
    """
    Update an existing issue with new values.

    This function takes a request with a single parameter 'data',
    which is a dictionary containing the new values for the issue.
    The keys in 'data' are the column names of the Issue table.

    The function returns a ResponseType object. If the update succeeds,
    the object has a status code of 200 and a message of 'ok'. If the
    update fails, the object has a status code of 400 or 500 and a
    message describing the error.

    The function logs the changes made to the issue in the log table.
    """
    # retval = ResponseType('ok', HttpResponseCode.OK.value)
    session = new_session()
    old_values: Dict[str, Any] = {}
    data = params

    issue_id = check_int(data['id'],
                         zeros_allowed=False,
                         negative_values=False)

    if issue_id is None:
        app.logger.error('issue_update: Invalid id.')
        return ResponseType('issue_update: Virheellinen id.',
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        issue = session.query(Issue).filter(Issue.id == issue_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(str(exp))
        return ResponseType(f'Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    if not issue:
        app.logger.error('issue_update: Issue not found.')
        return ResponseType('issue_update: Tietuea ei loydy.',
                            HttpResponseCode.BAD_REQUEST.value)

    if 'number' in data and data['number'] != issue.number:

        old_values['number'] = issue.number
        issue.number = data['number']

    if 'number_extra' in data and data['number_extra'] != issue.number_extra:
        old_values['number_extra'] = issue.number_extra
        issue.number_extra = data['number_extra']

    if 'cover_numer' in data and data['cover_number'] != issue.cover_number:
        old_values['cover_number'] = issue.cover_number
        issue.cover_number = data['cover_number']

    if 'count' in data and data['count'] != issue.count:
        old_values['count'] = issue.count
        issue.count = data['count']

    if 'year' in data and data['year'] != issue.year:
        old_values['year'] = issue.year
        issue.year = data['year']

    if 'notes' in data and data['notes'] != issue.notes:
        old_values['notes'] = issue.notes
        issue.notes = data['notes']

    if 'title' in data and data['title'] != issue.title:
        old_values['title'] = issue.title
        issue.title = data['title']

    if 'cover_number' in data and data['cover_number'] != issue.cover_number:
        old_values['cover_number'] = issue.cover_number
        issue.cover_number = data['cover_number']

    if 'link' in data and data['link'] != issue.link:
        old_values['link'] = issue.link
        issue.link = data['link']

    if ('size' in data and data['size'] and 'id' in data['size'] and
        data['size']['id'] != issue.size_id or
            ('size' not in data and issue.size_id is not None)):
        size_id = check_int(data['size']['id'], zeros_allowed=False,
                            negative_values=False)
        old_values['size'] = issue.size.name if issue.size else ''
        issue.size_id = size_id

    if 'image_attr' in data and data['image_attr'] != issue.image_attr:
        old_values['image_attr'] = issue.image_attr
        issue.image_attr = data['image_attr']

    if 'image_src' in data and data['image_src'] != issue.image_src:
        old_values['image_src'] = issue.image_src
        issue.image_src = data['image_src']

    if 'pages' in data and data['pages'] != issue.pages:
        old_values['pages'] = issue.pages
        issue.pages = data['pages']

    try:
        session.add(issue)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'{exp}')
        return ResponseType(f'Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if len(old_values) > 0:
        log_changes(session, obj=issue, old_values=old_values)
        session.commit()

    # Handle contributors separately
    if 'contributors' in data:
        contributors_result = update_issue_contributors(session, issue_id,
                                                        data['contributors'])
        if not contributors_result:
            return ResponseType('NOK',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    session.commit()
    return ResponseType(str(issue.id), HttpResponseCode.OK.value)


def issue_delete(issue_id: int) -> ResponseType:
    """
    Deletes an issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        ResponseType: The response object containing the result of the
                      operation.
    """
    session = new_session()
    try:
        issue_editors = session.query(IssueEditor)\
            .filter(IssueEditor.issue_id == issue_id).all()
        for editor in issue_editors:
            session.delete(editor)

        issue_content = session.query(IssueContent)\
            .filter(IssueContent.issue_id == issue_id).all()
        for content in issue_content:
            session.delete(content)

        issue_tags = session.query(IssueTag)\
            .filter(IssueTag.issue_id == issue_id).all()
        for tag in issue_tags:
            session.delete(tag)

        issue = session.query(Issue).filter(Issue.id == issue_id).first()
        session.delete(issue)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error({exp})
        return ResponseType(f'Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('ok', HttpResponseCode.OK.value)


def issue_shorts_get(issue_id: int) -> ResponseType:
    """ Returns a list of short stories associated with an issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        ResponseType: The response object containing the list of short
                      stories.
    """
    session = new_session()
    try:
        stories = session.query(ShortStory)\
            .join(IssueContent, ShortStory.id == IssueContent.shortstory_id)\
            .filter(IssueContent.issue_id == issue_id)\
            .filter(IssueContent.shortstory_id.isnot(None))\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'{exp}')
        return ResponseType(f'Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = ShortBriefestSchema(many=True)
        retval = schema.dump(stories)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'schema error: {exp}')
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def issue_shorts_save(params: Any) -> ResponseType:
    """
    Deletes all short stories associated with an issue and adds new ones.

    Args:
        params (dict): A dictionary containing the parameters for saving the
                      short stories.
            It should have the following keys:
            - 'issue_id': The ID of the issue.
            - 'shorts': A list of dictionaries, each containing the parameters
                       for a short story.
                       Each dictionary should have the following key:
                       - 'id': The ID of the short story.

    Returns:
        ResponseType: The response object containing the result of the
                      operation.
    """
    session = new_session()
    try:
        old_stories_list = session.query(IssueContent)\
            .filter(IssueContent.issue_id == params['issue_id'])\
            .filter(IssueContent.shortstory_id.isnot(None))\
            .all()

        for story in old_stories_list:
            session.delete(story)
        session.flush()

        for story in params['shorts']:
            content = IssueContent()
            content.issue_id = params['issue_id']
            content.shortstory_id = story
            session.add(content)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'{exp}')
        return ResponseType(f'Tietokantavirhe. id={params["issue_id"]}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType('ok', HttpResponseCode.OK.value)


def issue_articles_get(issue_id: int) -> ResponseType:
    """ Returns a list of articles associated with an issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        ResponseType: The response object containing the list of articles.
    """
    session = new_session()
    try:
        articles = session.query(Article)\
            .join(IssueContent, Article.id == IssueContent.article_id)\
            .filter(IssueContent.issue_id == issue_id)\
            .filter(IssueContent.article_id.isnot(None))\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'{exp}')
        return ResponseType(f'Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = ArticleBriefSchema(many=True)
        retval = schema.dump(articles)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'schema error: {exp}')
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def issue_articles_save(params: Any) -> ResponseType:
    """
    Deletes all articles associated with an issue and adds new ones.

    Args:
        params (dict): A dictionary containing the parameters for saving the
                      articles.
            It should have the following keys:
            - 'issue_id': The ID of the issue.
            - 'articles': A list of dictionaries, each containing the
                          parameters for an article.
                          Each dictionary should have the following key:
                          - 'id': The ID of the article.

    Returns:
        ResponseType: The response object containing the result of the
                      operation.
    """
    session = new_session()
    try:
        old_articles_list = session.query(IssueContent)\
            .filter(IssueContent.issue_id == params['issue_id'])\
            .filter(IssueContent.article_id.isnot(None))\
            .all()

        for article in old_articles_list:
            session.delete(article)
        session.flush()

        for article in params['articles']:
            content = IssueContent()
            content.issue_id = params['issue_id']
            content.article_id = article
            session.add(content)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'{exp}')
        return ResponseType(f'Tietokantavirhe. id={params["issue_id"]}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType('ok', HttpResponseCode.OK.value)


def get_issue_tags(issue_id: int) -> ResponseType:
    """
    Get the tags associated with a specific issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        ResponseType: The response object containing the tags associated with
                      the issue.
    """
    session = new_session()
    try:
        tags = session.query(Tag)\
            .join(IssueTag)\
            .filter(IssueTag.issue_id == issue_id)\
            .filter(IssueTag.tag_id == Tag.id)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_issue_tags: {exp}')
        return ResponseType(f'get_issue_tags: Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = TagSchema(many=True)
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_issue_tags schema error: {exp}')
        return ResponseType('get_issue_tags: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def issue_tag_add(issue_id: int, tag_id: int) -> ResponseType:
    """
    Adds a tag to an issue.

    Args:
        issue_id (int): The ID of the issue.
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: The response object containing the result of the
                      operation.
    """
    session = new_session()

    try:
        short = session.query(Issue).filter(
            Issue.id == issue_id).first()
        if not short:
            app.logger.error(
                f'issue_tag_add: Issue not found. Id = {issue_id}.')
            return ResponseType('Numeroa ei löydy',
                                HttpResponseCode.BAD_REQUEST.value)

        issue_tag = IssueTag()
        issue_tag.issue_id = issue_id
        issue_tag.tag_id = tag_id
        session.add(issue_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'issue_tag_add() ({issue_id}, {tag_id}): {exp}')
        return ResponseType('issue_tag_add: Tietokantavirhe. '
                            f'issue_id={issue_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('', HttpResponseCode.OK.value)


def issue_tag_remove(issue_id: int, tag_id: int) -> ResponseType:
    """
    Removes a tag from an issue.

    Args:
        issue_id (int): The ID of the issue.
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: The response type object.

    Raises:
        SQLAlchemyError: If there is an error with the SQLAlchemy operation.

    """
    session = new_session()

    try:
        issue_tag = session.query(IssueTag)\
            .filter(IssueTag.issue_id == issue_id, IssueTag.tag_id == tag_id)\
            .first()
        if not issue_tag:
            app.logger.error(
                ('issue_tag_remove: Issue has no such tag: '
                 f'issue_id {issue_id}, '
                 f'tag {tag_id}.')
            )
            return ResponseType('issue_tag_remove: Tagia ei löydy numerolta. '
                                f'issue_id={issue_id}, tag_id={tag_id}.',
                                HttpResponseCode.BAD_REQUEST.value)
        session.delete(issue_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'issue_tag_remove() ({issue_id}, {tag_id}): {exp}')
        return ResponseType('issue_tag_remove: Tietokantavirhe. '
                            f'issue_id={issue_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('', HttpResponseCode.OK.value)


def publication_sizes() -> ResponseType:
    """
    Retrieves a list of all publication sizes.

    Returns:
        ResponseType: The response type object containing the list of
        publication sizes.
    """
    session = new_session()
    sizes = session.query(PublicationSize).all()

    schema = PublicationSizeBriefSchema(many=True)
    retval = schema.dump(sizes)
    return ResponseType(retval, HttpResponseCode.OK.value)


def issue_image_add(issue_id: int, image: FieldStorage) -> ResponseType:
    """
    Uploads an image for a specific issue.

    Args:
        id (int): The ID of the issue.
        file (FileStorage): The image file.

    Returns:
        ResponseType: The response object containing the result of the image
                      upload.
    """
    old_values: Dict[str, Union[str, None]] = {}
    session = new_session()
    issue = session.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        app.logger.error(f'Issue not found. Id = {issue_id}.')
        return ResponseType('Numeroa ei käytynyt',
                            HttpResponseCode.BAD_REQUEST.value)

    image_name = image.filename
    if not image_name or image_name == "":
        app.logger.error('Kuvan nimi puuttuu.')
        return ResponseType('Kuvan nimi puuttuu',
                            HttpResponseCode.BAD_REQUEST.value)

    if not allowed_image(image_name):
        app.logger.error('Virheellinen kuvan tyyppi.')
        return ResponseType('Virheellinen kuvan tyyppi',
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        filename = secure_filename(image_name)
        file_loc = os.path.join(app.config["MAGAZINECOVER_SAVELOC"], filename)
        image.save(file_loc)
    except IOError as exp:
        app.logger.error(f'{exp}')
        return ResponseType('Tiedoston tallennus epäonnistui',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    issue.image_src = app.config['MAGAZINECOVER_DIR'] + filename
    try:
        session.add(issue)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(f'{exp}')
        return ResponseType(f'Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_changes(session=session,
                obj=issue,
                action='Päivitys',
                old_values=old_values)
    session.commit()
    return ResponseType('OK', HttpResponseCode.OK.value)


def issue_image_delete(issue_id: int) -> ResponseType:
    """
    Deletes an issue image.

    Args:
        id (int): The ID of the issue.

    Returns:
        ResponseType: The response object containing the result of the
                      operation.
    """
    session = new_session()

    try:
        issue = session.query(Issue).filter(Issue.id == issue_id).first()
        issue.image_src = None
        session.add(issue)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(f'{exp}')
        return ResponseType(f'Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('ok', HttpResponseCode.OK.value)
