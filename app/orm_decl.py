import os
import sys
import datetime
from sqlalchemy import (Column, ForeignKey, Integer,
                        String, Boolean, Date, DateTime, Text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
from sqlalchemy.sql.elements import UnaryExpression
from sqlalchemy.sql.expression import null
from sqlalchemy.util.langhelpers import classproperty
from wtforms.fields.core import IntegerField
from app import app, db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from typing import Any, List
from sqlalchemy.ext.hybrid import Comparator, hybrid_property

Base = declarative_base()

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

db_url = app.config['SQLALCHEMY_DATABASE_URI']


class AuthorComparator(Comparator):
    def __eq__(self, other):
        pass

    def __ne__(self, other):
        pass

    def like(self, other, escape=None):
        return super().like(other, escape)

    def ilike(self, other, escape=None):
        return super().ilike(other, escape)

    def startswith(self, other: str, **kwargs):
        return super().startswith(other, **kwargs)

    def endswith(self, other: str, **kwargs):
        return super().endswith(other, **kwargs)


class Alias(Base):
    __tablename__ = 'alias'
    alias = Column(Integer, ForeignKey('person.id'), nullable=False,
                   primary_key=True)
    realname = Column(Integer, ForeignKey('person.id'), nullable=False,
                      primary_key=True)


class Article(Base):
    __tablename__ = 'article'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False, index=True)
    person = Column(String(200))
    tags = relationship('Tag', secondary='articletag',
                        uselist=True, viewonly=True)
    links = relationship('ArticleLink', uselist=True, viewonly=True)
    excerpt = Column(Text())
    person_rel = relationship(
        'Person',
        secondary='articleperson', uselist=True, viewonly=True)
    author_rel = relationship(
        'Person', secondary='articleauthor', uselist=True, viewonly=True)
    issue = relationship('Issue', secondary='issuecontent',
                         uselist=False, viewonly=True)

    _author_str: str = ''

    @hybrid_property
    def author_str(self) -> str:
        if self._author_str != '':
            return self._author_str
        if len(self.author_rel) > 0:
            self._author_str = ' & '.join([x.name for x in self.author_rel])
        return self._author_str


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


class Award(Base):
    __tablename__ = 'award'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text())
    # If this is a domestic award (these are separated in the UI):
    domestic = Column(Boolean, default=False)
    categories = relationship(
        'AwardCategory', secondary='awardcategories', viewonly=True)


class AwardCategory(Base):
    __tablename__ = 'awardcategory'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    # 0 = personal, 1 = novel, 2 = short story
    type = Column(Integer, nullable=False)


class AwardCategories(Base):
    __tablename__ = 'awardcategories'
    award_id = Column(Integer, ForeignKey('award.id'),
                      primary_key=True, nullable=False)
    category_id = Column(Integer, ForeignKey('awardcategory.id'),
                         primary_key=True, nullable=False)


class Awarded(Base):
    __tablename__ = 'awarded'
    id = Column(Integer, primary_key=True)
    year = Column(Integer)
    award_id = Column(Integer, ForeignKey('award.id'))
    category_id = Column(Integer, ForeignKey('awardcategory.id'))
    person_id = Column(Integer, ForeignKey('person.id'))
    work_id = Column(Integer, ForeignKey('work.id'))
    story_id = Column(Integer, ForeignKey('shortstory.id'))
    award = relationship('Award', backref=backref('award'), viewonly=True)
    person = relationship('Person', backref=backref(
        'person_award'), viewonly=True)
    work = relationship('Work', backref=backref('work_award'), viewonly=True)
    category = relationship('AwardCategory', backref=backref(
        'awardcategory'), viewonly=True)
    story = relationship('ShortStory', backref=backref(
        'shortstory_award'), viewonly=True)


class BindingType(Base):
    __tablename__ = 'bindingtype'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class BookCondition(Base):
    __tablename__ = 'bookcondition'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    # Used to sort conditions from best to worst
    value = Column(Integer, nullable=False)


class Bookseries(Base):
    __tablename__ = 'bookseries'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, index=True)
    orig_name = Column(String(250))
    important = Column(Boolean, default=False)
    image_src = Column(String(100))
    image_attr = Column(String(100))  # Source website name
    works = relationship("Work", backref=backref('work'), uselist=True,
                         order_by='Work.bookseriesorder', viewonly=True)


