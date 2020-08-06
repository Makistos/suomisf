import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

Base = declarative_base()

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

db_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///suomisf.db'

class Alias(Base):
    __tablename__ = 'alias'
    alias = Column(Integer, ForeignKey('person.id'), nullable=False,
        primary_key=True)
    realname = Column(Integer, ForeignKey('person.id'), nullable=False,
        primary_key=True) ###

class Article(Base):
    __tablename__ = 'article'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False, index=True)
    # If author exists in db, use ArticleAuthor instead.
    # This is for cases where we don't want to add a row
    # to Person table.
    author = Column(String(200))
    # If person exists in db, use ArticlePerson instead.
    # This is for cases where we don't want to add a row
    # to Person table.
    person = Column(String(200))
    creator_str = Column(String(500), index=True)
    tags = relationship('Tag', secondary='articletag', uselist=True)
    links = relationship('ArticleLink', uselist=True)
    person_rel = relationship('Person', secondary='articleperson', uselist=True)
    author_rel = relationship('Person', secondary='articleauthor', uselist=True)
    issue = relationship('Issue', secondary='issuecontent', uselist=False)

class ArticleAuthor(Base):
    __tablename__ = 'articleauthor'
    article_id = Column(Integer, ForeignKey('article.id'), nullable=False,
            primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
            primary_key=True)

class ArticleLink(Base):
    __tablename__ = 'articlelink'
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'))
    link = Column(String(250), nullable=False)
    description = Column(String(100))

class ArticlePerson(Base):
    """ Links articles to persons they are about. """
    __tablename__ = 'articleperson'
    article_id = Column(Integer, ForeignKey('article.id'), nullable=False,
            primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
            primary_key=True)

class ArticleTag(Base):
    __tablename__ = 'articletag'
    article_id = Column(Integer, ForeignKey('article.id'),
            nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
            primary_key=True)


class Author(Base):
    __tablename__ = 'author'
    part_id = Column(Integer, ForeignKey('part.id'), nullable=False,
            primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
            primary_key=True)
    parts = relationship("Part", backref=backref("part_assoc1"))
    person = relationship("Person", backref=backref("person1_assoc"))

class Award(Base):
    __tablename__ = 'award'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))

class AwardCategory(Base):
    __tablename__ = 'awardcategory'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)

class Awarded(Base):
    __tablename__ = 'awarded'
    id = Column(Integer, primary_key=True)
    year = Column(Integer)
    award_id = Column(Integer, ForeignKey('award.id'))
    category_id = Column(Integer, ForeignKey('awardcategory.id'))
    person_id = Column(Integer, ForeignKey('person.id'))
    work_id = Column(Integer, ForeignKey('work.id'))
    story_id = Column(Integer, ForeignKey('shortstory.id'))
    award = relationship('Award', backref=backref('award'))
    person = relationship('Person', backref=backref('person_award'))
    work = relationship('Work', backref=backref('work_award'))
    category = relationship('AwardCategory', backref=backref('awardcategory'))
    story = relationship('ShortStory', backref=backref('shortstory_award'))

class BindingType(Base):
    __tablename__ = 'bindingtype'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

class Bookseries(Base):
    __tablename__ = 'bookseries'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, index=True)
    important = Column(Boolean, default=False)
    works = relationship("Work", backref=backref('work'), uselist=True,
                         order_by='Work.bookseriesorder, Work.creator_str')

class BookseriesLink(Base):
    __tablename__ = 'bookserieslink'
    id = Column(Integer, primary_key=True)
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'),
            nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))

class CoverType(Base):
    __tablename__ = 'covertype'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

