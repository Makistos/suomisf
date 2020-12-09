#!/usr/bin/python3

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from app.orm_decl import (Person, Author, Editor, Translator, Publisher, Work,
                          Edition, Part, Pubseries, Bookseries, User, UserBook, PublicationSize, Tag,
                          PersonTag, CoverType, BindingType, Format, Genre, ShortStory, ArticleTag,
                          WorkGenre)
from typing import List, Dict, Any, Tuple

"""
    This module contains the functions related to routes that are not directly
    route definitions.
"""


def new_session():
    engine = create_engine('sqlite:///suomisf.db', echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


def publisher_list(session) -> Dict[str, List[str]]:
    return {'publisher': [str(x.name) for x in
                          session.query(Publisher).order_by(Publisher.name).all()]}


def author_list(session) -> Dict[str, List[str]]:
    return {'author': [str(x.name) for x in
                       session.query(Person)
                       .join(Author)
                       .filter(Author.person_id == Person.id)
                       .distinct()
                       .order_by(Person.name)
                       .all()]}


def pubseries_list(session, pubid) -> List[Tuple[str, str]]:
    retval = [('0', 'Ei sarjaa')]

    if pubid != 0:
        return retval + [(str(x.id), str(x.name)) for x in
                         session.query(Pubseries).filter(Pubseries.publisher_id == pubid).order_by(Pubseries.name).all()]
    else:
        return retval + [(str(x.id), str(x.name)) for x in
                         session.query(Pubseries).order_by(Pubseries.name).all()]


def size_list(session) -> List[Tuple[str, str]]:
    return [(str(x.id), str(x.name)) for x in
            session.query(PublicationSize).all()]


def cover_list(session) -> List[Tuple[str, str]]:
    return [(str(x.id), str(x.name)) for x in
            session.query(CoverType).all()]


def binding_list(session) -> List[Tuple[str, str]]:
    return [(str(x.id), str(x.name)) for x in
            session.query(BindingType).all()]


def format_list(session) -> List[Tuple[str, str]]:
    return [(str(x.id), str(x.name)) for x in
            session.query(Format).all()]


def bookseries_list(session) -> Dict[str, List[str]]:
    return {'bookseries': [str(x.name) for x in
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


def editions_for_lang(workid, lang) -> List:
    """ Returns editions just for one language.
        See editions_for_work for return value structure.
    """
    return [x for x in editions_for_work(workid) if x['edition']['language']
            == lang]


def editions_for_work(workid) -> List[Dict[str, Any]]:
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
    retval: List[Dict[str, Any]] = []
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

        ed = {'edittion': edition,
              'translators': translators,
              'editors': editors,
              'pubseries': pubseries,
              'publisher': publisher}
        retval.append(ed)

    return retval


def get_first_edition(workid):
    session = new_session()

    return session.query(Edition)\
                  .join(Part)\
                  .filter(Edition.id == Part.edition_id,
                          Part.work_id == workid)\
                  .first()


def save_author_to_work(session, workid, authorname: str) -> None:

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
            author = Author(person_id=authorid, part_id=part.id)
            session.add(author)

        session.commit()

    update_work_creators(session, workid)


def save_author_to_story(session, storyid, authorname: str) -> None:

    parts = session.query(Part)\
                   .filter(Part.shortstory_id == storyid)\
                   .all()

    author = session.query(Person)\
                    .filter(Person.name == authorname)\
                    .first()

    for part in parts:
        auth = Author(part_id=part.id, person_id=author.id)
        session.add(auth)
    session.commit()

    update_story_creators(session, storyid)


def save_story_to_work(session, workid, title: str) -> None:
    story = session.query(ShortStory)\
                   .filter(ShortStory.title == title)\
                   .first()

    if not story:
        return

    editions = session.query(Edition)\
                      .join(Part)\
                      .filter(Edition.id == Part.edition_id)\
                      .filter(Part.work_id == workid)\
                      .all()

    authors = session.query(Author)\
                     .join(Part)\
                     .filter(Part.id == Author.part_id)\
                     .filter(Part.work_id == workid)\
                     .all()

    for edition in editions:
        part = Part(work_id=workid, edition_id=edition.id,
                    shortstory_id=story.id)
        session.add(part)
        session.commit()
        for author in authors:
            auth = Author(person_id=author.id, part_id=part.id)
            session.add(auth)

    work = session.query(Work).filter(Work.id == workid).first()
    work.collection = True
    session.add(work)

    session.commit()


def save_newstory_to_work(session, workid, form):

    person = session.query(Person)\
                    .filter(Person.name == form.author.data)\
                    .first()
    if not person:
        return

    s = session.query(ShortStory)\
               .filter(ShortStory.title == form.title.data)\
               .first()

    if s:
        return

    story = ShortStory(title=form.title.data,
                       orig_title=form.orig_title.data,
                       pubyear=form.pubyear.data,
                       creator_str=person.name)

    session.add(story)
    session.commit()

    save_story_to_work(session, workid, story.title)


def save_story_to_edition(session, editionid, title: str) -> None:
    story = session.query(ShortStory)\
                   .filter(ShortStory.title == title)\
                   .first()

    if not story:
        return

    works = session.query(Work)\
                   .join(Part)\
                   .filter(Part.work_id == Work.id)\
                   .filter(Part.edition_id == editionid)\
                   .all()

    authors = session.query(Author)\
                     .join(Part)\
                     .filter(Author.part_id == Part.id)\
                     .filter(Part.edition_id == editionid)\
                     .all()

    for work in works:
        part = Part(work_id=work.id,
                    edition_id=editionid,
                    shorstory_id=story.id)
        session.add(part)
        work.collection = True
        session.add(work)
        session.commit()
        for author in authors:
            auth = Author(part_id=part.id, person_id=author.id)
            session.add(auth)
            session.commit()


def save_newstory_to_edition(session, editionid, form) -> None:

    person = session.query(Person)\
                    .filter(Person.name == form.author.data)\
                    .first()
    if not person:
        return

    s = session.query(ShortStory)\
               .filter(ShortStory.title == form.title.data)\
               .first()

    if s:
        return

    story = ShortStory(title=form.title.data,
                       orig_title=form.orig_title.data,
                       pubyear=form.pubyear.data,
                       creator_str=form.author.data)

    session.add(story)
    session.commit()

    save_story_to_edition(session, editionid, story.title)


def save_translator_to_edition(session, editionid, name: str) -> None:
    translator = session.query(Person)\
                        .filter(Person.name == name)\
                        .first()

    if not translator:
        return

    parts = session.query(Part)\
                   .filter(Part.edition_id == editionid)\
                   .all()

    for part in parts:
        translator = Translator(part_id=part.id,
                                person_id=translator.id)
        session.add(translator)
    session.commit()


def save_editor_to_edition(session, editionid, name):
    editor = session.query(Person)\
                    .filter(Person.name == name)\
                    .first()

    if not editor:
        return

    editor = Editor(edition_id=editionid,
                    person_id=editor.id)
    session.add(editor)
    session.commit()


def save_story_to_issue(session, issueid, name):
    pass


def save_newstory_to_issue(session, issueid, form):
    pass


def update_work_creators(session, workid):
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


def update_story_creators(session, storyid):
    # Update story creator string
    authors = session.query(Person)\
        .join(Author)\
        .filter(Author.person_id == Person.id)\
        .join(Part)\
        .filter(Part.shortstory_id == storyid)\
        .all()

    story = session.query(ShortStory).filter(ShortStory.id == storyid).first()

    author_str = ' & '.join([x.name for x in authors])
    story.creator_str = author_str
    session.add(story)
    session.commit()


def translate_genrelist(glist):
    return glist

def save_genres(session, work, genrefield):

    genres = session.query(WorkGenre)\
                    .filter(WorkGenre.work_id == work.id)
    genres.delete()
    for g in genrefield:
        #genre = session.query(Genre).filter(Genre.id == g).first()
        genreobj = WorkGenre(work_id=work.id, genre_id=g)
        session.add(genreobj)
    session.commit()



def _add_tags(session, new_tags: List[str], old_tags: Dict[str, int]) -> List[int]:
    """ Adds any new tags to the Tag table and returns a list
        containing ids for all tags in the tags list.
    """
    new_ids: List[int] = []
    for tag in new_tags:
        # Add new tags
        if tag not in old_tags:
            tag_item = session.query(Tag).filter(Tag.name == tag).first()
            if not tag_item:
                # Complete new tag in db, add it to Tag table
                tag_item = Tag(name=tag)
                session.add(tag_item)
                session.commit()
            new_ids.append(tag_item.id)
    return new_ids


def save_tags(session, tag_list: str, tag_type: str, id: int) -> None:
    ''' Save tags for item to database creating new ones if needed.

        Parameters
        ----------
        session  : Database session.
        tag_list : Comma-separated list of tags.
        tag_type : Type of tag. Supported types: "Person".
        id       : Id of item whom tags are saved for.
    '''
    new_ids: List[int]
    new_tags = tag_list.split(',')
    new_tags = [x.strip() for x in new_tags if x.strip() != '']

    if not new_tags:
        return

    old_tags: Dict[str, int] = {}
    if tag_type == 'Person':
        link_table = PersonTag

        # Get all existing tags for person from db
        tags = session.query(Tag.name, Tag.id)\
            .join(PersonTag)\
            .filter(PersonTag.tag_id == Tag.id)\
            .filter(PersonTag.person_id == id)\
            .all()
        for tag in tags:
            old_tags[tag.name] = tag.id
        for tag in old_tags:
            # Remove any tags removed from list
            if tag not in new_tags:
                item = session.query(PersonTag)\
                    .filter(PersonTag.person_id == id)\
                    .join(Tag)\
                    .filter(PersonTag.tag_id == Tag.id)\
                    .filter(Tag.name == tag)\
                    .first()
                session.delete(item)
        new_ids = _add_tags(session, new_tags, old_tags)

        for tag in new_ids:
            # Add new tags
            person_tag = PersonTag(person_id=id,
                                   tag_id=tag)
            session.add(person_tag)
    elif tag_type == 'Article':
        tags = session.query(Tag.name, Tag.id)\
                      .join(ArticleTag)\
                      .filter(ArticleTag.tag_id == Tag.id)\
                      .filter(ArticleTag.article_id == id)\
                      .all()
        for tag in tags:
            old_tags[tag.name] = tag.id
        for tag in old_tags:
            # Remove any tags removed from list
            if tag not in new_tags:
                item = session.query(ArticleTag)\
                              .filter(ArticleTag.article_id == id)\
                              .join(Tag)\
                              .filter(ArticleTag.tag_id == Tag.id)\
                              .filter(Tag.name == tag)\
                              .first()
                session.delete(item)
            new_ids = _add_tags(session, new_tags, old_tags)

            for tag in new_ids:
                article_tag = ArticleTag(article_id=id, tag_id=tag)
                session.add(article_tag)

    session.commit()


def genre_select(session) -> List[Tuple[str, str]]:
    genres = session.query(Genre).all()
    return [(str(x.id), x.name) for x in genres]
