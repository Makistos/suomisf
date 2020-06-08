import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
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
    title = Column(String(200), nullable=False)
    # If author exists in db, use ArticleAuthor instead.
    # This is for cases where we don't want to add a row
    # to Person table.
    author = Column(String(200))
    # If person exists in db, use ArticlePerson instead.
    # This is for cases where we don't want to add a row
    # to Person table.
    person = Column(String(200))

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
    type = Column(Integer)  # For persons or works/stories
    description = Column(String(500))

class Awarded(Base):
    __tablename__ = 'awarded'
    id = Column(Integer, primary_key=True)
    award_id = Column(Integer, ForeignKey('award.id'))
    person_id = Column(Integer, ForeignKey('person.id'))
    work_id = Column(Integer, ForeignKey('work.id'))
    story_id = Column(Integer, ForeignKey('shortstory.id'))

class BindingType(Base):
    __tablename__ = 'bindingtype'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

class Bookseries(Base):
    __tablename__ = 'bookseries'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
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
    pubyear = Column(Integer)
    translation = Column(Boolean)
    language = Column(String(2))
    publisher_id = Column(Integer, ForeignKey('publisher.id'))
    editionnum = Column(Integer)
    image_src = Column(String(200))
    isbn = Column(String(13))
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'))
    pubseriesnum = Column(Integer)
    collection = Column(Boolean)
    pages = Column(Integer)
    coll_info = Column(String(200))
    pages = Column(Integer)
    cover = Column(Integer, ForeignKey('covertype.id'))
    binding = Column(Integer, ForeignKey('bindingtype.id'))
    description = Column(String(500))
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
    edits = relationship("Edition", backref=backref("edition2_assoc"))
    person = relationship("Person", backref=backref("person3_assoc"))

class Genre(Base):
    __tablename__ = 'genre'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    abbr = Column(String(20), nullable=False)
    works = relationship('Work', secondary='workgenre', backref=backref('workgenre_asooc'))

class Issue(Base):
    __tablename__ = 'issue'
    id = Column(Integer, primary_key=True)
    magazine_id = Column(Integer, ForeignKey('magazine.id'), nullable=False)
    number = Column(Integer, nullable=False)
    year = Column(Integer)
    editor = Column(Integer, ForeignKey('person.id'))
    image_src = Column(String(200))
    pages = Column(Integer)
    size = Column(Integer, ForeignKey('publicationsize.id'))
    link = Column(String(200))
    notes = Column(String(200))

class IssueContent(Base):
    __tablename__ = 'issuecontent'
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('issue.id'), nullable=False)
    article_id = Column(Integer, ForeignKey('article.id'))
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'))
    title = Column(String(200), nullable=False)

class Link(Base): ###
    __tablename__ = 'link'
    id = Column(Integer, primary_key=True)
    src = Column(String, nullable=False)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=True)
    work_id = Column(Integer, ForeignKey('work.id'), nullable=True)
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=True)
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'), nullable=True)
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'),
        nullable=True)
    publisher_id = Column(Integer, ForeignKey('publisher.id'), nullable=True)

class Magazine(Base):
    __tablename__ = 'magazine'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    publisher_id = Column(Integer, ForeignKey('publisher.id'))
    issn = Column(String(30))

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
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False)
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False)
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
    alt_name = Column(String(250))
    first_name = Column(String(100))
    last_name = Column(String(150))
    image = Column(String(100))  # Actual URL
    image_src_url = Column(String(200))  # URL to source website
    image_src = Column(String(100))  # Source website name
    dob = Column(Integer)
    dod = Column(Integer)
    bio = Column(String(1000))  # Biographgy
    bio_src_url = Column(String(200))  # URL to source website
    bio_src = Column(String(100))  # Source website name
    birthplace = Column(String(250))
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

class PersonLink(Base):
    __tablename__ = 'personlink'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))

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
    editions = relationship("Edition", backref=backref("edition4_assoc"))
    fullname = Column(String(250), nullable=False, unique=True)

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
    language = Column(String(2))
    pubyear = Column(Integer)
    genre = Column(String(100))
    creator_str = Column(String(500), index=True)
    parts = relationship('Part', backref=backref('part_assoc'), uselist=True)

class StoryGenre(Base):
    __tablename__ = 'storygenre'
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'),
            nullable=False, primary_key=True)
    genre_id = Column(Integer, ForeignKey('genre.id'),
            nullable=False, primary_key=True)

class Translator(Base):
    __tablename__ = 'translator'
    part_id = Column(Integer, ForeignKey('part.id'), nullable=False,
            primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
            primary_key=True)
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
    orig_title = Column(String(500), nullable=False, index=True)
    pubyear = Column(Integer)
    language = Column(String(2))
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'))
    bookseriesnum = Column(String(20))
    bookseriesorder = Column(Integer)
    collection = Column(Boolean)
    image_src = Column(String(200))
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
    editions = relationship("Edition", secondary='part', uselist=True)
    genres = relationship("Genre", secondary='workgenre', uselist=True)

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
    work = relationship('Work', backref=backref('work2_assoc'))
    genre = relationship('Genre', backref=backref('genre2_assoc'))

class WorkLink(Base):
    __tablename__ = 'worklink'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
            primary_key=True)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


@login.user_loader
def load_user(id):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session.query(User).get(int(id))

engine = create_engine(db_url) #, echo=True)

Base.metadata.create_all(engine)