class Edition(Base):
    ''' This is the base table for this database schema.
        Every book must have at least one Edition. Edition
        represents one edition printed in one language.
        So every existing book no matter their composition
        needs to have a row in this table.
    '''
    __tablename__ = 'edition'
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    subtitle = Column(String(500))
    pubyear = Column(Integer, index=True)
    translation = Column(Boolean)
    language = Column(String(2))
    publisher_id = Column(Integer, ForeignKey('publisher.id'))
    editionnum = Column(Integer)
    version = Column(Integer) # Laitos
    image_src = Column(String(200))
    isbn = Column(String(13))
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'))
    pubseriesnum = Column(Integer)
    collection = Column(Boolean)
    coll_info = Column(String(200))
    pages = Column(Integer)
    cover_id = Column(Integer, ForeignKey('covertype.id'))
    binding_id = Column(Integer, ForeignKey('bindingtype.id'))
    format_id = Column(Integer, ForeignKey('format.id'))
    size_id = Column(Integer, ForeignKey('publicationsize.id'))
    description = Column(String(500))
    artist_id = Column(Integer, ForeignKey('person.id'))
    misc = Column(String(500))
    imported_string = Column(String(500))
    parts = relationship('Part', backref=backref('parts_lookup'),
            uselist=True)
    editors = relationship('Person', secondary='editor')
    translators = relationship("Person",
                secondary='join(Part, Translator, Part.id == Translator.part_id)',
                primaryjoin='and_(Person.id == Translator.person_id,\
                Translator.part_id == Part.id, Part.edition_id == Edition.id)',
                uselist=True)
    work = relationship('Work', secondary='part', uselist=True)
    publisher = relationship("Publisher", backref=backref('publisher_lookup',
        uselist=False))
    pubseries = relationship("Pubseries", backref=backref('pubseries',
        uselist=False))
    owners = relationship("User", secondary='userbook')
    cover = relationship('CoverType', backref=backref('edition_cover_assoc'), uselist=False)
    binding = relationship('BindingType', backref=backref('edition_binding_assoc'), uselist=False)
    format = relationship('Format', backref=backref('edition_format_assoc'), uselist=False)
    size = relationship('PublicationSize', backref=backref('edition_size_assoc'), uselist=False)

class EditionLink(Base):
    __tablename__ = 'editionlink'
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))

class Editor(Base):
    __tablename__ = 'editor'
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False,
            primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
            primary_key=True)
    role = Column(String(100))
    edits = relationship("Edition", backref=backref("edition2_assoc"))
    person = relationship("Person", backref=backref("person3_assoc"))

class Format(Base):
    __tablename__ = 'format'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

class Genre(Base):
    __tablename__ = 'genre'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    abbr = Column(String(20), nullable=False, index=True)
    works = relationship('Work', secondary='workgenre', backref=backref('workgenre_asooc'))

class Issue(Base):
    __tablename__ = 'issue'
    id = Column(Integer, primary_key=True)
    magazine_id = Column(Integer, ForeignKey('magazine.id'), nullable=False)
    number = Column(Integer, nullable=False, index=True)
    number_extra = Column(String(20))
    count = Column(Integer)
    year = Column(Integer, index=True)
    image_src = Column(String(200))
    pages = Column(Integer)
    size_id = Column(Integer, ForeignKey('publicationsize.id'))
    link = Column(String(200))
    notes = Column(String(200))
    title = Column(String(200))
    tags = relationship('Tag', secondary='issuetag', uselist=True)
    articles = relationship('Article', secondary='issuecontent', uselist=True)
    stories = relationship('ShortStory', secondary='issuecontent', uselist=True)
    editors = relationship('Person', secondary='issueeditor', uselist=True)
    size = relationship('PublicationSize', uselist=False)
    magazine = relationship('Magazine', uselist=False)

class IssueContent(Base):
    __tablename__ = 'issuecontent'
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('issue.id'), nullable=False)
    article_id = Column(Integer, ForeignKey('article.id'))
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'))

class IssueEditor(Base):
    __tablename__ = 'issueeditor'
    issue_id = Column(Integer, ForeignKey('issue.id'),
            nullable=False, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'),
            nullable=False, primary_key=True)

