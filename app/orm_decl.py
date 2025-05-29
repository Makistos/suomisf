# pylint: disable=too-many-lines
""" Database models"""
from typing import Any, List, Union, Dict
import datetime
import html
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin  # type: ignore
from sqlalchemy import (Column, ForeignKey, Integer,
                        String, Boolean, Date, DateTime, Text, Table)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine
import jwt
from app import app, db_url, login, jwt_secret_key
# from app.route_helpers import new_session
# from flask_sqlalchemy.record_queries import get_recorded_queries

Base = declarative_base()

# basedir = os.path.abspath(os.path.dirname(__file__))
# load_dotenv(os.path.join(basedir, '.env'))

# db_url = app.config['SQLALCHEMY_DATABASE_URI']


# @app.after_request
# def after_request(response):
#     for query in get_recorded_queries():
#         app.logger.debug(
#             "SQL QUERY: %s\nParameters: %s\nDuration: %fs\nContext: %s\n\n" %
#             (query.statement,
#              query.parameters,
#              query.duration,
#              query.context))
#     return response


def generate_jwt_token(content: Dict[str, int]) -> List[str]:
    """
    Generates a JWT token based on the given content.

    Args:
        content (Dict[str, int]): A dictionary containing the content to be
        encoded.

    Returns:
        List[str]: A list of strings representing the encoded JWT token.
    """
    encoded_content = jwt.encode(content, jwt_secret_key, algorithm="HS256")
    token = str(encoded_content).split("'")
    return token


def decode_jwt_token(auth_token):
    """
    Decodes a JWT token and returns the subject (sub) claim.

    Parameters:
        auth_token (str): The JWT token to decode.

    Returns:
        str: The subject (sub) claim of the JWT token, or an empty string if
        the token is invalid or expired.
    """
    try:
        payload = jwt.decode(auth_token, jwt_secret_key, algorithms="HS256")
        return payload['sub']
    except jwt.ExpiredSignatureError:
        app.logger.warning('JWT token expired.')
        return ""
    except jwt.InvalidTokenError:
        app.logger.warning('Invalid JWT token.')


def edition_popup(edition_id: int, edition: Any, title: str, link: str) -> str:
    """
    Generate a popup HTML element for an edition.

    Args:
        id (int): The ID of the edition.
        edition (Any): The edition object.
        title (str): The title of the edition.
        link (str): The link for the edition.

    Returns:
        str: The generated HTML element for the edition popup.
    """
    if edition.images:
        img_src = edition.images[0].image_src
    else:
        img_src = '/static/icons/blue-book-icon-small.png'

    # pylint: disable=consider-using-f-string
    retval = r'''<a href="/edition/%d"
    data-toggle="popover"
    title="%s"
    data-content='
        <div class="container" style="text-align: left;">
            <div class="row">
                <div class="col-4">
                <img src="%s" width="100px">
                </div>
                <div class="col-8">
                %s
                </div>
            </div>
        </div>
    ' >%s</a>''' \
            % (edition_id, title, img_src, edition.long_info(), link)
    return retval


# class AuthorComparator(Comparator):
#     """ AuthorComparator class. """
#     def __eq__(self, other):
#         """
#         Equality comparison method for the class.

#         Args:
#             other: The object to compare with.

#         Returns:
#             None
#         """
#         return super().__eq__(other)

#     def __ne__(self, other):
#         pass

#     def like(self, other, escape=None):
#         return super().like(other, escape)

#     def ilike(self, other, escape=None):
#         return super().ilike(other, escape)

#     def startswith(self, other: str, **kwargs):
#         return super().startswith(other, **kwargs)

#     def endswith(self, other: str, **kwargs):
#         return super().endswith(other, **kwargs)


class Alias(Base):
    """ Alias table. """
    __tablename__ = 'alias'
    alias = Column(Integer, ForeignKey('person.id'), nullable=False,
                   primary_key=True)
    realname = Column(Integer, ForeignKey('person.id'), nullable=False,
                      primary_key=True)


class Article(Base):
    """ Article table. """
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
        """
        Returns a string representation of the author of the current object.

        :return: A string containing the names of the authors separated by
                 an ' & '.
        :rtype: str
        """
        if self._author_str != '':
            return self._author_str
        if len(self.author_rel) > 0:
            self._author_str = ' & '.join([x.name for x in self.author_rel])
        return self._author_str

    @property
    def name(self) -> str:
        """
        Get the name of the object.

        Returns:
            str: The name of the object.
        """
        return self.title


class ArticleAuthor(Base):
    """ Links articles to authors. """
    __tablename__ = 'articleauthor'
    article_id = Column(Integer, ForeignKey('article.id'), nullable=False,
                        primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
                       primary_key=True)


