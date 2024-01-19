"""
Module for award-related functions.
"""
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.route_helpers import new_session
from app.impl import ResponseType
from app.model import AwardBriefSchema, AwardSchema, AwardedSchema
from app.orm_decl import Award, Awarded, Contributor, Part, ShortStory, Work
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
        app.logger.error(f'list_awards: {exp}.')
        return ResponseType(f'list_awards tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = AwardBriefSchema(many=True)
        awards = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'list_awards schema error: {exp}.')
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
        app.logger.error(f'get_award: {exp}.')
        return ResponseType(
            f'get_award: Tietokantavirhe. id={award_id}: {exp}.',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = AwardSchema()
        retval = schema.dump(award)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_award schema error: {exp}.')
        return ResponseType(f'get_award: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK)


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
        app.logger.error(f'get_awards_for_work: {exp}.')
        return ResponseType(f'get_awards_for_work: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardedSchema(many=True)
        retval = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_awards_for_work schema error: {exp}.')
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
            .distinct()\
            .all()

        short_awards = session.query(Awarded)\
            .join(ShortStory)\
            .filter(Awarded.story_id == ShortStory.id)\
            .join(Part, Part.shortstory_id == ShortStory.id)\
            .join(Contributor, Contributor.part_id == Part.id)\
            .filter(Contributor.person_id == person_id)\
            .distinct()\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_person_awards: {exp}.')
        return ResponseType(f'get_person_awards: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    all_awards = person_awards + work_awards + short_awards

    try:
        schema = AwardedSchema(many=True)
        retval = schema.dump(all_awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_person_awards schema error: {exp}.')
        return ResponseType(f'get_person_awards: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def get_story_awards(story_id: int) -> ResponseType:
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
        app.logger.error(f'get_story_awards: {exp}.')
        return ResponseType(f'get_story_awards: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardedSchema(many=True)
        retval = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_story_awards schema error: {exp}.')
        return ResponseType(f'get_story_awards: Skeemavirhe. {exp}.',
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
        app.logger.error(f'update_awarded: {exp}.')
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
        app.logger.error(f'update_awarded: {exp}.')
        return ResponseType(f'update_awarded: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)
