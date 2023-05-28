from marshmallow import fields
from app.orm_decl import (Person, Edition, Pubseries, Contributor, Article, Awarded)
from .model import (PersonLinkBriefSchema, WorkBriefSchema, ShortBriefSchema,
                    PublisherBriefSchema, EditionImageBriefSchema, BindingBriefSchema,
                    FormatBriefSchema, ContributorRoleSchema, IssueBriefSchema,
                    TagBriefSchema, AwardBriefSchema, AwardCategorySchema, CountryBriefSchema)
from app import ma

class PersonPageBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Person
    id = fields.Number()
    name = fields.String()
    alt_name = fields.String()
    fullname = fields.String()
    image_src = fields.String()

class PersonPagePubseriesSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Pubseries

    publisher = fields.Nested(PublisherBriefSchema)

class PersonPageContributorSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Contributor
    person = fields.Nested(PersonPageBriefSchema)
    role = fields.Nested(ContributorRoleSchema)
    description = fields.String()
    real_person = fields.Nested(PersonPageBriefSchema)

class PersonPageArticleSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Article
    id = fields.Int()
    title = fields.String()
    person = fields.String()
    author_rel = ma.List(fields.Nested(PersonPageBriefSchema))
    tags = ma.List(fields.Nested(TagBriefSchema))
    issue = fields.Nested(IssueBriefSchema)
    excerpt = fields.String()

class PersonPageEditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Edition

    publisher = fields.Nested(PublisherBriefSchema, only=('id', 'name'))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    translators = ma.List(fields.Nested(PersonPageBriefSchema))
    pubseries = fields.Nested(PersonPagePubseriesSchema)
    work = ma.List(fields.Nested(WorkBriefSchema))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    #binding = fields.Nested(BindingBriefSchema)
    #format = fields.Nested(FormatBriefSchema)
    editors = ma.List(fields.Nested(PersonPageBriefSchema))
    contributions = ma.List(fields.Nested(PersonPageContributorSchema))

class AwardedSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Awarded
    award = fields.Nested(AwardBriefSchema)
    person = fields.Nested(PersonPageBriefSchema)
    work = fields.Nested(WorkBriefSchema)
    category = fields.Nested(AwardCategorySchema)
    story = fields.Nested(ShortBriefSchema)

class PersonSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Person
    real_names = ma.List(fields.Nested(PersonPageBriefSchema))
    aliases = ma.List(fields.Nested(PersonPageBriefSchema))
    links = ma.List(fields.Nested(PersonLinkBriefSchema))
    works = ma.List(fields.Nested(WorkBriefSchema))
    stories = ma.List(fields.Nested(ShortBriefSchema))
    edits = ma.List(fields.Nested(PersonPageEditionSchema))
    translations = ma.List(fields.Nested(PersonPageEditionSchema))
    chief_editor = ma.List(fields.Nested(IssueBriefSchema))
    articles = ma.List(fields.Nested(PersonPageArticleSchema))
    magazine_stories = ma.List(fields.Nested(ShortBriefSchema))
    translated_stories = ma.List(fields.Nested(ShortBriefSchema))
    appears_in = ma.List(fields.Nested(PersonPageArticleSchema))
    personal_awards = ma.List(fields.Nested(AwardBriefSchema))
    nationality = fields.Nested(CountryBriefSchema)
    awarded = ma.List(fields.Nested(AwardedSchema))