class ArticleLink(Base):
    """ Article links table. """
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
    """ Links articles to tags. """
    __tablename__ = 'articletag'
    article_id = Column(Integer, ForeignKey('article.id'),
                        nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
                    primary_key=True)


class Award(Base):
    """ Award table. """
    __tablename__ = 'award'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text())
    # If this is a domestic award (these are separated in the UI):
    domestic = Column(Boolean, default=False)
    categories = relationship(
        'AwardCategory', secondary='awardcategories', viewonly=True)
    winners = relationship(
        'Awarded', viewonly=True)


class AwardCategory(Base):
    """ Award category table. """
    __tablename__ = 'awardcategory'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    # 0 = personal, 1 = novel, 2 = short story
    type = Column(Integer, nullable=False)


class AwardCategories(Base):
    """ Links awards to categories. """
    __tablename__ = 'awardcategories'
    award_id = Column(Integer, ForeignKey('award.id'),
                      primary_key=True, nullable=False)
    category_id = Column(Integer, ForeignKey('awardcategory.id'),
                         primary_key=True, nullable=False)


class Awarded(Base):
    """ Links awards to person, work or story and category as well as year. """
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
    """ Binding type table. """
    __tablename__ = 'bindingtype'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class BookCondition(Base):
    """ Book condition table. """
    __tablename__ = 'bookcondition'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    # Used to sort conditions from best to worst
    value = Column(Integer, nullable=False)


class Bookseries(Base):
    """ Book series table. """
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
    """ Book series link table. """
    __tablename__ = 'bookserieslink'
    id = Column(Integer, primary_key=True)
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'),
                           nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class Contributor(Base):
    """ Contributor table. """
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
    role = relationship('ContributorRole', viewonly=True)
    real_person = relationship('Person', foreign_keys=[real_person_id])


