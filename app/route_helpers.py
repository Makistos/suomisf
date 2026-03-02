"""
    This module contains the functions related to routes that are not directly
    route definitions.
"""

from typing import List, Dict, Any, Tuple, Set, Union
from functools import wraps
import json
import itertools
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.pool import NullPool
from flask_login import current_user  # type: ignore
from flask import abort, Response
from app.orm_decl import (Language, Person, Publisher,
                          Pubseries, Bookseries,
                          PublicationSize, Tag, PersonTag, BindingType, Format,
                          Genre, ShortStory, ArticleTag, WorkGenre, Log)
from app import db_url


def new_session() -> Any:
    ''' Create a new SQLAlchemy database session handle.

    Returns:
        Any: Session handler.
    '''
    engine = create_engine(db_url, poolclass=NullPool)
    # engine = create_engine(db_url, poolclass=NullPool, echo=True)
    # app.config['SQLALCHEMY_DATABASE_URI'], poolclass=NullPool)
    session_obj = sessionmaker(bind=engine)
    session = session_obj()
    return session


def admin_required(f: Any) -> Any:
    """
    Decorator that checks if the current user is an admin before allowing
    access to a function.

    Parameters:
        f (Any): The function to be wrapped.

    Returns:
        Any: The wrapped function.

    Raises:
        HTTPException: If the current user is not an admin (status code 401).
    """
    @wraps(f)
    def wrap(*args: Any, **kwargs: Any) -> Any:
        if current_user.is_admin:
            return f(*args, **kwargs)
        abort(401)
    return wrap


table_locals = {'article': 'Artikkeli',
                'edition': 'Painos',
                'issue': 'Irtonumero',
                'magazine': 'Lehti',
                'person': 'Henkilö',
                'publisher': 'Kustantaja',
                'shortstory': 'Novelli',
                'work': 'Teos'}


def log_change(session: Any, obj: Any, action: str = 'Päivitys',
               fields: List[str] = []) -> None:
    ''' Log a change made to data.

    Args:
        session (Any): Session handler.
        obj (Any): Object that was changed.
        action (str, optional): Description of change, either "Päivitys" or
                                "Uusi". Defaults to 'Päivitys'.
        fields (List[str], optional): Fields that were changed. Needed for
                                      "Päivitys", not used for "Uusi". Defaults
                                      to [].
    '''
    name: str = obj.name
    tbl_name = table_locals[obj.__table__.name]
    if action == 'Päivitys':
        for field in fields:
            log = Log(table_name=tbl_name, table_id=obj.id, action=action,
                      field_name=field,
                      object_name=name,
                      user_id=current_user.get_id(),
                      date=datetime.now())
            session.add(log)
    else:
        log = Log(table_name=tbl_name, table_id=obj.id, action=action,
                  field_name='',
                  object_name=name,
                  user_id=current_user.get_id(),
                  date=datetime.now())
        session.add(log)
    session.commit()


def publisher_list(session: Any) -> Dict[str, List[str]]:
    ''' Get a list of publishers from the database.

    Args:
        session (Any): Session handler.

    Returns:
        Dict[str, List[str]]:
    '''
    return {
        'publisher': [str(x.name) for x in
                      session.query(Publisher).order_by(Publisher.name).all()]}


def pubseries_list(session: Any, pubid: Any) -> List[Tuple[str, str]]:
    """
    Generate a list of tuples containing the ID and name of pubseries.

    Args:
        session (Any): The session object for the database connection.
        pubid (Any): The ID of the publisher. If pubid is not 0, the query will
                     filter by publisher_id.

    Returns:
        List[Tuple[str, str]]: A list of tuples containing the ID and name of
                               pubseries.
    """
    retval = [('0', 'Ei sarjaa')]

    if pubid != 0:
        return retval + [(str(x.id), str(x.name)) for x in
                         session.query(Pubseries).filter(Pubseries.publisher_id == pubid).order_by(Pubseries.name).all()]
    else:
        return retval + [(str(x.id), str(x.name)) for x in
                         session.query(Pubseries).order_by(Pubseries.name).all()]


