# pylint: disable=no-member, too-few-public-methods, too-many-ancestors
""" SQLAlchemy models for person page. Optimized for speed / size. """
from marshmallow import fields
from app import ma
from app.orm_decl import (Person, Edition, Contributor, Article, Awarded,
                          ShortStory)
from .model import (LanguageSchema, PersonBriefSchema, PersonLinkBriefSchema,
                    WorkBriefSchema,
                    ShortBriefSchema,
                    PublisherBriefSchema, EditionImageBriefSchema,
                    ContributorRoleSchema, IssueBriefSchema,
                    TagBriefSchema, AwardBriefSchema, AwardCategorySchema,
                    CountryBriefSchema, StoryTypeSchema, GenreBriefSchema,
                    BookseriesBriefSchema, WorkContributorSchema)


class PersonPageBriefSchema(ma.SQLAlchemySchema):  # type: ignore
    """ Person schema, shortest usable version. """
    id = fields.Number()
    name = fields.String()
    alt_name = fields.String()


class PersonPagePubseriesSchema(ma.SQLAlchemySchema):  # type: ignore
    """ Pubseries schema, shortest usable version. """
    id = fields.Number()
    name = fields.String()
    publisher = fields.Nested(PublisherBriefSchema(only=('id', 'name')))


class PersonPageContributorSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Contributor schema."""
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Contributor
    person = fields.Nested(PersonPageBriefSchema)
    role = fields.Nested(ContributorRoleSchema)
    description = fields.String()
    real_person = fields.Nested(PersonPageBriefSchema)


class PersonPageArticleSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Article schema."""
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Article
    id = fields.Int()
    title = fields.String()
    person = fields.String()
    author_rel = ma.List(fields.Nested(PersonPageBriefSchema))
    tags = ma.List(fields.Nested(TagBriefSchema))
    issue = fields.Nested(lambda: IssueBriefSchema(
        only=['id', 'cover_number', 'magazine', 'year', 'number']))
    excerpt = fields.String()


class PersonPageEditionBriefSchema(ma.SQLAlchemySchema):  # type: ignore
    """ Edition schema with just id, title and work relationship. """
    id = fields.Int()
    title = fields.String()
    work = fields.Nested(lambda: WorkBriefSchema(only=['id', 'title',
                                                       'orig_title']))


class PersonPageEditionWorkSchema(ma.SQLAlchemySchema):  # type: ignore
    """ Edition work schema. """
    id = fields.Int()
    title = fields.String()
    orig_title = fields.String()
    author_str = fields.String()
    pubyear = fields.Int()
    editions = ma.List(fields.Nested(lambda: PersonPageEditionBriefSchema(
        only=['id', 'title', 'work'])))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    bookseries = fields.Nested(
        lambda: BookseriesBriefSchema(exclude=['works']))
    tags = ma.List(fields.Nested(TagBriefSchema))
    contributions = ma.List(fields.Nested(lambda: WorkContributorSchema(
        only=['description', 'person', 'role'])))
    language_name = fields.Nested(LanguageSchema)


class PersonPageEditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Edition

    publisher = fields.Nested(PublisherBriefSchema, only=('id', 'name'))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    # translators = ma.List(fields.Nested(PersonPageBriefSchema))
    pubseries = fields.Nested(PersonPagePubseriesSchema)
    work = ma.List(fields.Nested(lambda: PersonPageEditionWorkSchema(
        only=['id', 'title', 'orig_title', 'pubyear', 'editions', 'genres',
              'bookseries', 'tags', 'contributions', 'language_name'])))
    # images = ma.List(fields.Nested(EditionImageBriefSchema))
    # binding = fields.Nested(BindingBriefSchema)
    # format = fields.Nested(FormatBriefSchema)
    # editors = ma.List(fields.Nested(PersonPageBriefSchema))
    contributions = ma.List(fields.Nested(PersonPageContributorSchema))
    owners = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    wishlisted = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))


class AwardedSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Awarded schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Awarded
    award = fields.Nested(AwardBriefSchema)
    person = fields.Nested(PersonPageBriefSchema)
    work = fields.Nested(WorkBriefSchema)
    category = fields.Nested(AwardCategorySchema)
    story = fields.Nested(ShortBriefSchema)


class PersonPageShortBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Short story schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = ShortStory
    # id = fields.Int()
    # title = fields.String()
    # orig_title = fields.String()
    # pubyear = fields.Int()
    # authors = ma.List(fields.Nested(PersonBriefSchema))
    type = fields.Nested(StoryTypeSchema)
    issues = ma.List(fields.Nested(lambda: IssueBriefSchema(
        only=['id', 'cover_number', 'magazine', 'year', 'number'])))
    editions = ma.List(fields.Nested(PersonPageEditionSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    contributors = ma.List(fields.Nested(PersonPageContributorSchema))
    tags = ma.List(fields.Nested(TagBriefSchema))
    language_name = fields.Nested(CountryBriefSchema)


class PersonPageWorkBriefSchema(ma.SQLAlchemySchema):  # type: ignore
    """ Work schema, brief version. """
    id = fields.Number()
    title = fields.String()
    orig_title = fields.String()
    author_str = fields.String()
    pubyear = fields.Number()
    contributions = ma.List(fields.Nested(WorkContributorSchema))
    editions = ma.List(fields.Nested(PersonPageEditionSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    bookseries = fields.Nested(
        lambda: BookseriesBriefSchema(exclude=['works']))
    bookseriesnum = fields.String()
    tags = ma.List(fields.Nested(TagBriefSchema))
    language_name = fields.Nested(LanguageSchema)
    type = fields.Number()


class PersonSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Person schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Person
    real_names = ma.List(fields.Nested(PersonPageBriefSchema))
    aliases = ma.List(fields.Nested(PersonPageBriefSchema))
    links = ma.List(fields.Nested(PersonLinkBriefSchema))
    works = ma.List(fields.Nested(PersonPageWorkBriefSchema))
    # work_contributions = ma.List(fields.Nested(PersonPageWorkBriefSchema))
    stories = ma.List(fields.Nested(PersonPageShortBriefSchema))
    edits = ma.List(fields.Nested(PersonPageEditionSchema))
    # translations = ma.List(fields.Nested(PersonPageEditionSchema))
    editions = ma.List(fields.Nested(PersonPageEditionSchema))
    chief_editor = ma.List(fields.Nested(IssueBriefSchema))
    articles = ma.List(fields.Nested(PersonPageArticleSchema))
    magazine_stories = ma.List(fields.Nested(ShortBriefSchema))
    translated_stories = ma.List(fields.Nested(ShortBriefSchema))
    appears_in = ma.List(fields.Nested(PersonPageArticleSchema))
    personal_awards = ma.List(fields.Nested(AwardBriefSchema))
    nationality = fields.Nested(CountryBriefSchema)
    awarded = ma.List(fields.Nested(AwardedSchema))