class ContributorRole(Base):
    """ Contributor role table. """
    __tablename__ = 'contributorrole'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class Country(Base):
    """ Country table. """
    __tablename__ = 'country'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, index=True)


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
    size = Column(Integer)  # Height in centimeters
    # size_id = Column(Integer, ForeignKey('publicationsize.id'))
    dustcover = Column(Integer, default=0)  # 1 = not known, 2 = no, 3 = yes
    coverimage = Column(Integer, default=0)  # 1 = not known, 2 = no, 3 = yes
    misc = Column(String(500))
    imported_string = Column(String(500))
    verified = Column(Boolean, default=False)
    parts = relationship('Part', backref=backref('parts_lookup'),
                         uselist=True, viewonly=True)
    # editors = relationship('Person', secondary='editor',
    #                        uselist=True, viewonly=True)
    editors = relationship(
        "Person",
        secondary='join(Part, Contributor, Part.id == \
         Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
         Contributor.part_id == Part.id, Contributor.role_id == 3, \
         Part.edition_id == Edition.id)',
        uselist=True, viewonly=True,
        foreign_keys=[Contributor.person_id,
                      Contributor.part_id,
                      Contributor.role_id])
    translators = relationship(
        "Person",
        secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
         Contributor.part_id == Part.id, Contributor.role_id == 2, \
         Part.edition_id == Edition.id)',
        uselist=True, viewonly=True,
        foreign_keys=[Contributor.person_id,
                      Contributor.part_id,
                      Contributor.role_id])
    work = relationship('Work', secondary='part', uselist=True, viewonly=True)
    contributions = relationship(
        'Contributor',
        secondary='part',
        primaryjoin='and_(Part.edition_id == Edition.id, \
            Part.shortstory_id == None, Contributor.role_id != 1, \
            Contributor.role_id != 3)',
        uselist=True, viewonly=True)

    # publisher = relationship("Publisher", backref=backref('publisher_lookup',
    publisher = relationship("Publisher",
                             backref=backref('edition_assoc4'),
                             uselist=False,
                             viewonly=True)
    pubseries = relationship("Pubseries",
                             backref=backref('pubseries'),
                             uselist=False,
                             viewonly=True)
    owners = relationship("User", secondary='userbook')
    binding = relationship('BindingType',
                           backref=backref('edition_binding_assoc'),
                           uselist=False,
                           viewonly=True)
    format = relationship('Format',
                          backref=backref('edition_format_assoc'),
                          uselist=False,
                          viewonly=True)
    images = relationship(
        'EditionImage',
        backref=backref('edition_image_assoc'),
        uselist=True,
        viewonly=True)
    owners = relationship('User',
                          primaryjoin='and_(UserBook.condition_id > 0, \
                          UserBook.condition_id < 6, \
                          UserBook.edition_id == Edition.id)',
                          secondary='userbook',
                          viewonly=True)
    # owners = relationship('User', secondary='userbook', viewonly=True)
    wishlisted = relationship('User',
                              primaryjoin='and_( \
                              UserBook.edition_id == Edition.id, \
                              UserBook.condition_id == 6)',
                              secondary='userbook',
                              viewonly=True)
    # viewonly=True)

    @property
    def name(self) -> str:
        """
        Get the name of the object.

        Returns:
            str: The name of the object.
        """
        return self.title

    def long_info(self) -> str:
        """
        Returns a string containing information about the book. The string
        includes the publisher name, publication year, publication series,
        publication series number, number of pages, size, ISBN, binding, and
        whether the book has a dust jacket or a cover image.

        :return: A string containing the book information.
        :rtype: str
        """
        retval: str = ''
        # if self.title != self.work[0].title:
        #    retval += '<b>' + html.escape(self.title) + '</b><br>'
        #    if self.subtitle:
        #        retval += '<i>' + html.escape(self.subtitle) + '</i><br>'
        if self.publisher:
            retval += html.escape(self.publisher.name)
        if self.pubyear:
            retval += ' ' + str(self.pubyear)
        if self.publisher_id or self.pubyear:
            retval += '.<br>'
        if self.pubseries:
            retval += html.escape(self.pubseries.name)
            if self.pubseriesnum:
                retval += ' ' + str(self.pubseriesnum)
            retval += '.<br>'
        if self.pages:
            retval += str(self.pages) + ' sivua. '
        if self.size:
            retval += str(self.size) + 'cm.'
        if self.pages or self.size:
            retval += '<br>'
        if self.isbn:
            retval += 'ISBN ' + self.isbn
        if self.binding_id:
            if self.binding_id > 1:
                if self.isbn:
                    retval += ' '
                if self.binding:
                    retval += str(self.binding.name)
        if self.isbn or self.binding_id:
            if self.binding_id:
                if self.binding_id > 1 or self.isbn:
                    retval += '.<br>'
        if self.dustcover == 3:
            retval += 'Kansipaperi.<br>'
        if self.coverimage == 3:
            retval += 'Ylivetokannet.<br>'
        return retval

    def version_str(self) -> str:
        """
        Returns a string representation of the version number and edition
        number of the object.

        :return: A string representing the version and edition number of the
                 object.
        :rtype: str
        """
        retval: str = ''
        if not self.version:
            version = 1
        else:
            version = self.version
        if version > 1:
            retval += f'{self.version}. laitos'
            if not self.editionnum:
                retval += ' ?. painos'
            elif self.editionnum > 1:
                retval += f' {self.editionnum}. painos'
        else:
            if not self.editionnum:
                retval += '?. painos'
            else:
                retval += f'{self.editionnum}. painos'
        retval += '</a>'
        return retval

    def __str__(self) -> str:
        """
        Returns a string representation of the object.

        :return: A string representation of the object.
        :rtype: str
        """
        retval: str = ''
        work = self.work[0]

        retval = edition_popup(self.id, self, html.escape(self.title) +
                               ': ' + self.version_str(), self.version_str())
        retval += ': '
        if self.title != work.title:
            retval += f'<b>{self.title}</b>. '

        if self.pubseries:
            retval += f'{self.pubseries.name}'
            if self.pubseriesnum:
                retval += f' {self.pubseriesnum}'
            retval += '. '
        if self.translators:
            if self.translators != work.editions[0].translators:
                retval += 'Suom '
                retval += ' & '.join(
                    [x.alt_name for x in self.translators if x.alt_name])
                retval += '. '
        if self.publisher:
            retval += f'{self.publisher.name}'
        if self.pubyear:
            retval += f' {self.pubyear}'
        if self.publisher or self.pubyear:
            retval += '.'
        retval += '<br>'
        return retval


class EditionImage(Base):
    """ Edition image table. """
    __tablename__ = 'editionimage'
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey(
        'edition.id'), nullable=False)
    image_src = Column(String(200), nullable=False)
    image_attr = Column(String(100))  # Source website name
    edition = relationship('Edition', uselist=False, viewonly=True)


class EditionLink(Base):
    """ Edition link table. """
    __tablename__ = 'editionlink'
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class EditionPrice(Base):
    """ Edition price table. """
    __tablename__ = 'editionprice'
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False)
    date = Column(Date, nullable=False)
    condition_id = Column(Integer, ForeignKey('bookcondition.id'))
    price = Column(Integer, nullable=False)


class Format(Base):
    """ Format table, holds edition format options. """
    __tablename__ = 'format'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))


class Genre(Base):
    """ Genre table """
    __tablename__ = 'genre'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    abbr = Column(String(20), nullable=False, index=True)
    works = relationship('Work', secondary='workgenre',
                         backref=backref('workgenre_asooc'), viewonly=True)