def size_list(session: Any) -> List[Tuple[str, str]]:
    """
    Returns a list of tuples containing the id and name of each publication
    size in the given session.

    Parameters:
    - session: An instance of the session object.

    Returns:
    - A list of tuples, where each tuple contains the id and name of a
      publication size.
    """
    return [(str(x.id), str(x.name)) for x in
            session.query(PublicationSize).all()]


def binding_list(session: Any) -> List[Tuple[str, str]]:
    return [(str(x.id), str(x.name)) for x in
            session.query(BindingType).all()]


def format_list(session: Any) -> List[Tuple[str, str]]:
    return [(str(x.id), str(x.name)) for x in
            session.query(Format).all()]


def bookseries_list(session: Any) -> Dict[str, List[str]]:
    return {'bookseries': [str(x.name) for x in
                           session.query(Bookseries).order_by(Bookseries.name).all()]}


def get_select_ids(form: Any, item_field: str = 'itemId') -> Tuple[int, List[Dict[str, str]]]:
    ''' Read parameters from  a front end request for a select component.

        Each request has the parent id (work id etc) and a list of item ids
        corresponding to the items selected in a select component. This
        function parses these fields and returns parent id and a list containing
        the ids as ints.

        Args:
            form (request.form): Form that contains the values.
            item_field (str): Name for the parent id field. Default: "itemId".

        Returns:
            Tuple[int, List[int]]: A tuple of parent id and list of item ids.
    '''
    if ('items' not in form or item_field not in form):
        abort(400)

    parentid = int(json.loads(form[item_field]))
    items = json.loads(form['items'])
    # items = {int(x['id']): x['text']} for x in items]

    return(parentid, items)


def get_join_changes(existing: Union[List[int], Set[int]], new: List[int]) -> Tuple[List[int], List[int]]:
    to_add: List[int] = new
    to_delete: List[int] = []

    if existing:
        for id in existing:
            if id in new:
                to_add.remove(id)
            else:
                to_delete.append(id)

    return (to_add, to_delete)

# ArticleTag.article


def create_booklisting(works: Any) -> str:
    page: str = ''
    for author in works:
        author_name = author[0]
        works = author[1]
        page += r'''<h2><span class="person-list">%s</span></h2>''' % author_name
        page += '\n'
        for work in works:
            page += str(work)
            page += '\n'
            editions = list(work.editions)
            if len(editions) > 1:
                for edition in editions[1:]:
                    page += str(edition)
                    page += '\n'
        page += '\n\n'
    return page


def work_grouper(x: Any) -> str: return str(x.author_str)


def make_book_list(books: Any, author_name: str = '') -> Tuple[List[Tuple[str, Any]], int]:
    it = itertools.groupby(books, work_grouper)
    works_d: Dict[str, Any] = {}
    for key, group in it:
        if author_name != '':
            if author_name.lower() not in key.lower():
                continue
        for work in group:
            if key in works_d:
                works_d[key].append(work)
            else:
                works_d[key] = []
                works_d[key].append(work)
    works: List[Tuple[str, Any]] = list(works_d.items())
    works.sort()

    count = sum([len(x[1]) for x in works])
    return (works, count)


def save_join(session: Any, cls: object, *paths: Any) -> None:

    options = [joinedload(path) for path in paths]
    existing = session.query(cls).options(*options).all()
    # existing = session.query(cls)\
    #                  .filter(join1 == itemid)\
    #                  .all()
    # (to_add, to_remove) = get_join_changes(x.)

    session.commit()


def save_story_to_issue(session, issueid, name):
    pass


def save_newstory_to_issue(session, issueid, form):
    pass


def translate_genrelist(glist):
    return glist


def save_genres(session, work, genrefield):

    genres = session.query(WorkGenre)\
                    .filter(WorkGenre.work_id == work.id)
    genres.delete()
    for g in genrefield:
        # genre = session.query(Genre).filter(Genre.id == g).first()
        genreobj = WorkGenre(work_id=work.id, genre_id=g)
        session.add(genreobj)
    session.commit()