class IssueTag(Base):
    __tablename__ = 'issuetag'
    issue_id = Column(Integer, ForeignKey('issue.id'),
            nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
            primary_key=True)

class Magazine(Base):
    __tablename__ = 'magazine'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    publisher_id = Column(Integer, ForeignKey('publisher.id'))
    description = Column(String(500))
    link = Column(String(200))
    issn = Column(String(30))
    tags = relationship('Tag', secondary='magazinetag', uselist=True)
    issues = relationship('Issue', backref=backref('magazine_issue'),
            uselist=True, order_by='Issue.count')
    publisher = relationship('Publisher', uselist=False)

class MagazineTag(Base):
    __tablename__ = 'magazinetag'
    magazine_id = Column(Integer, ForeignKey('magazine.id'),
            nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
            primary_key=True)


class Part(Base):
    ''' Part is most often representing a short story. So a collection
        consists of a number of parts, each representing one story.
        These are often published in different collections so there is
        no direct link between edition, part and work. Part might have
        been published in a magazine, for instance.

        Part is also used in cases where either the original work has
        been split into several volumes or several works have been combined
        into one volume. In the first case Work has one row while Edition and
        Part have as many rows as there are volumes. In the second case
        Work and Part have multiple rows and Edition has one.
    '''
    __tablename__ = 'part'
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=True)
    work_id = Column(Integer, ForeignKey('work.id'), nullable=True)
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'), nullable=True)
    # Title is repeated from edition in the simple case but required for
    # e.g. collections.
    title = Column(String(250))
    authors = relationship('Person', secondary='author', uselist=True)
    translators = relationship('Person', secondary='translator', uselist=True)
    edition = relationship('Edition', backref=backref('edition_assoc'))
    work = relationship('Work', backref=backref('work_assoc'))
    shortstory = relationship('ShortStory',
                              backref=backref('shortstory_assoc'))

class Person(Base):
    __tablename__ = 'person'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, index=True, unique=True)
    alt_name = Column(String(250), index=True)
    first_name = Column(String(100))
    last_name = Column(String(150))
    image_src = Column(String(100))  # Source website name
    image_attr = Column(String(100))
    dob = Column(Integer)
    dod = Column(Integer)
    bio = Column(String(1000))  # Biographgy
    bio_src = Column(String(100))  # Source website name
    nationality = Column(String(250))
    other_names = Column(String(200))
    imported_string = Column(String(500))
    other_names = Column(String(250))
    #real_names = relationship("Person", secondary="Alias", primaryjoin="Person.id==Alias.alias")
    real_names = relationship('Person',
                    primaryjoin=id==Alias.alias,
                    secondary='alias',
                    secondaryjoin=id==Alias.realname,
                    uselist=True)
    #aliases = relationship("Person", primaryjoin="Person.id==Alias.realname")
    aliases = relationship("Person",
                    primaryjoin=id==Alias.realname,
                    secondary='alias',
                    secondaryjoin=id==Alias.alias,
                    uselist=True)
    works = relationship("Work",
                secondary='join(Part, Author, Part.id == Author.part_id)',
                primaryjoin='and_(Person.id == Author.person_id,\
                Author.part_id == Part.id, Part.work_id == Work.id,\
                Part.shortstory_id == None)',
                order_by='Work.title',
                uselist=True)
    stories = relationship("ShortStory",
                secondary='join(Part, Author, Part.id == Author.part_id)',
                primaryjoin='and_(Person.id == Author.person_id,\
                Author.part_id == Part.id, Part.work_id == Work.id,\
                Part.shortstory_id == ShortStory.id)',
                uselist=True)
    edits = relationship("Edition", secondary='editor')
    translations = relationship("Edition",
                secondary='join(Part, Translator, Part.id == Translator.part_id)',
                primaryjoin='and_(Person.id == Translator.person_id,\
                Translator.part_id == Part.id, Part.work_id == Work.id)',
                uselist=True)
    chief_editor = relationship('Issue', secondary='issueeditor', uselist=True)
    articles = relationship('Article', secondary='articleauthor',
            uselist=True)
    magazine_stories = relationship('ShortStory',
            secondary='join(Part, Author, Part.id == Author.part_id)',
            primaryjoin='and_(Person.id == Author.person_id,\
                         IssueContent.shortstory_id == Part.shortstory_id)',
            uselist=True)
    appears_in = relationship('Article', secondary='articleperson',
            uselist=True)
    tags = relationship('Tag', secondary='persontag', uselist=True)