class Issue(Base):
    """ Issue table """
    __tablename__ = 'issue'
    id = Column(Integer, primary_key=True)
    magazine_id = Column(Integer, ForeignKey('magazine.id'), nullable=False)
    number = Column(Integer, index=True)
    number_extra = Column(String(20))
    count = Column(Integer)
    year = Column(Integer, index=True)
    cover_number = Column(String(100))
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

    @hybrid_property
    def issue_order(self, other):
        """
        Calculate the order of two issues based on their count, year, number,
        and number_extra.

        Parameters:
            self (Issue): The first issue.
            other (Issue): The second issue.

        Returns:
            int: The difference between the count of the two issues, if both
                 are not None.
                If the count is None for either issue, the difference between
                the year of the two issues.
                If the year is the same for both issues, the difference between
                the number of the two issues.
                If the number is the same for both issues, the difference
                between the number_extra of the two issues.
        """
        if self.count is not None and other.count is not None:
            return self.count - other.count
        if self.year != other.year:
            return self.year - other.year
        if self.number != other.number:
            return self.number - other.number
        return self.number_extra - other.number_extra

    @property
    def name(self) -> str:
        """
        Returns the name of the object.

        :return: A string representing the name of the object.
        :rtype: str
        """
        retval: str = self.magazine.name
        if self.number:
            retval += ' ' + str(self.number)
            if self.number_extra:
                retval += self.number_extra
        elif self.count:
            retval += ' ' + str(self.count)

        return retval


class IssueContent(Base):
    """ Issue content table. """
    __tablename__ = 'issuecontent'
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('issue.id'), nullable=False)
    article_id = Column(Integer, ForeignKey('article.id'))
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'))


class IssueEditor(Base):
    """ Issue editors table. """
    __tablename__ = 'issueeditor'
    issue_id = Column(Integer, ForeignKey('issue.id'),
                      nullable=False, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'),
                       nullable=False, primary_key=True)


class IssueTag(Base):
    """ Issue tags table. """
    __tablename__ = 'issuetag'
    issue_id = Column(Integer, ForeignKey('issue.id'),
                      nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
                    primary_key=True)


class Language(Base):
    """ Language table. """
    __tablename__ = 'language'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, index=True)


class Log(Base):
    """ Log table. """
    __tablename__ = 'Log'
    id = Column(Integer, primary_key=True)
    table_name = Column(String(30), index=True)
    field_name = Column(String(30))
    table_id = Column(Integer)
    object_name = Column(String(200))
    action = Column(String(30))
    user_id = Column(Integer, ForeignKey('user.id'))
    old_value = Column(String(500))
    date = Column(DateTime, default=datetime.datetime.now())
    user = relationship('User', uselist=False)


class Magazine(Base):
    """ Magazines table. """
    __tablename__ = 'magazine'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    publisher_id = Column(Integer, ForeignKey('publisher.id'))
    description = Column(Text())
    link = Column(String(200))
    issn = Column(String(30))
    type_id = Column(Integer, ForeignKey('magazinetype.id'))
    tags = relationship('Tag', secondary='magazinetag', uselist=True)
    issues = relationship(
        'Issue',
        backref=backref('magazine_issue'),
        uselist=True, order_by='Issue.year, Issue.count, Issue.number, \
        Issue.number_extra')
    publisher = relationship('Publisher', uselist=False)
    # Type of magazine. 0 = fanzine, 1 = other.
    type = relationship('MagazineType', uselist=False, viewonly=True)


class MagazineTag(Base):
    """ Tags for magazines. """
    __tablename__ = 'magazinetag'
    magazine_id = Column(Integer, ForeignKey('magazine.id'),
                         nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
                    primary_key=True)


class MagazineType(Base):
    """ Magazine type table. """
    __tablename__ = 'magazinetype'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)


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
    # For short stories, order number in a collection
    order_num = Column(Integer)
    # Title is repeated from edition in the simple case but required for
    # e.g. collections.
    title = Column(String(500))
    authors = relationship(
        'Person',
        secondary='contributor',
        foreign_keys=[Contributor.part_id,
                      Contributor.person_id,
                      Contributor.role_id],
        uselist=True, viewonly=True)
    # translators = relationship(
    #     'Person', secondary='translator', uselist=True, viewonly=True)
    edition = relationship('Edition', backref=backref(
        'edition_assoc'), viewonly=True)
    work = relationship('Work', backref=backref('work_assoc'), viewonly=True)
    shortstory = relationship('ShortStory',
                              backref=backref('shortstory_assoc'),
                              viewonly=True)