class BookseriesLink(Base):
    __tablename__ = 'bookserieslink'
    id = Column(Integer, primary_key=True)
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'),
                           nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class Contributor(Base):
    __tablename__ = 'contributor'
    part_id = Column(Integer, ForeignKey('part.id'), nullable=False,
                     primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
                       primary_key=True)
    role_id = Column(Integer, ForeignKey('contributorrole.id'),
                     nullable=False, primary_key=True)
    real_person_id = Column(Integer, ForeignKey('person.id'))
    description = Column(String(50))
    person = relationship('Person', foreign_keys=[person_id])
    parts = relationship("Part", backref=backref("part2_assoc"), viewonly=True)


class ContributorRole(Base):
    __tablename__ = 'contributorrole'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class Country(Base):
    __tablename__ = 'country'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, index=True)


class CoverArtist(Base):
    __tablename__ = 'coverartist'
    person_id = Column(Integer, ForeignKey('person.id'),
                       nullable=False, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'),
                        nullable=False, primary_key=True)


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
    pubyear = Column(Integer, index=True, nullable=False)
    publisher_id = Column(Integer, ForeignKey('publisher.id'), index=True)
    editionnum = Column(Integer)
    version = Column(Integer)  # Laitos
    # image_src = Column(String(200))
    isbn = Column(String(13))
    printedin = Column(String(50))
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'))
    pubseriesnum = Column(Integer)
    coll_info = Column(String(200))
    pages = Column(Integer)
    binding_id = Column(Integer, ForeignKey('bindingtype.id'))
    format_id = Column(Integer, ForeignKey('format.id'))
    size_id = Column(Integer, ForeignKey('publicationsize.id'))
    dustcover = Column(Integer, default=0)  # 0 = not known, 1 = no, 2 = yes
    coverimage = Column(Integer, default=0)  # 0 = not known, 1 = no, 2 = yes
    misc = Column(String(500))
    imported_string = Column(String(500))
    parts = relationship('Part', backref=backref('parts_lookup'),
                         uselist=True, viewonly=True)
    # editors = relationship('Person', secondary='editor',
    #                        uselist=True, viewonly=True)
    editors = relationship("Person",
                           secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                           primaryjoin='and_(Person.id == Contributor.person_id,\
                Contributor.part_id == Part.id, Contributor.role_id == 2, Part.edition_id == Edition.id)',
                           uselist=True, viewonly=True,
                           foreign_keys=[Contributor.person_id, Contributor.part_id, Contributor.role_id])
    translators = relationship("Person",
                               secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                               primaryjoin='and_(Person.id == Contributor.person_id,\
                Contributor.part_id == Part.id, Contributor.role_id == 1, Part.edition_id == Edition.id)',
                               uselist=True, viewonly=True,
                               foreign_keys=[Contributor.person_id, Contributor.part_id, Contributor.role_id])
    work = relationship('Work', secondary='part', uselist=True, viewonly=True)

    # publisher = relationship("Publisher", backref=backref('publisher_lookup',
    publisher = relationship("Publisher", backref=backref('edition_assoc4',
                                                          uselist=False), viewonly=True)
    pubseries = relationship("Pubseries", backref=backref('pubseries',
                                                          uselist=False), viewonly=True)
    owners = relationship("User", secondary='userbook')
    binding = relationship('BindingType', backref=backref(
        'edition_binding_assoc'), uselist=False, viewonly=True)
    format = relationship('Format', backref=backref(
        'edition_format_assoc'), uselist=False, viewonly=True)
    size = relationship('PublicationSize', backref=backref(
        'edition_size_assoc'), uselist=False, viewonly=True)
    images = relationship(
        'EditionImage', backref=backref('edition_image_assoc'), uselist=True, viewonly=True)


class EditionImage(Base):
    __tablename__ = 'editionimage'
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey(
        'edition.id'), nullable=False)
    image_src = Column(String(200))
    image_attr = Column(String(100))  # Source website name


