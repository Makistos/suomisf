#!/usr/bin/python3

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from app.orm_decl import Person, Author, Editor, Translator, Publisher, Work, Edition, Part, Pubseries, Bookseries, User, UserBook

"""
    This module contains the functions related to routes that are not directly
    route definitions.
"""


def new_session():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def publisher_list(session):
    return {'publisher' : [str(x.name) for x in
            session.query(Publisher).order_by(Publisher.name).all()]}

def author_list(session):
    return {'author' : [str(x.name) for x in
            session.query(Person)\
                   .join(Author)\
                   .filter(Author.person_id == Person.id)\
                   .distinct()\
                   .order_by(Person.name)\
                   .all()]}

def pubseries_list(session, pubid):
    if pubid != 0:
        return {'pubseries' : [(str(x.id), str(x.name)) for x in
                session.query(Pubseries).filter(Pubseries.publisher_id == pubid).order_by(Pubseries.name).all()]}
    else:
        return {'pubseries' : [str(x.name) for x in
                session.query(Pubseries).order_by(Pubseries.name).all()]}


def bookseries_list(session):
    return {'bookseries' : [str(x.name) for x in
            session.query(Bookseries).order_by(Bookseries.name).all()]}

def people_for_book(s, workid, type):
    if type == 'A':
        return s.query(Person)\
                .join(Author)\
                .join(Part)\
                .filter(Author.part_id == Part.id)\
                .filter(Part.work_id == workid)\
                .all()
    elif type == 'T':
        return s.query(Person)\
                .join(Translator)\
                .join(Part)\
                .filter(Person.id == Translator.person_id)\
                .filter(Translator.part_id == Part.id)\
                .filter(Part.work_id == workid)\
                .all()
    elif type == 'E':
        return s.query(Person)\
                .join(Editor)\
                .join(Edition)\
                .filter(Person.id == Editor.person_id)\
                .filter(Editor.edition_id == Edition.id)\
                .join(Part)\
                .filter(Edition.id == Part.edition_id)\
                .filter(Part.work_id == workid)\
                .all()

def books_for_person(s, personid, type):
    if type == 'A':
        return s.query(Work)\
                .join(Part)\
                .filter(Part.work_id == Work.id)\
                .join(Author)\
                .filter(Author.person_id == personid)\
                .filter(Author.part_id == Part.id)\
                .order_by(Work.title)\
                .all()
    elif type == 'T':
        return s.query(Edition)\
                .join(Part)\
                .filter(Edition.id == Part.edition_id)\
                .join(Translator)\
                .filter(Translator.person_id == personid)\
                .filter(Translator.part_id == Part.id)\
                .all()
    elif type == 'E':
        return s.query(Edition)\
                .join(Editor)\
                .filter(Editor.person_id == personid)\
                .filter(Editor.edition_id == Edition.id)\
                .all()
    else:
        return None

def editions_for_lang(workid, lang):
    """ Returns editions just for one language.
        See editions_for_work for return value structure.
    """
    return [x for x in editions_for_work(workid) if x['edition']['language']
            == lang]


def editions_for_work(workid):
    """ Returns a list of dictionaries that include edition information as well as
        translators, editors, publisher series and publisher.
        E.g.
        [ 'edition' : {'id' : 1, 'title' : 'End of Eternity',
                        'edition_num' : 1, ... },
          'translators' : [{ 'name' : 'Tamara Translator' ... }, ...],
          'editors' : [],
          'pubseries' : [],
          'publisher' : { 'id' : 1, 'name' : 'Gollanz' },
          ...
        ]

        This list is ordered primarily by language and secondary by edition
        number.
    """
    retval = []
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    editions = session.query(Edition)\
                      .filter(Edition.work_id == workid)\
                      .orderby(Edition.language, Edition.editionnum)\
                      .all()

    for edition in editions:
        # Editions can have multiple translators and editors but only
        # one publisher series and publisher.
        translators = session.query(Person)\
                             .join(Translator)\
                             .filter(Person.id == Translator.person_id,
                                     Translator.edition_id == edition.id)\
                             .all()
        editors = session.query(Person)\
                         .join(Editor)\
                         .filter(Person.id == Editor.person_id,
                                 Editor.edition_id == edition.id)\
                         .all()
        pubseries = session.query(Pubseries)\
                           .filter(Pubseries.id == edition.pubseries_id)\
                           .first()
        publisher = session.query(Publisher)\
                           .filter(Publisher.id == edition.publisher)\
                           .first()

        ed = { 'edittion' : edition,
               'translators': translators,
               'editors' : editors,
               'pubseries': pubseries,
               'publisher': publisher }
        retval += ed

    return retval

def get_first_edition(workid):
    session = new_session()

    return session.query(Edition)\
                  .join(Part)\
                  .filter(Edition.id == Part.edition_id,
                          Part.work_id == workid)\
                  .first()

def save_author_to_work(session, workid, authorname):

    author = session.query(Person)\
                    .filter(Person.name == authorname)\
                    .first()
    if not author:
        return

    authorid = author.id

    already_exists = session.query(Author)\
                            .join(Part)\
                            .filter(Author.person_id == authorid)\
                            .filter(Part.work_id == workid)\
                            .count()
    if already_exists == 0:
        parts = session.query(Part)\
                       .filter(Part.work_id == workid)\
                       .all()
        for part in parts:
            author = Author(person_id = authorid, part_id = part.id)
            session.add(author)

        session.commit()

    update_creators(session, workid)


def update_creators(session, workid):
    # Update creator string (used to group works together)
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Author.person_id == Person.id)\
                     .join(Part)\
                     .filter(Part.work_id == workid)\
                     .all()
    work = session.query(Work).filter(Work.id == workid).first()

    author_str = ' & '.join([x.name for x in authors])
    work.creator_str = author_str
    session.add(work)
    session.commit()