class Person(Base):
    """ Person table. """
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
    links = relationship("PersonLink", uselist=True, viewonly=True)
    works = relationship("Work",
                         secondary='join(Part, Contributor, \
                            Part.id == Contributor.part_id)',
                         primaryjoin='and_(Person.id == Contributor.person_id,\
                            Contributor.part_id == Part.id,\
                            Contributor.role_id == 1,\
                            Part.work_id == Work.id,\
                            Part.shortstory_id == None)',
                         order_by='Work.title',
                         uselist=True, viewonly=True)
    work_contributions = relationship(
        "Work",
        secondary='join(Part, Contributor, \
                   Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
                     Contributor.part_id == Part.id,\
                     Part.work_id == Work.id,\
                     Part.shortstory_id == None)',
        order_by='Work.title',
        uselist=True, viewonly=True)
    # all_works = relationship("Work",
    #                      secondary='join(Part, Contributor, \
    #                       Part.id == Contributor.part_id)',
    #                      primaryjoin='and_\
    #                         (or_(Person.id == Contributor.person_id,\
    #                             Contributor.person_id.in_(Person.id)\
    #                         Contributor.part_id == Part.id,\
    #                         Contributor.role_id == 1,\
    #                         Part.work_id == Work.id,\
    #                         Part.shortstory_id == None)',
    #                      order_by='Work.title',
    #                      uselist=True, viewonly=True)
    # works = relationship(
    #   "Work",
    #   primaryjoin='and_(Person.id == Contributor.person_id,\
    #                Contributor.part_id == Part.id,\
    #                Contributor.role_id == 1,\
    #                Part.work_id == Work.id,\
    #                Part.shortstory_id == None)',
    #   order_by='Work.title',
    #   uselist=True, viewonly=True)
    stories = relationship(
        "ShortStory",
        # secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        # primaryjoin='and_(Person.id == Contributor.person_id,\
        #              Contributor.part_id == Part.id,\
        #              Part.shortstory_id == ShortStory.id)',
        secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id)',
        secondaryjoin='Part.shortstory_id == ShortStory.id',
        uselist=True, viewonly=True)
    # Author.part_id == Part.id, Part.work_id == Work.id,\
    # edits = relationship("Edition", secondary='editor', viewonly=True)
    edits = relationship(
        "Edition",
        secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
                     Contributor.part_id == Part.id,\
                     Contributor.role_id == 3,\
                     Part.edition_id == Edition.id,\
                     Part.shortstory_id == None)',
        order_by='Edition.title',
        uselist=True, viewonly=True)
    translations = relationship(
        "Edition",
        secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
                     Contributor.part_id == Part.id,\
                     Contributor.role_id == 2,\
                     Part.edition_id == Edition.id,\
                     Part.shortstory_id == None)',
        order_by='Edition.title',
        uselist=True, viewonly=True)
    editions = relationship(
        "Edition",
        secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
                     Contributor.part_id == Part.id,\
                     Part.edition_id == Edition.id,\
                     Part.shortstory_id == None)',
        order_by='Edition.title',
        uselist=True, viewonly=True)
    chief_editor = relationship(
        'Issue', secondary='issueeditor', uselist=True, viewonly=True)
    # articles = relationship('Article', secondary='articleauthor',
    #                         uselist=True, viewonly=True)
    # magazine_stories = relationship(
    #     'ShortStory',
    #     secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
    #     primaryjoin='and_(Person.id == Contributor.person_id, \
    #                  Contributor.role_id == 1, \
    #                  IssueContent.shortstory_id == Part.shortstory_id)',
    #     uselist=True, viewonly=True)
    # translated_stories = relationship(
    #     'ShortStory',
    #     secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
    #     primaryjoin="and_(Person.id == Contributor.person_id, \
    #     Contributor.role_id == 2, Part.shortstory_id is not None)",
    #     uselist=True, viewonly=True)
    # appears_in = relationship('Article', secondary='articleperson',
    #                           uselist=True, viewonly=True)
    tags = relationship('Tag', secondary='persontag',
                        uselist=True, viewonly=True)
    languages = relationship(
        'Language', secondary='personlanguage', uselist=True, viewonly=True)
    personal_awards = relationship(
        'Awarded', uselist=True, viewonly=True, order_by='Awarded.year')
    nationality = relationship(
        'Country', foreign_keys=[nationality_id], uselist=False, viewonly=True)
    roles = relationship(
        'ContributorRole',
        secondary='join(Contributor, ContributorRole, \
                   Contributor.role_id == ContributorRole.id)',
        primaryjoin="and_(Person.id == Contributor.person_id)",
        uselist=True, viewonly=True,
        foreign_keys=[Contributor.person_id, Contributor.role_id])
    wrks = relationship('Work', secondary=lambda: personworks_table)
    awarded = relationship('Awarded', uselist=True, viewonly=True)
    works2 = association_proxy('wrks', 'work')

    @hybrid_property
    def workcount(self) -> int:
        """
        Calculate the number of works associated with this object.

        Returns:
            int: The number of works associated with this object.
        """
        return len([x for x in self.works])

    @hybrid_property
    def storycount(self) -> int:
        """
        Returns the number of stories associated with the current instance.

        :return: An integer representing the number of stories.
        :rtype: int
        """
        return len(self.stories)

    @hybrid_property
    def nationalityname(self) -> Union[str, None]:
        """
        Returns the name of the nationality of the current object.

        :return: A string representing the name of the nationality or None if
                 the nationality is not set.
        :rtype: Union[str, None]
        """
        if self.nationality:
            return self.nationality.name
        else:
            return None

    def __str__(self) -> str:
        return self.name


