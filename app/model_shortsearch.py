# pylint: disable=no-member, too-few-public-methods, too-many-ancestors
""" Database models for short search. """
from marshmallow import fields
from app import ma
from app.orm_decl import (Contributor, Edition, Issue, Magazine, Person,
                          ShortStory, Work)
from .model import (GenreBriefSchema, EditionImageBriefSchema,
                    WorkBriefestSchema,
                    PersonBriefSchema, ContributorRoleSchema, StoryTypeSchema,
                    ContributorSchema, LanguageSchema)

# Schemas for short story search


class ShortSearchPersonSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Person schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Person
        fields = ('id', 'name')


class ShortSearchEdition(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Edition

    images = ma.List(fields.Nested(EditionImageBriefSchema))
    work = ma.List(fields.Nested(WorkBriefestSchema))


class ShortSearchWork(ma.SQLAlchemyAutoSchema):  # type: ignore
    " Work schema. "
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Work


class ShortSearchContributor(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Contributor schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Contributor
    person = fields.Nested(PersonBriefSchema(only=('id', 'name',)))
    role = fields.Nested(ContributorRoleSchema)
    description = fields.String()
    real_person = fields.Nested(lambda: PersonBriefSchema(only=('id', 'name')))


class ShortSearchMagazine(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Magazine schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Magazine


class ShortSearchIssue(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Issue schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Issue
    magazine = fields.Nested(ShortSearchMagazine)


class ShortSchemaForSearch(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Short story schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = ShortStory

    works = ma.List(fields.Nested(ShortSearchWork))
    editions = ma.List(fields.Nested(ShortSearchEdition))
    issues = ma.List(fields.Nested(ShortSearchIssue))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    type = fields.Nested(StoryTypeSchema)
    contributors = ma.List(fields.Nested(ContributorSchema))
    lang = fields.Nested(LanguageSchema)