class PersonLink(Base):
    __tablename__ = 'personlink'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))

class PersonTag(Base):
    __tablename__ = 'persontag'
    person_id = Column(Integer, ForeignKey('person.id'),
            nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
            primary_key=True)

class Problem(Base):
    __tablename__ = 'problems'
    id = Column(Integer, primary_key=True)
    status = Column(String(20))
    comment = Column(String(500))
    tabletype = Column(String(50))
    table_id = Column(Integer)

class PublicationSize(Base):
    __tablename__ = 'publicationsize'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    mm_width = Column(Integer)
    mm_height = Column(Integer)

class Publisher(Base):
    __tablename__ = 'publisher'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, unique=True, index=True)
    fullname = Column(String(250), nullable=False, unique=True)
    editions = relationship("Edition", backref=backref("edition4_assoc"))

class PublisherLink(Base):
    __tablename__ = 'publisherlink'
    id = Column(Integer, primary_key=True)
    publisher_id = Column(Integer, ForeignKey('publisher.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))

class Pubseries(Base):
    __tablename__ = 'pubseries'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    publisher_id = Column(Integer, ForeignKey('publisher.id'), nullable=False)
    important = Column(Boolean, default=False)
    publisher = relationship("Publisher", backref=backref('publisher',
        uselist=False))
    #editions = relationship("Edition", backref=backref('edition'), uselist=True,
    #                        order_by='Edition.pubseriesnum')
    editions = relationship("Edition", primaryjoin="Pubseries.id == Edition.pubseries_id", uselist=True,
                            order_by='Edition.pubseriesnum')

class PubseriesLink(Base):
    __tablename__ = 'pubserieslink'
    id = Column(Integer, primary_key=True)
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))

class ShortStory(Base):
    __tablename__ = 'shortstory'
    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False, index=True)
    orig_title = Column(String(250))
    language = Column(String(2))
    pubyear = Column(Integer, index=True)
    creator_str = Column(String(500), index=True)
    parts = relationship('Part', backref=backref('part_assoc'), uselist=True)
    genres = relationship('Genre', secondary='storygenre', uselist=True)
    issues = relationship('Issue', secondary='issuecontent', uselist=True)
    tags = relationship('Tag', secondary='storytag', uselist=True)

class StoryGenre(Base):
    __tablename__ = 'storygenre'
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'),
            nullable=False, primary_key=True)
    genre_id = Column(Integer, ForeignKey('genre.id'),
            nullable=False, primary_key=True)
    stories = relationship('ShortStory', backref=backref('story_assoc'))
    genres = relationship('Genre', backref=backref('genre_assoc'))

class StoryTag(Base):
    __tablename__ = 'storytag'
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'),
            nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
            primary_key=True)

class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, index=True)


class Translator(Base):
    __tablename__ = 'translator'
    part_id = Column(Integer, ForeignKey('part.id'), nullable=False,
            primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
            primary_key=True)
    role = Column(String(100))
    parts = relationship("Part", backref=backref("part2_assoc"))
    person = relationship("Person", backref=backref("person2_assoc"))

class User(UserMixin, Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True, unique=True)
    password_hash = Column(String(128))
    is_admin = Column(Boolean, default=False)
    language = Column(String(2), default='FI')
    books = relationship("Edition", secondary="userbook")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}'.format(self.name)