class PersonLanguage(Base):
    """ Person languages. """
    __tablename__ = 'personlanguage'
    person_id = Column(Integer, ForeignKey('person.id'),
                       nullable=False, primary_key=True)
    language_id = Column(Integer, ForeignKey('language.id'),
                         nullable=False, primary_key=True)


class PersonLink(Base):
    """ Person links. """
    __tablename__ = 'personlink'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class PersonTag(Base):
    """ Person tags. """
    __tablename__ = 'persontag'
    person_id = Column(Integer, ForeignKey('person.id'),
                       nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
                    primary_key=True)


class Problem(Base):
    """ Problem table. """
    __tablename__ = 'problems'
    id = Column(Integer, primary_key=True)
    status = Column(String(20))
    comment = Column(Text())
    table_name = Column(String(50))
    table_id = Column(Integer)


class PublicationSize(Base):
    """ Publication size. """
    __tablename__ = 'publicationsize'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    mm_width = Column(Integer)
    mm_height = Column(Integer)


class Publisher(Base):
    """ Publisher table. """
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
    links = relationship("PublisherLink", uselist=True, viewonly=True)
    magazines = relationship("Magazine", uselist=True, viewonly=True)

    def __str__(self) -> str:
        return self.name


class PublisherLink(Base):
    """ Publisher links. """
    __tablename__ = 'publisherlink'
    id = Column(Integer, primary_key=True)
    publisher_id = Column(Integer, ForeignKey('publisher.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class Pubseries(Base):
    """ Pubseries table. """
    __tablename__ = 'pubseries'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    publisher_id = Column(Integer, ForeignKey('publisher.id'), nullable=False)
    important = Column(Boolean, default=False)
    image_src = Column(String(100))
    image_attr = Column(String(100))  # Source website name
    publisher = relationship(
        "Publisher",
        backref=backref('publisher'),
        uselist=False, viewonly=True)
    editions = relationship(
        "Edition",
        primaryjoin="Pubseries.id == Edition.pubseries_id",
        uselist=True,
        order_by='Edition.pubseriesnum',
        viewonly=True)


class PubseriesLink(Base):
    """ Pubseries links. """
    __tablename__ = 'pubserieslink'
    id = Column(Integer, primary_key=True)
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class ShortStory(Base):
    """ Short story table. """
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
    authors = relationship(
        "Person",
        secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
                     Contributor.role_id == 1, \
                     Part.shortstory_id == ShortStory.id)',
        uselist=True, order_by='Person.alt_name', viewonly=True,
        foreign_keys=[Contributor.part_id,
                      Contributor.person_id,
                      Contributor.role_id])
    translators = relationship(
        "Person",
        secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
        Contributor.role_id == 2, Part.shortstory_id == ShortStory.id)',
        uselist=True, order_by='Person.alt_name', viewonly=True,
        foreign_keys=[Contributor.part_id,
                      Contributor.person_id,
                      Contributor.role_id])
    type = relationship('StoryType', uselist=False, viewonly=True)
    contributors = relationship(
        'Contributor', secondary='part', uselist=True, viewonly=True)
    lang = relationship(
        'Language', viewonly=True)
    awards = relationship('Awarded', uselist=True, viewonly=True)
    _author_str: str = ''

    @hybrid_property
    def author_str(self) -> str:
        """
        Returns a string representation of the author(s) of the object.

        :return: A string containing the names of the authors separated by
        ' & '.
        :rtype: str
        """
        if self._author_str != '':
            return self._author_str
        if len(self.authors) > 0:
            self._author_str = ' & '.join([x.name for x in self.authors])
        return self._author_str

    @hybrid_property
    def name(self) -> str:
        """
        Returns the name of the object.

        :return: The name of the object.
        :rtype: str
        """
        return self.title


class StoryGenre(Base):
    """ Story genres. """
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
    """ Story tags. """
    __tablename__ = 'storytag'
    shortstory_id = Column(Integer, ForeignKey('shortstory.id'),
                           nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
                    primary_key=True)