class EditionLink(Base):
    __tablename__ = 'editionlink'
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class EditionPrice(Base):
    __tablename__ = 'editionprice'
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False)
    date = Column(Date, nullable=False)
    condition_id = Column(Integer, ForeignKey('bookcondition.id'))
    price = Column(Integer, nullable=False)


class Format(Base):
    __tablename__ = 'format'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))


class Genre(Base):
    __tablename__ = 'genre'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    abbr = Column(String(20), nullable=False, index=True)
    works = relationship('Work', secondary='workgenre',
                         backref=backref('workgenre_asooc'), viewonly=True)


class Issue(Base):
    __tablename__ = 'issue'
    id = Column(Integer, primary_key=True)
    magazine_id = Column(Integer, ForeignKey('magazine.id'), nullable=False)
    number = Column(Integer, index=True)
    number_extra = Column(String(20))
    count = Column(Integer)
    year = Column(Integer, index=True)
    image_src = Column(String(200))
    image_attr = Column(String(100))  # Source website name
    pages = Column(Integer)
    size_id = Column(Integer, ForeignKey('publicationsize.id'))
    link = Column(String(200))
    notes = Column(Text())
    title = Column(String(200))
    tags = relationship('Tag', secondary='issuetag',
                        uselist=True, viewonly=True)
    articles = relationship(
        'Article', secondary='issuecontent', uselist=True, viewonly=True)
    stories = relationship(
        'ShortStory', secondary='issuecontent', uselist=True, viewonly=True)
    editors = relationship(
        'Person', secondary='issueeditor', uselist=True, viewonly=True)
    size = relationship('PublicationSize', uselist=False, viewonly=True)
    magazine = relationship('Magazine', uselist=False, viewonly=True)


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


class Language(Base):
    __tablename__ = 'language'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, index=True)


class Log(Base):
    __tablename__ = 'Log'
    id = Column(Integer, primary_key=True)
    table_name = Column(String(30), index=True)
    field_name = Column(String(30))
    table_id = Column(Integer)
    action = Column(String(30))
    user_id = Column(Integer, ForeignKey('user.id'))
    old_value = Column(String(500))
    date = Column(DateTime, default=datetime.datetime.now())


class Magazine(Base):
    __tablename__ = 'magazine'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    publisher_id = Column(Integer, ForeignKey('publisher.id'))
    description = Column(Text())
    link = Column(String(200))
    issn = Column(String(30))
    tags = relationship('Tag', secondary='magazinetag', uselist=True)
    issues = relationship('Issue', backref=backref('magazine_issue'),
                          uselist=True, order_by='Issue.count')
    publisher = relationship('Publisher', uselist=False)
    # Type of magazine. 0 = fanzine, 1 = other.
    type = Column(Integer, nullable=False)


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
    edition_id = Column(Integer, ForeignKey(
        'edition.id'), nullable=True, index=True)
    work_id = Column(Integer, ForeignKey('work.id'), nullable=True, index=True)
    shortstory_id = Column(Integer, ForeignKey(
        'shortstory.id'), nullable=True, index=True)
    # Title is repeated from edition in the simple case but required for
    # e.g. collections.
    title = Column(String(500))
    authors = relationship('Person', secondary='contributor', foreign_keys=[Contributor.part_id, Contributor.person_id, Contributor.role_id],
                           uselist=True, viewonly=True)
    # translators = relationship(
    #     'Person', secondary='translator', uselist=True, viewonly=True)
    edition = relationship('Edition', backref=backref(
        'edition_assoc'), viewonly=True)
    work = relationship('Work', backref=backref('work_assoc'), viewonly=True)
    shortstory = relationship('ShortStory',
                              backref=backref('shortstory_assoc'), viewonly=True)


