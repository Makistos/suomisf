from marshmallow import Schema, fields

from app import ma
from app.orm_decl import (Article, Award, AwardCategory, Awarded, BindingType, Bookseries, Contributor, ContributorRole, Country, Edition,
                          EditionImage, Genre, Issue, Language, Log, Magazine, Person, PersonLink,
                          PublicationSize, Publisher, PublisherLink, Pubseries, ShortStory, Tag, User,
                          Work, Article, StoryType, WorkLink, Format, WorkType)

class BookIndexPubseriesSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Pubseries

class BookIndexPersonSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Person

class BookIndexContributorRoleSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = ContributorRole

class BookIndexEditionImageSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = EditionImage

class BookIndexGenreSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Genre
    # id = fields.Int(required=True)
    # name = fields.String(required=True)
    # abbr = fields.String()

class BookIndexPublisherSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Publisher

class BookIndexBookseriesSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Bookseries

class BookIndexTagSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Tag

class BookIndexWorkContributorSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Contributor
    person = fields.Nested(BookIndexPersonSchema(only=('id', 'name', 'alt_name')))
    role = fields.Nested(BookIndexContributorRoleSchema)
    description = fields.String()
    #real_person = fields.Nested(lambda: BookIndexPersonSchema(only=('id', 'name')))

class BookIndexWorkEditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Edition

    editors = ma.List(fields.Nested(BookIndexPersonSchema))
    translators = ma.List(fields.Nested(BookIndexPersonSchema))
    contributions = ma.List(fields.Nested(BookIndexWorkContributorSchema))
    images = ma.List(fields.Nested(BookIndexEditionImageSchema))
    publisher = fields.Nested(lambda: BookIndexPublisherSchema(only=('id', 'name')))

class BookIndexWorkTypeSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = WorkType
    # id = fields.Int()
    # name = fields.String()

class WorkEditionBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Edition

    #editors = ma.List(fields.Nested(BookIndexPersonSchema))
    #translators = ma.List(fields.Nested(PersonBriefSchema))
    contributions = ma.List(fields.Nested(BookIndexWorkContributorSchema))
    images = ma.List(fields.Nested(BookIndexEditionImageSchema))
    publisher = fields.Nested(lambda: BookIndexPublisherSchema(only=('id', 'name')))
    pubseries = fields.Nested(lambda: BookIndexPubseriesSchema(only=('id', 'name')))

class BookIndexSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Work

    # id = fields.Number()
    # title = fields.String()
    # orig_title = fields.String()
    # author_str = fields.String()
    contributions = ma.List(fields.Nested(BookIndexWorkContributorSchema))
    editions = ma.List(fields.Nested(WorkEditionBriefSchema,
                                     only=['id', 'title', 'pubyear', 'publisher',
                                           'contributions', 'images', 'version',
                                           'pubseries',
                                           'pubseriesnum', 'editionnum']))
    # authors = ma.List(fields.Nested(BookIndexPersonSchema))
    genres = ma.List(fields.Nested(BookIndexGenreSchema))
    bookseries = fields.Nested(BookIndexBookseriesSchema)
    tags = ma.List(fields.Nested(BookIndexTagSchema))

