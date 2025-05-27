# pylint: disable=no-member, too-few-public-methods, too-many-ancestors
""" SQLAlchemy models for bookindex page. """
from marshmallow import fields

from app import ma
from app.model import (LanguageSchema, PersonBriefSchema)
from app.orm_decl import (Bookseries, Contributor, ContributorRole, Edition,
                          EditionImage, Genre, Person,
                          Publisher, Pubseries, Tag,
                          Work, WorkType)


class BookIndexPubseriesSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Pubseries schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Pubseries


class BookIndexPersonSchema(ma.SQLAlchemySchema):  # type: ignore
    """ Person schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Person
    id = fields.Int()
    name = fields.String()
    alt_name = fields.String()


class BookIndexContributorRoleSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Contributor role schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = ContributorRole


class BookIndexEditionImageSchema(ma.SQLAlchemySchema):  # type: ignore
    """ Edition image schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = EditionImage
    id = fields.Int()
    image_src = fields.String()


class BookIndexGenreSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Genre schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Genre
    # id = fields.Int(required=True)
    # name = fields.String(required=True)
    # abbr = fields.String()


class BookIndexPublisherSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Publisher


class BookIndexBookseriesSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Bookseries schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Bookseries


class BookIndexTagSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Tag schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Tag


class BookIndexWorkContributorSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work contributor schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Contributor
    person = fields.Nested(BookIndexPersonSchema())
    # person = fields.Nested(BookIndexPersonSchema(
    #     only=('id', 'name', 'alt_name')))
    role = fields.Nested(BookIndexContributorRoleSchema)
    # description = fields.String()
    # real_person = fields.Nested(
    # lambda: BookIndexPersonSchema(only=('id', 'name')))


class BookIndexEditionWorkSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Work


class BookIndexWorkEditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Edition
    editors = ma.List(fields.Nested(BookIndexPersonSchema))
    translators = ma.List(fields.Nested(BookIndexPersonSchema))
    contributions = ma.List(fields.Nested(BookIndexWorkContributorSchema))
    images = ma.List(fields.Nested(BookIndexEditionImageSchema))
    publisher = fields.Nested(
        lambda: BookIndexPublisherSchema(only=('id', 'name')))
    work = ma.List(fields.Nested(
        lambda: BookIndexEditionWorkSchema(
            only=('id', 'title', 'orig_title'))))


class BookIndexWorkTypeSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work type schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = WorkType
    # id = fields.Int()
    # name = fields.String()


class WorkEditionBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work edition schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Edition
    # editors = ma.List(fields.Nested(BookIndexPersonSchema))
    # translators = ma.List(fields.Nested(PersonBriefSchema))
    contributions = ma.List(fields.Nested(BookIndexWorkContributorSchema))
    images = ma.List(fields.Nested(BookIndexEditionImageSchema))
    publisher = fields.Nested(
        lambda: BookIndexPublisherSchema(only=('id', 'name')))
    pubseries = fields.Nested(
        lambda: BookIndexPubseriesSchema(only=('id', 'name')))
    work = ma.List(fields.Nested(
        lambda: BookIndexEditionWorkSchema(
            only=('id', 'title', 'orig_title'))))
    owners = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    wishlisted = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))


class BookIndexSchema(ma.SQLAlchemySchema):  # type: ignore
    """ Main schema for BookIndex page. """

    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Work

    id = fields.Number()
    title = fields.String()
    orig_title = fields.String()
    author_str = fields.String()
    pubyear = fields.Number()

    contributions = ma.List(fields.Nested(BookIndexWorkContributorSchema))
    editions = ma.List(
        fields.Nested(WorkEditionBriefSchema,
                      only=['id', 'title', 'pubyear', 'publisher',
                            'contributions', 'images', 'version',
                            'pubseries',
                            'pubseriesnum', 'editionnum', 'work',
                            'owners', 'wishlisted']))
    # authors = ma.List(fields.Nested(BookIndexPersonSchema))
    genres = ma.List(fields.Nested(BookIndexGenreSchema))
    bookseries = fields.Nested(BookIndexBookseriesSchema, only=['id', 'name'])
    tags = ma.List(fields.Nested(BookIndexTagSchema, only=['id', 'name']))
    type = fields.Number()
    language_name = fields.Nested(LanguageSchema, only=['id'])