class Person(Base):
    __tablename__ = 'person'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, index=True, unique=True)
    alt_name = Column(String(250), index=True)
    fullname = Column(String(250))
    other_names = Column(Text())
    first_name = Column(String(100))
    last_name = Column(String(150))
    image_src = Column(String(100))
    image_attr = Column(String(100))  # Source website name
    dob = Column(Integer)
    dod = Column(Integer)
    bio = Column(Text())  # Biographgy
    bio_src = Column(String(100))  # Source website name
    nationality_id = Column(Integer, ForeignKey('country.id'), index=True)
    imported_string = Column(String(500))
    real_names = relationship('Person',
                              primaryjoin=id == Alias.alias,
                              secondary='alias',
                              secondaryjoin=id == Alias.realname,
                              uselist=True, viewonly=True)
    aliases = relationship("Person",
                           primaryjoin=id == Alias.realname,
                           secondary='alias',
                           secondaryjoin=id == Alias.alias,
                           uselist=True, viewonly=True)
    works = relationship("Work",
                         secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                         primaryjoin='and_(Person.id == Contributor.person_id,\
                            Contributor.part_id == Part.id,\
                            Contributor.role_id == 0,\
                            Part.work_id == Work.id,\
                            Part.shortstory_id == None)',
                         order_by='Work.title',
                         uselist=True, viewonly=True)
    stories = relationship("ShortStory",
                           secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                           primaryjoin='and_(Person.id == Contributor.person_id,\
                Contributor.part_id == Part.id, Contributor.role_id == 0,\
                Part.shortstory_id == ShortStory.id)',
                           uselist=True, viewonly=True)
    # Author.part_id == Part.id, Part.work_id == Work.id,\
    #edits = relationship("Edition", secondary='editor', viewonly=True)
    edits = relationship("Edition",
                         secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                         primaryjoin='and_(Person.id == Contributor.person_id,\
                              Contributor.part_id == Part.id,\
                              Contributor.role_id == 2,\
                              Part.edition_id == Edition.id,\
                              Part.shortstory_id == None)',
                         order_by='Edition.title',
                         uselist=True, viewonly=True)
    # foreign_keys=[Contributor.person_id, Contributor.part_id, Contributor.role_id])
    translations = relationship("Edition",
                                secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                                primaryjoin='and_(Person.id == Contributor.person_id,\
                                    Contributor.part_id == Part.id,\
                                    Contributor.role_id == 1,\
                                    Part.edition_id == Edition.id,\
                                    Part.shortstory_id == None)',
                                order_by='Edition.title',
                                uselist=True, viewonly=True)
    # foreign_keys=[Contributor.person_id, Contributor.part_id, Contributor.role_id])
    chief_editor = relationship(
        'Issue', secondary='issueeditor', uselist=True, viewonly=True)
    articles = relationship('Article', secondary='articleauthor',
                            uselist=True, viewonly=True)
    magazine_stories = relationship('ShortStory',
                                    secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                                    primaryjoin='and_(Person.id == Contributor.person_id, Contributor.role_id == 0, \
                         IssueContent.shortstory_id == Part.shortstory_id)',
                                    uselist=True, viewonly=True)
    translated_stories = relationship('ShortStory',
                                      secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                                      primaryjoin="and_(Person.id == Contributor.person_id, \
                                      Contributor.role_id == 1, Part.shortstory_id is not None)",
                                      uselist=True, viewonly=True)
    appears_in = relationship('Article', secondary='articleperson',
                              uselist=True, viewonly=True)
    tags = relationship('Tag', secondary='persontag',
                        uselist=True, viewonly=True)
    languages = relationship(
        'Language', secondary='personlanguage', uselist=True, viewonly=True)
    personal_awards = relationship(
        'Award', secondary='awarded', uselist=True, viewonly=True)
    nationality = relationship(
        'Country', foreign_keys=[nationality_id], uselist=False, viewonly=True)
    # birtcountry = relationship(
    #     'Country', foreign_keys=[birthcountry_id], uselist=False)
    # deatchcountry = relationship(
    #     'Country', foreign_keys=[deathcountry_id], uselist=False)