class UserBook(Base):
    __tablename__ = 'userbook'
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False,
            primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
            primary_key=True)
    book = relationship("Edition", backref=backref("edition3_assoc"))
    user = relationship("User", backref=backref("user2_assoc"))

class UserBookseries(Base):
    __tablename__ = 'userbookseries'
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
            primary_key=True)
    series_id = Column(Integer, ForeignKey('bookseries.id'), nullable=False,
            primary_key=True)
    series = relationship("Bookseries", backref=backref("bookseries_assoc"))
    user = relationship("User", backref=backref("user4_asocc"))

class UserPubseries(Base):
    __tablename__ = 'userpubseries'
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
            primary_key=True)
    series_id = Column(Integer, ForeignKey('pubseries.id'), nullable=False,
            primary_key=True)
    series = relationship("Pubseries", backref=backref("pubseries_assoc"))
    user = relationship("User", backref=backref("user3_asocc"))
    publisher = relationship("Publisher", secondary="pubseries", viewonly=True)

class Work(Base):
    ''' Work is a more abstract idea than edition. Work is
        basically the representation of the original work of which
        editions are printed. Every work must have at least one
        edition but sometimes there is no work, this is the case
        with collections. Not all parts have necessarily been
        published in a book.
    '''
    def join_names(context):
        return '& '.join([x.name for x in authors])
    __tablename__ = 'work'
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    subtitle = Column(String(500))
    orig_title = Column(String(250))
    pubyear = Column(Integer, index=True)
    language = Column(String(2))
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'))
    bookseriesnum = Column(String(20))
    bookseriesorder = Column(Integer)
    collection = Column(Boolean)
    type = Column(Integer, ForeignKey('worktype.id'))
    image_src = Column(String(200))
    description = Column(String(500))
    misc = Column(String(500))
    imported_string = Column(String(500))
    creator_str = Column(String(500), index=True)
    authors = relationship("Person",
                secondary='join(Part, Author, Part.id == Author.part_id)',
                primaryjoin='and_(Person.id == Author.person_id,\
                Author.part_id == Part.id, Part.work_id == Work.id,\
                Part.shortstory_id == None)',
                uselist=True,
                order_by='Person.alt_name')
    translators = relationship("Person",
                secondary='join(Part, Translator, Part.id == Translator.part_id)',
                primaryjoin='and_(Person.id == Translator.person_id,\
                Translator.part_id == Part.id, Part.work_id == Work.id)',
                uselist=True)
    editions = relationship("Edition", secondary='Part', uselist=True)
    parts = relationship('Part', backref=backref('part', uselist=True))
    bookseries = relationship("Bookseries", backref=backref('bookseries'),
        uselist=False)
    editions = relationship('Edition', secondary='part', uselist=True,
                            lazy='dynamic')
    genres = relationship("Genre", secondary='workgenre', uselist=True)
    tags = relationship('Tag', secondary='worktag', uselist=True)

class WorkConsists(Base):
    __tablename__ = 'workconsists'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
            primary_key=True)
    parent_id = Column(Integer, ForeignKey('work.id'), nullable=False,
            primary_key=True)

class WorkGenre(Base):
    __tablename__ = 'workgenre'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
            primary_key=True)
    genre_id = Column(Integer, ForeignKey('genre.id'), nullable=False,
            primary_key=True)

class WorkLink(Base):
    __tablename__ = 'worklink'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
            primary_key=True)
    link = Column(String(200), nullable=False)
    description = Column(String(100))

class WorkTag(Base):
    __tablename__ = 'worktag'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
            primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
            primary_key=True)

class WorkType(Base):
    __tablename__ = 'worktype'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)

@login.user_loader
def load_user(id):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session.query(User).get(int(id))

engine = create_engine(db_url) #, echo=True)

Base.metadata.create_all(engine)