class StoryType(Base):
    """ Story types. """
    __tablename__ = 'storytype'
    id = Column(Integer, primary_key=True)
    name = Column(String(30))


class Tag(Base):
    """ Tag table. """
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text())
    # type = Column(String(100))
    type_id = Column(Integer, ForeignKey('tagtype.id'))
    type = relationship('TagType', uselist=False, viewonly=True)
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


class TagType(Base):
    """ Tag types. """
    __tablename__ = 'tagtype'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)


class User(UserMixin, Base):
    """ User table. """
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True, unique=True)
    password_hash = Column(String(128))
    is_admin = Column(Boolean, default=False)
    language = Column(Integer, ForeignKey('language.id'))
    books = relationship("Edition", secondary="userbook", viewonly=True)

    def set_password(self, password: str) -> None:
        """
        Set the password for the user.

        Args:
            password (str): The password to be set.

        Returns:
            None: This function does not return anything.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Check if the provided password matches the hashed password stored in
        the object.

        Args:
            password (str): The password to be checked.

        Returns:
            bool: True if the password matches the hashed password, False
                  otherwise.
        """
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def validate_user(self, password: str) -> Union[List[str], bool]:
        """
        Validates a user's password and returns a JWT token if the password is
        correct.

        Args:
            password (str): The user's password.

        Returns:
            Union[List[str], bool]: If the password is correct, returns a JWT
            token. Otherwise, returns False.
        """

        if self.check_password(password):
            jwt_token = generate_jwt_token({'id': self.id})
            return jwt_token
        return False

    def __repr__(self) -> str:
        """
        Returns a string representation of the User object.

        :return: A string representation of the User object.
        :rtype: str
        """
        return f'<User {self.name}'


class UserBook(Base):
    """ User books. """
    __tablename__ = 'userbook'
    edition_id = Column(Integer, ForeignKey('edition.id'), nullable=False,
                        primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
                     primary_key=True)
    condition_id = Column(Integer, ForeignKey('bookcondition.id'))
    description = Column(String(100))
    price = Column(Integer)
    added = Column(DateTime, default=datetime.datetime.now(), nullable=True)
    book = relationship("Edition", backref=backref(
        "edition3_assoc"), viewonly=True)
    user = relationship("User", backref=backref("user2_assoc"), viewonly=True)
    condition = relationship("BookCondition",
                             backref=backref("bookcondition_assoc"),
                             viewonly=True)


class UserBookseries(Base):
    """ User book series. """
    __tablename__ = 'userbookseries'
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
                     primary_key=True)
    series_id = Column(Integer, ForeignKey('bookseries.id'), nullable=False,
                       primary_key=True)
    series = relationship("Bookseries", backref=backref(
        "bookseries_assoc"), viewonly=True)
    user = relationship("User", backref=backref("user4_asocc"), viewonly=True)