class PersonLanguage(Base):
    __tablename__ = 'personlanguage'
    person_id = Column(Integer, ForeignKey('person.id'),
                       nullable=False, primary_key=True)
    language_id = Column(Integer, ForeignKey('language.id'),
                         nullable=False, primary_key=True)


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
    comment = Column(Text())
    table_name = Column(String(50))
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
    name = Column(String(500), nullable=False, unique=True, index=True)
    fullname = Column(String(500), nullable=False, unique=True)
    description = Column(Text())
    image_src = Column(String(100))
    image_attr = Column(String(100))  # Source website name
    editions = relationship("Edition", backref=backref(
        "edition4_assoc"), order_by="Edition.pubyear", viewonly=True)
    series = relationship('Pubseries', viewonly=True)


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
    image_src = Column(String(100))
    image_attr = Column(String(100))  # Source website name
    publisher = relationship("Publisher", backref=backref('publisher',
                                                          uselist=False), viewonly=True)

    # editions = relationship("Edition", backref=backref('edition'), uselist=True,
    #                        order_by='Edition.pubseriesnum')
    editions = relationship("Edition", primaryjoin="Pubseries.id == Edition.pubseries_id", uselist=True,
                            order_by='Edition.pubseriesnum', viewonly=True)


class PubseriesLink(Base):
    __tablename__ = 'pubserieslink'
    id = Column(Integer, primary_key=True)
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class ShortStory(Base):
    __tablename__ = 'shortstory'
    id = Column(Integer, primary_key=True)
    title = Column(String(700), nullable=False, index=True)
    orig_title = Column(String(700))
    language = Column(Integer, ForeignKey('language.id'))
    pubyear = Column(Integer, index=True)
    story_type = Column(Integer, ForeignKey('storytype.id'))
    parts = relationship('Part', backref=backref(
        'part_assoc'), uselist=True, viewonly=True)
    genres = relationship('Genre', secondary='storygenre',
                          uselist=True, viewonly=True)
    works = relationship('Work', secondary='part',
                         uselist=True, viewonly=True)
    editions = relationship('Edition', secondary='part',
                            uselist=True, viewonly=True)
    issues = relationship('Issue', secondary='issuecontent',
                          uselist=True, viewonly=True)
    tags = relationship('Tag', secondary='storytag',
                        uselist=True, viewonly=True)
    authors = relationship("Person",
                           secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                           primaryjoin='and_(Person.id == Contributor.person_id,\
                Contributor.part_id == Part.id, Contributor.role_id == 0, Part.work_id == ShortStory.id)',
                           uselist=True, order_by='Person.alt_name', viewonly=True,
                           foreign_keys=[Contributor.part_id, Contributor.person_id, Contributor.role_id])

    _author_str: str = ''

    @hybrid_property
    def author_str(self) -> str:
        if self._author_str != '':
            return self._author_str
        if len(self.authors) > 0:
            self._author_str = ' & '.join([x.name for x in self.authors])
        return self._author_str


class StoryGenre(Base):
    __tablename__ = 'storygenre'
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'),
                           nullable=False, primary_key=True)
    genre_id = Column(Integer, ForeignKey('genre.id'),
                      nullable=False, primary_key=True)
    stories = relationship('ShortStory', backref=backref(
        'story_assoc'), viewonly=True)
    genres = relationship('Genre', backref=backref(
        'genre_assoc'), viewonly=True)


class StoryTag(Base):
    __tablename__ = 'storytag'
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'),
                           nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
                    primary_key=True)


class StoryType(Base):
    __tablename__ = 'storytype'
    id = Column(Integer, primary_key=True)
    name = Column(String(30))


class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    works = relationship('Work', secondary='worktag',
                         uselist=True, viewonly=True)
    articles = relationship(
        'Article', secondary='articletag', uselist=True, viewonly=True)
    stories = relationship(
        'ShortStory', secondary='storytag', uselist=True, viewonly=True)
    magazines = relationship(
        'Magazine', secondary='magazinetag', uselist=True, viewonly=True)
    people = relationship('Person', secondary='persontag',
                          uselist=True, viewonly=True)


class User(UserMixin, Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True, unique=True)
    password_hash = Column(String(128))
    is_admin = Column(Boolean, default=False)
    language = Column(Integer, ForeignKey('language.id'))
    books = relationship("Edition", secondary="userbook", viewonly=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return '<User {}'.format(self.name)


class UserBook(Base):
    __tablename__ = 'userbook'
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False,
                        primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
                     primary_key=True)
    condition = Column(Integer, ForeignKey('bookcondition.id'))
    description = Column(String(100))
    price = Column(Integer)
    book = relationship("Edition", backref=backref(
        "edition3_assoc"), viewonly=True)
    user = relationship("User", backref=backref("user2_assoc"), viewonly=True)


