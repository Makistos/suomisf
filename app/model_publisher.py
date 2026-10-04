# pylint: disable=no-member, too-few-public-methods, too-many-ancestors
""" SQLAlchemy model for publisher. """
from marshmallow import fields
from app import ma
from app.model import (WorkContributorSchema, EditionImageBriefSchema,
                       GenreBriefSchema, LanguageSchema, MagazineBriefSchema,
                       PersonBriefSchema,
                       PublisherLinkSchema, PubseriesSchema)
from app.orm_decl import Edition, Publisher, Work


class WorkSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work schema. """
    class Meta:
        """ Meta class. """
        model = Work
    contributions = ma.List(fields.Nested(WorkContributorSchema()))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    language_name = fields.Nested(LanguageSchema)
    type = fields.Integer()


class EditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition schema. """
    class Meta:
        """ Meta class. """
        model = Edition
    work = fields.Nested(WorkSchema)
    publisher = fields.Nested('PublisherSchema', only=('id', 'name'))
    pubseries = fields.Nested(PubseriesSchema(
        only=('id', 'name')))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    owners = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    wishlisted = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))


# What the publisher page's edition list (EditionList, EditionSummary,
# CoverImageList and their grouping/sorting helpers) reads. A publisher can
# have thousands of editions, so nothing else is sent (2026-10: WSOY's page
# was 4.6 MB). Keep in step with get_publisher's eager loading.
PUBLISHER_EDITION_FIELDS = (
    'id', 'title', 'pubyear', 'editionnum', 'version', 'pages', 'size',
    'isbn',  # combineEditions indexes it unless it's a string or null
    'images', 'publisher', 'owners', 'wishlisted',
    'work.id', 'work.title', 'work.orig_title', 'work.pubyear', 'work.type',
    'work.author_str', 'work.genres', 'work.language_name', 'work.contributions',
)


class PublisherPageSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher schema. """
    class Meta:
        """ Meta class. """
        model = Publisher
    editions = ma.List(fields.Nested(EditionSchema(only=PUBLISHER_EDITION_FIELDS)))
    series = ma.List(fields.Nested(PubseriesSchema(only=('id', 'name'))))
    links = ma.List(fields.Nested(PublisherLinkSchema))
    magazines = ma.List(fields.Nested(MagazineBriefSchema(
        only=('id', 'name', 'type_id'))))
