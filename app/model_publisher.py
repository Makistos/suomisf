# pylint: disable=no-member, too-few-public-methods, too-many-ancestors
""" SQLAlchemy model for publisher. """
from marshmallow import fields
from app import ma
from app.model import (ContributorSchema, EditionImageBriefSchema,
                       GenreBriefSchema, LanguageSchema, MagazineBriefSchema,
                       PersonBriefSchema,
                       PublisherLinkSchema, PubseriesSchema)
from app.orm_decl import Edition, Publisher, Work


class WorkSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work schema. """
    class Meta:
        """ Meta class. """
        model = Work
    contributions = ma.List(fields.Nested(ContributorSchema()))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    language_name = fields.Nested(LanguageSchema)
    type = fields.Number()


class EditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition schema. """
    class Meta:
        """ Meta class. """
        model = Edition
    work = ma.List(fields.Nested(WorkSchema))
    publisher = fields.Nested('PublisherSchema', only=('id', 'name'))
    pubseries = fields.Nested(PubseriesSchema(
        only=('id', 'name')))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    owners = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    wishlisted = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))


class PublisherPageSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher schema. """
    class Meta:
        """ Meta class. """
        model = Publisher
    editions = ma.List(fields.Nested(EditionSchema))
    series = ma.List(fields.Nested(PubseriesSchema(only=('id', 'name'))))
    links = ma.List(fields.Nested(PublisherLinkSchema))
    magazines = ma.List(fields.Nested(MagazineBriefSchema(
        only=('id', 'name', 'type_id'))))