class UserBookseries(Base):
    __tablename__ = 'userbookseries'
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
                     primary_key=True)
    series_id = Column(Integer, ForeignKey('bookseries.id'), nullable=False,
                       primary_key=True)
    series = relationship("Bookseries", backref=backref(
        "bookseries_assoc"), viewonly=True)
    user = relationship("User", backref=backref("user4_asocc"), viewonly=True)


class UserPubseries(Base):
    __tablename__ = 'userpubseries'
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
                     primary_key=True)
    series_id = Column(Integer, ForeignKey('pubseries.id'), nullable=False,
                       primary_key=True)
    series = relationship("Pubseries", backref=backref(
        "pubseries_assoc"), viewonly=True)
    user = relationship("User", backref=backref("user3_asocc"), viewonly=True)
    publisher = relationship("Publisher", secondary="pubseries", viewonly=True)


class Work(Base):
    ''' Work is a more abstract idea than edition. Work is
        basically the representation of the original work of which         editions are printed. Every work must have at least one        edition but sometimes there is no work, this is the case
       with collections. Not all parts have necessarily been
        published in a book.
    '''
    __tablename__ = 'work'
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    subtitle = Column(String(500))
    orig_title = Column(String(500), index=True)
    pubyear = Column(Integer, index=True)
    language = Column(Integer, ForeignKey('language.id'), index=True)
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'))
    bookseriesnum = Column(String(20))
    bookseriesorder = Column(Integer)
    type = Column(Integer, ForeignKey('worktype.id'), index=True)
    misc = Column(String(500))
    description = Column(Text())
    descr_attr = Column(String(200))
    imported_string = Column(String(500))
    authors = relationship("Person",
                           secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                           primaryjoin='and_(Person.id == Contributor.person_id,\
                Contributor.part_id == Part.id, Contributor.role_id == 0, Part.work_id == Work.id,\
                Part.shortstory_id == None)',
                           uselist=True,
                           order_by='Person.alt_name', viewonly=True,
                           foreign_keys=[Contributor.part_id, Contributor.person_id, Contributor.role_id])
    translators = relationship("Person",
                               secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
                               primaryjoin='and_(Person.id == Contributor.person_id,\
                                   Contributor.role_id == 1,\
                                Contributor.part_id == Part.id, Part.work_id == Work.id)',
                               uselist=True, viewonly=True,
                               foreign_keys=[Contributor.person_id, Contributor.part_id, Contributor.role_id])
    parts = relationship('Part', backref=backref(
        'part', uselist=True), viewonly=True)
    bookseries = relationship("Bookseries", backref=backref('bookseries'),
                              uselist=False, viewonly=True)
    editions = relationship('Edition', primaryjoin='and_(Part.work_id == Work.id, Part.edition_id == Edition.id, Part.shortstory_id == None)',
                            secondary='part', uselist=True,
                            lazy='dynamic',
                            order_by='Edition.pubyear, Edition.version, Edition.editionnum',
                            viewonly=True)
    genres = relationship("Genre", secondary='workgenre',
                          uselist=True, viewonly=True)
    tags = relationship('Tag', secondary='worktag',
                        uselist=True, viewonly=True)
    language_name = relationship(
        'Language', backref=backref('language'), uselist=False)
    stories = relationship('ShortStory', secondary='part', uselist=True,
                           viewonly=True)

    _author_str: str = ''

    @hybrid_property
    def author_str(self) -> Any:
        if self._author_str != '':
            return self._author_str
        if len(self.authors) > 0:
            self._author_str = ' & '.join([x.name for x in self.authors])
        else:
            # Collection of several authors, use editors instead
            self._author_str = ' & '.join(
                [x.name for x in self.editions[0].editors]) + ' (toim.)'
        return self._author_str


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


class WorkReview(Base):
    # Links Works with articles that contain a review.
    __tablename__ = 'workreview'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
                     primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'), nullable=False,
                        primary_key=True)


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
def load_user(id: Any) -> Any:
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session.query(User).get(int(id))


engine = create_engine(db_url)  # , echo=True)

Base.metadata.create_all(engine)
