"""
Module for award-related functions.
"""
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.route_helpers import new_session
from app.impl import ResponseType
from app.model import (AwardBriefSchema, AwardCategorySchema, AwardSchema,
                       AwardedSchema)
from app.orm_decl import (Award, AwardCategories, AwardCategory, Awarded,
                          Contributor, Part, ShortStory, Work)
from app.types import HttpResponseCode

from app import app


def list_awards() -> ResponseType:
    """
    List all awards.

    Returns:
      list: A list of Award objects.
    """
    session = new_session()
    try:
        awards = session.query(Award).order_by(Award.name).all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'list_awards tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = AwardBriefSchema(many=True)
        awards = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'list_awards skeemavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(awards, HttpResponseCode.OK.value)


def get_award(award_id: int) -> ResponseType:
    """
    Get an award.

    Args:
      award_id (int): The ID of the award to retrieve.

    Returns:
      Award: The retrieved award object.
    """
    session = new_session()

    try:
        award = session.query(Award).filter(Award.id == award_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(
            f'Tietokantavirhe. id={award_id}: {exp}.',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = AwardSchema()
        retval = schema.dump(award)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_award: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK)


def get_awards_by_filter(filter: str) -> ResponseType:
    """
    Get all awards that match a given filter.

    Args:
        filter (str): The filter to apply to the awards.

    Returns:
        ResponseType: The list of awards that match the given filter.
    """
    session = new_session()

    try:
        awards = session.query(Award)\
            .filter(Award.name.ilike(f'%{filter}%'))\
            .order_by(Award.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'get_awards_by_filter: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardBriefSchema(many=True)
        retval = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_awards_by_filter: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_awards_for_work(work_id: int) -> ResponseType:
    """
    Get the awards for a specific work.

    Args:
        work_id (int): The ID of the work.

    Returns:
        ResponseType: The list of awards for the work.
    """
    session = new_session()

    try:
        awards = session.query(Awarded)\
            .filter(Awarded.work_id == work_id)\
            .order_by(Awarded.year)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'get_awards_for_work: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardedSchema(many=True)
        retval = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_awards_for_work: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_person_awards(person_id: int) -> ResponseType:
    """
    Get the awards for a specific person.

    This also includes awards for works and shorts.

    Args:
        person_id (int): The ID of the person.

    Returns:
        ResponseType: The list of awards for the person.
    """
    session = new_session()

    try:
        person_awards = session.query(Awarded)\
            .filter(Awarded.person_id == person_id)\
            .order_by(Awarded.year)\
            .all()

        work_awards = session.query(Awarded)\
            .join(Work)\
            .filter(Awarded.work_id == Work.id)\
            .join(Part, Part.work_id == Work.id)\
            .join(Contributor, Contributor.part_id == Part.id)\
            .filter(Contributor.person_id == person_id)\
            .filter(Contributor.role_id == 1)\
            .distinct()\
            .order_by(Awarded.year)\
            .all()

        short_awards = session.query(Awarded)\
            .join(ShortStory)\
            .filter(Awarded.story_id == ShortStory.id)\
            .join(Part, Part.shortstory_id == ShortStory.id)\
            .join(Contributor, Contributor.part_id == Part.id)\
            .filter(Contributor.person_id == person_id)\
            .filter(Contributor.role_id == 1)\
            .distinct()\
            .order_by(Awarded.year)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'get_person_awards: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    all_awards = person_awards + work_awards + short_awards

    try:
        schema = AwardedSchema(many=True)
        retval = schema.dump(all_awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_person_awards: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def get_awards_for_short(story_id: int) -> ResponseType:
    """
    Get the awards for a specific story.

    Args:
        story_id (int): The ID of the story.

    Returns:
        ResponseType: The list of awards for the story.
    """
    session = new_session()

    try:
        awards = session.query(Awarded)\
            .filter(Awarded.story_id == story_id)\
            .order_by(Awarded.year)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'get_story_awards: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardedSchema(many=True)
        retval = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error('Schema error: {exp}.')
        return ResponseType(f'get_story_awards: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def get_categories_for_award(award_id: int) -> ResponseType:
    """
    Get the categories for a specific award.

    Args:
        award_id (int): The ID of the award.

    Returns:
        ResponseType: The list of categories for the award.
    """
    session = new_session()

    try:
        categories = session.query(AwardCategory)\
            .join(AwardCategories)\
            .filter(AwardCategory.id == AwardCategories.award_id)\
            .filter(AwardCategories.award_id == award_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(
            f'get_categories_for_award: Tietokantavirhe. {exp}.',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardSchema()
        retval = schema.dump(categories)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_categories_for_award: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def get_categories_for_type(type: str) -> ResponseType:
    session = new_session()

    if type == 'person':
        type = 0
    elif type == 'work':
        type = 1
    elif type == 'story':
        type = 2
    else:
        app.logger.error('get_categories_for_type: Unknown award type: '
                         f'{type}.')
        return ResponseType('get_categories_for_type: Virheellinen '
                            f'palkintotyyppi: {type}.',
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        categories = session.query(AwardCategory)\
            .filter(AwardCategory.type == type)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(
            f'get_categories_for_type: Tietokantavirhe. {exp}.',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardCategorySchema(many=True)
        retval = schema.dump(categories)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_categories_for_type: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def get_awards_for_type(award_type: str) -> ResponseType:
    """
    Get the awards for a specific type of object.

    Args:
        award_type (str): The type of object to get the awards for.
        id (int): The ID of the object.

    Returns:
        ResponseType: The list of awards for the object.
    """
    session = new_session()

    award_type = 0

    if award_type == 'person':
        award_type = 0
    elif award_type == 'work':
        award_type = 1
    elif award_type == 'story':
        award_type = 2
    else:
        app.logger.error('get_awards_for_type: Unknown award type: '
                         f'{award_type}.')
        return ResponseType('get_awards_for_type: Virheellinen '
                            f'palkintotyyppi: {award_type}.',
                            HttpResponseCode.BAD_REQUEST.value)
    try:
        awards = session.query(Award)\
            .join(AwardCategories)\
            .filter(Award.id == AwardCategories.award_id)\
            .join(AwardCategory)\
            .filter(AwardCategories.category_id == AwardCategory.id)\
            .filter(AwardCategory.type == award_type)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'get_awards_for_type: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardedSchema(many=True)
        retval = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_awards_for_type: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def update_awarded(params: Any) -> ResponseType:
    """
    Updates the awarded data based on the provided parameters.

    Does not log changes at the moment.

    Args:
        params (Any): The parameters for the update operation.

    Returns:
        ResponseType: The response type indicating the status of the update
        operation.
    """
    session = new_session()
    data = params["data"]
    award_type = data['award_type']
    try:
        if award_type == 'person':
            old_awards = session.query(Awarded)\
                .filter(Awarded.person_id == data["person_id"])\
                .all()
        elif award_type == 'work':
            old_awards = session.query(Awarded)\
                .filter(Awarded.work_id == data["work_id"])\
                .all()
        elif award_type == 'story':
            old_awards = session.query(Awarded)\
                .filter(Awarded.story_id == data["story_id"])\
                .all()
        else:
            app.logger.error('update_awarded: Unknown award type: '
                             f'{award_type}.')
            return ResponseType('update_awarded: Virheellinen palkintotyyppi: '
                                f'{award_type}.',
                                HttpResponseCode.BAD_REQUEST.value)
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType(f'update_awarded: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Check if there are any changes
    new_awards = data['awards']  # Contains the award info from user
    changed = False
    if len(old_awards) != len(new_awards):
        changed = True
    else:
        for idx, old_award in enumerate(old_awards):
            if (old_award.year != new_awards[idx]['year'] or
                    old_award.category_id != new_awards[idx]['category_id'] or
                    old_award.award_id != new_awards[idx]['award_id'] or
                    old_award.person_id != new_awards[idx]['person_id'] or
                    old_award.work_id != new_awards[idx]['work_id'] or
                    old_award.story_id != new_awards[idx]['story_id']):
                changed = True
                break
    if not changed:
        # Nothing changed, skip rest
        return ResponseType('OK', HttpResponseCode.OK.value)

    # Save changes
    try:
        for award in old_awards:
            session.delete(award)
        for award in new_awards:
            new = Awarded()
            new.year = award['year']
            new.award_id = award['award_id']
            new.category_id = award['category_id']
            if award_type == 'person':
                new.person_id = award['person_id']
            elif award_type == 'work':
                new.work_id = award['work_id']
            elif award_type == 'story':
                new.story_id = award['story_id']
            session.add(new)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType(f'update_awarded: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def save_work_awards(params: any) -> ResponseType:
    """
    Save the awards for a work.

    Args:
        params (any): The parameters for the operation.

    Returns:
        ResponseType: The response type indicating the status of the operation.
    """
    session = new_session()
    work_id = params['work_id']
    awards = params['awards']
    try:
        old_awards = session.query(Awarded)\
            .filter(Awarded.work_id == work_id)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType(f'save_work_awards: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Check if there are any changes
    changed = False
    if len(old_awards) != len(awards):
        changed = True
    else:
        for idx, old_award in enumerate(old_awards):
            if (old_award.year != awards[idx]['year'] or
                    old_award.category_id != awards[idx]['category_id'] or
                    old_award.award_id != awards[idx]['award_id'] or
                    old_award.person_id != awards[idx]['person_id'] or
                    old_award.work_id != awards[idx]['work_id'] or
                    old_award.story_id != awards[idx]['story_id']):
                changed = True
                break
    if not changed:
        # Nothing changed, skip rest
        return ResponseType('OK', HttpResponseCode.OK.value)

    # Save changes
    try:
        for award in old_awards:
            session.delete(award)
        for award in awards:
            new = Awarded()
            new.year = award['year']
            new.award_id = award['award_id']
            new.category_id = award['category_id']
            new.work_id = award['work_id']
            session.add(new)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType(f'save_work_awards: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def save_person_awards(params: any) -> ResponseType:
    """
    Save the awards for a person.

    Args:
        params (any): The parameters for the operation.

    Returns:
        ResponseType: The response type indicating the status of the operation.
    """
    session = new_session()
    person_id = params['person_id']
    awards = params['awards']
    try:
        old_awards = session.query(Awarded)\
            .filter(Awarded.person_id == person_id)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType(f'save_person_awards: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Check if there are any changes
    changed = False
    if len(old_awards) != len(awards):
        changed = True
    else:
        for idx, old_award in enumerate(old_awards):
            if (old_award.year != awards[idx]['year'] or
                    old_award.category_id != awards[idx]['category_id'] or
                    old_award.award_id != awards[idx]['award_id'] or
                    old_award.person_id != awards[idx]['person_id'] or
                    old_award.work_id != awards[idx]['work_id'] or
                    old_award.story_id != awards[idx]['story_id']):
                changed = True
                break
    if not changed:
        # Nothing changed, skip rest
        return ResponseType('OK', HttpResponseCode.OK.value)

    # Save changes
    try:
        for award in old_awards:
            session.delete(award)
        for award in awards:
            new = Awarded()
            new.year = award['year']
            new.award_id = award['award_id']
            new.category_id = award['category_id']
            new.person_id = award['person_id']
            session.add(new)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType(f'save_person_awards: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def save_awarded(params: any):
    session = new_session()
    awards = params["awards"]
    itemId = params['id']
    typeId = params['type']

    if typeId == 0:
        itemType = 'person'
    elif typeId == 1:
        itemType = 'work'
    elif typeId:
        itemType = 'story'
    else:
        app.logger.error('save_awarded: Unknown item type.')
        return ResponseType('save_awarded: Tuntematon palkintotyyppi.',
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        for award in awards:
            # Check if award field is a string, if it is, create a new award
            if isinstance(award['award'], str):
                # Save the award name to the database
                new_award = Award()
                new_award.name = award['award']
                new_award.domestic = False

                session.add(new_award)
                session.flush()
                # Select categories for this award
                categories = session.query(AwardCategory)\
                    .filter(AwardCategory.type == itemId)\
                    .all()
                for category in categories:
                    new_category = AwardCategories()
                    new_category.award_id = new_award.id
                    new_category.category_id = category.id
                    session.add(new_category)
                session.flush()
                award['award'] = {'id': new_award.id, 'name': new_award.name}
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'save_awarded: Tietokantavirhe. {exp}.')
        return ResponseType(f'Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    except KeyError as exp:
        app.logger.error(f'save_awarded: KeyError. {exp}.')
        return ResponseType({exp},
                            HttpResponseCode.BAD_REQUEST.value)

    # Check if award was removed
    try:
        # Find awards that are not in the new data and that belong to this
        # person, work or story
        ids = [x['id'] for x in awards]
        # Delete awards that are not in the new data
        # and that belong to this person, work or story
        query = session.query(Awarded)
        if itemType == 'person':
            query = query.filter(Awarded.person_id == itemId)
        elif itemType == 'work':
            query = query.filter(Awarded.work_id == itemId)
        elif itemType == 'story':
            query = query.filter(Awarded.story_id == itemId)
        else:
            app.logger.error('save_awarded: Unknown item type.')
            return ResponseType('Tuntematon palkintotyyppi.',
                                HttpResponseCode.BAD_REQUEST.value)
        if len(ids) > 0:
            query = query.filter(Awarded.id.notin_(ids))
        query = query.delete()
        session.flush()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'save_awarded: Tietokantavirhe. {exp}.')
        return ResponseType(f'Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    except KeyError as exp:
        app.logger.error(f'save_awarded: KeyError. {exp}.')
        return ResponseType({exp},
                            HttpResponseCode.BAD_REQUEST.value)
    except AttributeError as exp:
        app.logger.error(f'save_awarded: AttributeError. {exp}.')
        return ResponseType(f'AttributeError. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        for award in awards:
            # Add new awards
            if award['id'] == 0:
                new = Awarded()
                new.year = award['year']
                new.award_id = award['award']['id']
                new.category_id = award['category']['id']
                if itemType == 'person':
                    new.person_id = award['person']['id']
                elif itemType == 'work':
                    new.work_id = award['work']['id']
                elif itemType == 'story':
                    new.story_id = award['story']['id']
                session.add(new)
            else:
                # Update existing awards
                existing = session.query(Awarded)\
                    .filter(Awarded.id == award['id'])\
                    .first()
                if existing is None:
                    app.logger.error(
                        f'save_awarded: Award not found: {award["id"]}.')
                    return ResponseType('Palkintoa ei löydy.',
                                        HttpResponseCode.BAD_REQUEST.value)
                existing.year = award['year']
                existing.award_id = award['award']['id']
                existing.category_id = award['category']['id']
                if itemType == 'person':
                    existing.person_id = award['person']['id']
                elif itemType == 'work':
                    existing.work_id = award['work']['id']
                elif itemType == 'story':
                    existing.story_id = award['story']['id']
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'save_awarded: Tietokantavirhe. {exp}.')
        return ResponseType(f'Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    except KeyError as exp:
        app.logger.error(f'save_awarded: KeyError. {exp}.')
        return ResponseType({exp},
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'save_awarded: Tietokantavirhe. {exp}.')
        return ResponseType(f'save_awarded: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType('OK', HttpResponseCode.OK.value)
