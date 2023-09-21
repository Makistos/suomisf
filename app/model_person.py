from marshmallow import fields
from app.orm_decl import (Person, Edition, Pubseries, Contributor, Article, Awarded,
                          ShortStory, Work)
from .model import (PersonLinkBriefSchema, WorkBriefSchema, ShortBriefSchema,
                    PublisherBriefSchema, EditionImageBriefSchema, BindingBriefSchema,
                    FormatBriefSchema, ContributorRoleSchema, IssueBriefSchema,
                    TagBriefSchema, AwardBriefSchema, AwardCategorySchema, CountryBriefSchema,
                    ShortSchema, PersonBriefSchema, StoryTypeSchema, GenreBriefSchema,
                    BookseriesBriefSchema, WorkContributorSchema, WorkEditionBriefSchema,
                    EditionBriefSchema)
from app import ma

class PersonPageBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    # class Meta:
    #     model = Person
    id = fields.Number()
    name = fields.String()
    alt_name = fields.String()
    # fullname = fields.String()
    # image_src = fields.String()

class PersonPagePubseriesSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    id = fields.Number()
    name = fields.String()
    publisher = fields.Nested(PublisherBriefSchema(only=('id', 'name')))

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

class PersonPageEditionBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    id = fields.Int()
    title = fields.String()
    work = fields.Nested(lambda: WorkBriefSchema(only=['id', 'title', 'orig_title']))

class PersonPageEditionWorkSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    id = fields.Int()
    title = fields.String()
    orig_title = fields.String()
    author_str = fields.String()
    editions = ma.List(fields.Nested(lambda: PersonPageEditionBriefSchema(
        only=['id', 'title', 'work'])))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    bookseries = fields.Nested(lambda: BookseriesBriefSchema(exclude=['works']))
    tags = ma.List(fields.Nested(TagBriefSchema))
    contributions = ma.List(fields.Nested(lambda: WorkContributorSchema(
        only=['description', 'person', 'role'])))

class PersonPageEditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Edition

    publisher = fields.Nested(PublisherBriefSchema, only=('id', 'name'))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    #translators = ma.List(fields.Nested(PersonPageBriefSchema))
    pubseries = fields.Nested(PersonPagePubseriesSchema)
    work = ma.List(fields.Nested(lambda: PersonPageEditionWorkSchema(
        only=['id', 'title', 'orig_title', 'editions', 'genres', 'bookseries',
              'tags', 'contributions'])))
    #images = ma.List(fields.Nested(EditionImageBriefSchema))
    #binding = fields.Nested(BindingBriefSchema)
    #format = fields.Nested(FormatBriefSchema)
    #editors = ma.List(fields.Nested(PersonPageBriefSchema))
    contributions = ma.List(fields.Nested(PersonPageContributorSchema))

class AwardedSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Awarded
    award = fields.Nested(AwardBriefSchema)
    person = fields.Nested(PersonPageBriefSchema)
    work = fields.Nested(WorkBriefSchema)
    category = fields.Nested(AwardCategorySchema)
    story = fields.Nested(ShortBriefSchema)

class PersonPageShortBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = ShortStory

    # id = fields.Int()
    # title = fields.String()
    # orig_title = fields.String()
    # pubyear = fields.Int()
    #authors = ma.List(fields.Nested(PersonBriefSchema))
    type = fields.Nested(StoryTypeSchema)
    issues = ma.List(fields.Nested(IssueBriefSchema))
    editions = ma.List(fields.Nested(PersonPageEditionSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    contributors = ma.List(fields.Nested(PersonPageContributorSchema))

class PersonPageWorkBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore

    id = fields.Number()
    title = fields.String()
    orig_title = fields.String()
    author_str = fields.String()
    contributions = ma.List(fields.Nested(WorkContributorSchema))
    editions = ma.List(fields.Nested(PersonPageEditionSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    bookseries = fields.Nested(lambda: BookseriesBriefSchema(exclude=['works']))
    tags = ma.List(fields.Nested(TagBriefSchema))

class PersonSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    class Meta:
        model = Person
    real_names = ma.List(fields.Nested(PersonPageBriefSchema))
    aliases = ma.List(fields.Nested(PersonPageBriefSchema))
    links = ma.List(fields.Nested(PersonLinkBriefSchema))
    works = ma.List(fields.Nested(PersonPageWorkBriefSchema))
    stories = ma.List(fields.Nested(PersonPageShortBriefSchema))
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