class UserPubseries(Base):
    """ User pub series. """
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
        basically the representation of the original work of which editions are
        printed. Every work must have at least one edition but sometimes there
        is no work, this is the case with collections. Not all parts have
        necessarily been published in a book.
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
    authors = relationship(
        "Person",
        secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
        primaryjoin='and_(Person.id == Contributor.person_id,\
                     Contributor.part_id == Part.id, Contributor.role_id == 1,\
                     Part.work_id == Work.id,\
                     Part.shortstory_id == None)',
        uselist=True,
        viewonly=True,
        foreign_keys=[Contributor.part_id,
                      Contributor.person_id,
                      Contributor.role_id])
    # translators = relationship(
    #     "Person",
    #     secondary='join(Part, Contributor, Part.id == Contributor.part_id)',
    #     primaryjoin='and_(Person.id == Contributor.person_id,\
    #                  Contributor.role_id == 2,\
    #                  Contributor.part_id == Part.id, Part.work_id == Work.id)',
    #     uselist=True, viewonly=True,
    #     foreign_keys=[Contributor.person_id,
    #                   Contributor.part_id,
    #                   Contributor.role_id])
    parts = relationship('Part', backref=backref(
        'part', uselist=True), viewonly=True)
    bookseries = relationship("Bookseries", backref=backref('bookseries'),
                              uselist=False, viewonly=True)
    editions = relationship(
        'Edition',
        primaryjoin='and_(Part.work_id == Work.id, \
                     Part.edition_id == Edition.id, \
                     Part.shortstory_id == None)',
        secondary='part', uselist=True,
        order_by='Edition.pubyear, Edition.version, Edition.editionnum',
        viewonly=True)
    contributions = relationship(
        'Contributor',
        secondary='part',
        primaryjoin='and_(Part.work_id == Work.id, Part.shortstory_id == None,\
                     Contributor.role_id.in_([1,3]))',
        viewonly=True, uselist=True)
    genres = relationship("Genre", secondary='workgenre',
                          uselist=True, viewonly=True)
    tags = relationship('Tag', secondary='worktag',
                        uselist=True, viewonly=True)
    language_name = relationship(
        'Language', backref=backref('language'), uselist=False)
    stories = relationship('ShortStory', secondary='part', uselist=True,
                           viewonly=True)
    work_type = relationship('WorkType', backref=backref('worktype'),
                             uselist=False)
    links = relationship("WorkLink", uselist=True, viewonly=True)
    awards = relationship('Awarded', uselist=True, viewonly=True)
    author_str = Column(String(500))

    @property
    def name(self) -> str:
        """
        Get the name of the object.

        Returns:
            str: The name of the object.
        """
        return self.title

    # @hybrid_property
    def update_author_str(self) -> Any:
        """
        Update the author string.

        Returns:
            Any: The updated author string.
        """
        retval: str = ''
        if len(self.authors) > 0:
            retval = ' & '.join([x.name for x in self.authors])
        else:
            # Collection of several authors, use editors instead
            retval = ' & '.join(
                [x.name for x in self.editions[0].editors]) + ' (toim.)'
        return retval

    def __str__(self) -> str:
        """
        Returns a string representation of the object.

        :return: A string representation of the object.
        :rtype: str
        """
        retval: str = ''
        edition = self.editions[0]
        # img_src: str = ''
        # if edition.images:
        #     img_src = edition.images[0].image_src
        # else:
        #     img_src = "/static/icons/blue-book-icon-small.png"
        retval = edition_popup(
            self.editions[0].id, self.editions[0], html.escape(self.title),
            '<b>' + html.escape(self.title) + '</b>')
        retval += '. '
        # Bookseries
        if self.bookseries:
            retval += f' {self.bookseries.name}'
            if self.bookseriesnum:
                retval += f' {self.bookseriesnum}'
            retval += '.'

        # Original title and year
        if self.title != self.orig_title:
            retval += f' ({self.orig_title}'
            if self.pubyear != 0:
                retval += f', {self.pubyear}'
            retval += '). '
        elif self.pubyear != 0 and self.pubyear != edition.pubyear:
            retval += f' ({self.pubyear}).'

        # Translators
        if self.editions[0].translators:
            retval += ' Suom <span class="person-list">'
            retval += ' & '.join(
                [x.alt_name for x in self.editions[0].translators
                 if x.alt_name])
            retval += '</span>. '

        # Publisher
        if edition.publisher:
            retval += f' {edition.publisher.name} '
        if edition.pubyear:
            retval += f' {edition.pubyear}'

        retval += '. '

        # Pubseries
        if edition.pubseries:
            retval += f' {edition.pubseries.name}'
            if edition.pubseriesnum:
                retval += f' {edition.pubseriesnum}'
            retval += '. '

        # Genres
        if self.genres:
            for genre in self.genres:
                retval += f'<img src="/static/icons/{genre.abbr}_16.png" \
                title="{genre.name}">'
        retval += '<br>'
        return retval


class WorkGenre(Base):
    """ Links Works with genres. """
    __tablename__ = 'workgenre'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
                     primary_key=True)
    genre_id = Column(Integer, ForeignKey('genre.id'), nullable=False,
                      primary_key=True)


class WorkLink(Base):
    """ Work links table. """
    __tablename__ = 'worklink'
    id = Column(Integer, primary_key=True)
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False)
    link = Column(String(200), nullable=False)
    description = Column(String(100))


class WorkReview(Base):
    """ Links Works with articles that contain a review. """
    __tablename__ = 'workreview'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
                     primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'), nullable=False,
                        primary_key=True)


class WorkTag(Base):
    """ Links Works with tags. """
    __tablename__ = 'worktag'
    work_id = Column(Integer, ForeignKey('work.id'), nullable=False,
                     primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False,
                    primary_key=True)


class WorkType(Base):
    """ Work types. """
    __tablename__ = 'worktype'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)


personworks_table = Table('personworks', Base.metadata,
                          Column('person_id', Integer, ForeignKey(
                              'person.id'), primary_key=True),
                          Column('work.id', Integer, ForeignKey('work.id'),
                                 primary_key=True))


@login.user_loader
def load_user(user_id: Any) -> Any:
    """
    Load a user from the database based on the given ID.

    Parameters:
        id (Any): The ID of the user to load.

    Returns:
        Any: The loaded user object.
    """
    eng = create_engine(db_url, poolclass=NullPool)
    sess = sessionmaker(bind=eng)
    session = sess()
    return session.query(User).get(int(user_id))


engine = create_engine(db_url, poolclass=NullPool, echo=False)
# engine = create_engine(db_url, poolclass=NullPool, echo=True)

Base.metadata.create_all(engine)