def genre_summary(books: Any) -> Dict[str, Tuple[int, str]]:
    retval: Dict[str, Tuple[int, str]] = {}

    for book in books:
        for genre in book.genres:
            if genre.abbr not in retval:
                retval[genre.abbr] = (1, genre.name)
            else:
                v, g = retval[genre.abbr]
                retval[genre.abbr] = (v+1, g)
    retval['Yht'] = (len(books), 'Yhteensä')
    return retval


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


def genre_select(session: Any) -> List[Tuple[str, str]]:
    genres = session.query(Genre).all()
    return [(str(x.id), x.name) for x in genres]


def make_people_response(people: Any) -> Any:
    retval: List[Dict[str, str]] = []
    if people:
        for person in people:
            obj: Dict[str, str] = {}
            obj['id'] = str(person.id)
            obj['text'] = person.name
            retval.append(obj)

    return Response(json.dumps(retval))


def create_new_people(session: Any, names: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    retval: List[Dict[str, Any]] = []

    for person in names:
        name = person['text']
        if person['id'] == name:
            new_person = Person(name=name)
            session.add(new_person)
            session.commit()
            id = new_person.id
            name = new_person.name
        else:
            id = int(person['id'])
        retval.append({'id': id, 'text': name})

    return retval


def create_new_tags(
        session: Any, tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    retval: List[Dict[str, Any]] = []

    for tag in tags:
        name = tag['text']
        t = session.query(Tag).filter(Tag.name == name).first()
        if not t:
            # if tag['id'] == name:
            new_tag = Tag(name=name, type_id=1)
            session.add(new_tag)
            session.commit()
            tag_id = new_tag.id
            name = new_tag.name
        else:
            tag_id = t.id
        retval.append({'id': tag_id, 'text': name, 'type_id': 1})

    return retval


def create_new_languages(session: Any, languages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    retval: List[Dict[str, Any]] = []

    for lang in languages:
        name = lang['text']
        if lang['id'] == name:
            new_lang = Language(name=name)
            session.add(new_lang)
            session.commit()
            id = new_lang.id
            name = new_lang.name
        else:
            id = int(lang['id'])
        retval.append({'id': id, 'text': name})

    return retval


def create_new_shortstory_to_work(session: Any, stories: List[Dict[str, Any]], workid: int) -> List[Dict[str, Any]]:
    retval: List[Dict[str, Any]] = []

    for story in stories:
        title = story['text']
        if story['id'] == title:
            new_story = ShortStory(title=title)
            session.add(new_story)
            session.commit()
            id = new_story.id
            title = new_story.title
        else:
            id = int(story['id'])
        retval.append({'id': id, 'text': title})

    return retval


def create_new_language(session: Any, lang_name: str) -> Tuple[int, str]:
    lang = Language(name=lang_name)
    session.add(lang)
    session.commit()

    return (lang.id, lang.name)


# Called when a person's name field is changed. This requires updating all
# author strings in works.
def dynamic_changed(original_list: List[Any], new_list: List[Any]) -> bool:
    ''' Check if contents of a dynamic field (e.g. links section) has changed.

    Args:
        original_list (List[Any]): Old values, use the database reference,
                                    e.g. person.links
        param new_list (List[Any]): Contents of the field when saving.
                                    Use the field's data, e.g. form.links.data.

    Returns:
        bool: True if user made changes, False otherwise.
    '''
    if len(original_list) != len(new_list):
        return True
    for i in range(len(original_list)):
        if original_list[i] != new_list[i]:
            return True

    return False


def awards_to_data(awards: List[Any]) -> List[Dict[str, Any]]:
    retval: List[Dict[str, Any]] = []

    for award in awards:
        item = {'year': award.year,
                'name': award.award.name,
                'award_id': award.award.id,
                'category': award.category.name,
                'category_id': award.category.id}
        retval.append(item)

    return retval


def links_to_data(links: List[Any]) -> List[Dict[str, Any]]:
    retval: List[Dict[str, Any]] = []

    for link in links:
        item = {'link': link.link,
                'description': link.description}
        retval.append(item)
    return retval
