# pylint: disable=no-member, too-few-public-methods, too-many-ancestors
""" SQLAlchemy models not fitting into other model_ files. """
from marshmallow import Schema, fields
from app import ma
from app.orm_decl import (Article, Award, AwardCategory, Awarded, BindingType,
                          BookCondition,
                          Bookseries, Contributor, ContributorRole, Country,
                          Edition, EditionImage, Genre, Issue, Language, Log,
                          Magazine, Person, PersonLink, PublicationSize,
                          Publisher, PublisherLink, Pubseries, ShortStory, Tag,
                          TagType, UserBook, MagazineType,
                          Work, StoryType, WorkLink, Format, WorkType)

# Brief schemas should not include any relationships to other
# tables. These exists to get around the issue with Python that
# you can't have two entities using each other. It is impossible
# to get the one defined first to "see" the other. Plus this will
# minimize data transfer. So brief schemas is used by other schemas
# to implement nested data structures.

# Some exceptions are required. Therefore ordering of these
# definitions might well be critical.


class TagTypeSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Tag type schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = TagType


class MagazineTypeSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Magazine type schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = MagazineType


class WorkBriefestSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work schema with no relationships. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Work


class ArticleBriefestSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Article schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Article


class ShortTagSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Short story schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = ShortStory


class TagBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Tag schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Tag
    type = fields.Nested(TagTypeSchema)
    works = ma.List(fields.Nested(WorkBriefestSchema(only=("id",))))
    articles = ma.List(fields.Nested(ArticleBriefestSchema(only=("id",))))
    stories = ma.List(fields.Nested(ShortTagSchema(only=("id",))))


class UserSchema(ma.SQLAlchemySchema):  # type: ignore
    """ User schema. """
    id = fields.Int(required=True)
    name = fields.String(required=True)
    is_admin = fields.Boolean(required=True)


class LanguageSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Language schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Language
    id = fields.Int(required=True)
    name = fields.String(required=True)


class LogSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Log schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Log
    user = fields.Nested(UserSchema)


class ErrorSchema(Schema):
    """ Error schema. """
    code = fields.Int(required=True,)
    message = fields.String(required=True,)


class BindingBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Binding schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = BindingType


class FormatBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Format schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Format


class BookseriesBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Bookseries schema with only works relationship. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Bookseries
    works = ma.List(fields.Nested(WorkBriefestSchema))


class EditionImageBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition image schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = EditionImage


class PersonLinkBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Person link schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = PersonLink


class PublicationSizeBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publication size schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = PublicationSize


class StoryTypeSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Story type schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = StoryType


class WorkLinkBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work link schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = WorkLink


class ContributorRoleSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Contributor role schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = ContributorRole


class CountryBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Country schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Country


class GenreBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Genre schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Genre
    # id = fields.Int(required=True)
    # name = fields.String(required=True)
    # abbr = fields.String()


class LinkSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Link schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = PersonLink

# class PersonBriefestSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
#     """ Minimal person schema. """
#     class Meta:
#         """ Metadata for SQLAlchemyAutoSchema. """
#         model = Person


class PersonBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Person schema with no relationships. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Person
    id = fields.Number()
    name = fields.String()
    alt_name = fields.String()
    fullname = fields.String()
    image_src = fields.String()
    dob = fields.Number()
    dod = fields.Number()
    roles = fields.Pluck("self", "name", many=True)
    # nationality = fields.String(attribute='nationalityname')
    nationality = fields.Nested(CountryBriefSchema)
    workcount = fields.Number()
    # storycount = fields.Number()
    storycount = fields.Function(lambda obj: len([x.id for x in obj.stories]))


class WorkContributorSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work contributor schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Contributor
    person = fields.Nested(PersonBriefSchema(only=('id', 'name', 'alt_name')))
    role = fields.Nested(ContributorRoleSchema)
    description = fields.String()
    real_person = fields.Nested(lambda: PersonBriefSchema(only=('id', 'name')))


class WorkEditionBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work edition schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Edition
    editors = ma.List(fields.Nested(PersonBriefSchema))
    translators = ma.List(fields.Nested(PersonBriefSchema))
    contributions = ma.List(fields.Nested(WorkContributorSchema))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    publisher = fields.Nested(lambda: PublisherSchema(only=('id', 'name')))
    Language = fields.Nested(lambda: LanguageSchema(only=('id', 'name')))
    owners = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    wishlisted = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))


class WorkTypeBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work type schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = WorkType
    id = fields.Int()
    name = fields.String()


class WorkBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work schema without all relationships. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Work
    id = fields.Number()
    title = fields.String()
    orig_title = fields.String()
    author_str = fields.String()
    contributions = ma.List(fields.Nested(WorkContributorSchema))
    editions = ma.List(fields.Nested(WorkEditionBriefSchema))
    # authors = ma.List(fields.Nested(PersonBriefSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    bookseries = fields.Nested(BookseriesBriefSchema, exclude=("works",))
    tags = ma.List(fields.Nested(TagBriefSchema), only=("id", "name"))
    language_name = fields.Nested(LanguageSchema)
    type = fields.Number()


class EditionBriefestSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition schema with just images and work relationships. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Edition
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    # work = fields.Pluck(WorkBriefestSchema, 'id')
    work = ma.List(fields.Nested(WorkBriefestSchema))
    owners = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    wishlisted = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))


class EditionImageSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition image schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = EditionImage
    edition = fields.Nested(EditionBriefestSchema)


class EditionBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition schema with work, editors, contributions and  images
    relationships.
    """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Edition
    work = ma.List(fields.Nested(WorkBriefSchema))
    editors = ma.List(fields.Nested(PersonBriefSchema))
    contributions = ma.List(fields.Nested(WorkContributorSchema))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    publisher = fields.Nested(lambda: PublisherSchema(only=('id', 'name')))
    owners = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    wishlisted = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    binding = fields.Nested(BindingBriefSchema)


class BookConditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Book condition schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = BookCondition


class UserBookSchema(ma.SQLAlchemyAutoSchema):
    """ User book schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = UserBook
    book = fields.Nested(EditionBriefSchema)
    user = fields.Nested(UserSchema)
    condition = fields.Nested(BookConditionSchema)


class MagazineBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Magazine schema with no relationships. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Magazine
    type_id = fields.Int()
    type = fields.Nested(MagazineTypeSchema)


class IssueBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Issue schema with just magazine relationship. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Issue
    magazine = fields.Nested(MagazineBriefSchema)


class ContributorSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Contributor schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Contributor
    person = fields.Nested(PersonBriefSchema(only=('id', 'name', 'alt_name')))
    role = fields.Nested(ContributorRoleSchema)
    description = fields.String()
    real_person = fields.Nested(
        lambda: PersonBriefSchema(only=('id', 'name',
                                        'alt_name')))


class ShortBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Short story schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = ShortStory
    authors = ma.List(fields.Nested(PersonBriefSchema))
    type = fields.Nested(StoryTypeSchema)
    issues = ma.List(fields.Nested(IssueBriefSchema))
    editions = ma.List(fields.Nested(EditionBriefSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    contributors = ma.List(fields.Nested(ContributorSchema))
    lang = fields.Nested(LanguageSchema)


class ShortBriefestSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Short story schema for dropdowns etc. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = ShortStory
    contributors = ma.List(fields.Nested(ContributorSchema))
    type = fields.Nested(StoryTypeSchema)
    lang = fields.Nested(LanguageSchema)


class ArticleBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Article schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Article
    id = fields.Int()
    title = fields.String()
    author_rel = ma.List(fields.Nested(PersonBriefSchema))
    excerpt = fields.String()


class AwardCategorySchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Award category schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = AwardCategory


class AwardBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Award schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Award
    categories = ma.List(fields.Nested(AwardCategorySchema))


class PublisherBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Publisher


class PublisherBriefSchemaWEditions(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Publisher
    editions = ma.List(fields.Nested(
        lambda: EditionSchema(only=('id', 'pubyear'))))


class PubseriesBriefSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Pubseries
    publisher = fields.Nested(PublisherBriefSchema)
    editions = ma.List(fields.Nested(EditionBriefestSchema))


# Full schemas. Mainly used to be returned as the main object
# type in API calls. This makes is super easy to retrieve all
# relevant data for certain object types.

class AwardedSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Awarded schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Awarded
    award = fields.Nested(
        AwardBriefSchema(only=('id', 'name', 'domestic')))
    person = fields.Nested(PersonBriefSchema)
    work = fields.Nested(
        WorkBriefSchema(
            only=('id', 'title', 'author_str', 'orig_title', 'pubyear')))
    category = fields.Nested(AwardCategorySchema)
    story = fields.Nested(ShortBriefSchema)


class AwardSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Award schema with all relationships. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Award
    categories = ma.List(fields.Nested(AwardCategorySchema))
    winners = ma.List(fields.Nested(AwardedSchema))


class BookseriesSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Book series schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Bookseries
    works = ma.List(fields.Nested(WorkBriefSchema))


class PubseriesSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Pubseries
    pubseries_id = fields.Int()
    publisher = fields.Nested(PublisherBriefSchema(
        only=('id', 'name', 'fullname')
    ))
    editions = ma.List(fields.Nested(EditionBriefSchema))


class EditionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Edition schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Edition
    publisher = fields.Nested(PublisherBriefSchema)
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    translators = ma.List(fields.Nested(PersonBriefSchema))
    pubseries = fields.Nested(PubseriesBriefSchema)
    work = ma.List(fields.Nested(WorkBriefSchema))
    images = ma.List(fields.Nested(EditionImageBriefSchema))
    binding = fields.Nested(BindingBriefSchema)
    format = fields.Nested(FormatBriefSchema)
    editors = ma.List(fields.Nested(PersonBriefSchema))
    contributions = ma.List(fields.Nested(ContributorSchema))
    owners = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))
    wishlisted = ma.List(fields.Nested(PersonBriefSchema(only=('id', 'name'))))


class WorkSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Work schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Work
    editions = ma.List(fields.Nested(EditionSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    bookseries = fields.Nested(BookseriesBriefSchema)
    tags = ma.List(fields.Nested(TagBriefSchema))
    language_name = fields.Nested(LanguageSchema)
    # authors = ma.List(fields.Nested(PersonBriefSchema))
    links = ma.List(fields.Nested(WorkLinkBriefSchema))
    stories = ma.List(fields.Nested(ShortBriefSchema))
    translators = ma.List(fields.Nested(PersonBriefSchema))
    awards = ma.List(fields.Nested(AwardedSchema))
    contributions = ma.List(fields.Nested(ContributorSchema))
    type = fields.Number()
    work_type = fields.Nested(WorkTypeBriefSchema)


class ArticleSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Article schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Article
    id = fields.Int()
    title = fields.String()
    person = fields.String()
    author_rel = ma.List(fields.Nested(PersonBriefSchema))
    tags = ma.List(fields.Nested(TagBriefSchema))
    issue = fields.Nested(IssueBriefSchema)
    excerpt = fields.String()


class PublisherLinkSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher link schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = PublisherLink


class PublisherSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Publisher schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Publisher
    editions = ma.List(fields.Nested(EditionBriefSchema))
    series = ma.List(fields.Nested(PubseriesBriefSchema))
    links = ma.List(fields.Nested(PublisherLinkSchema))


class ShortSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Short story schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = ShortStory
    authors = ma.List(fields.Nested(PersonBriefSchema))
    translators = ma.List(fields.Nested(PersonBriefSchema))
    tags = ma.List(fields.Nested(TagBriefSchema), only=("id", "name"))
    issues = ma.List(fields.Nested(IssueBriefSchema))
    works = ma.List(fields.Nested(WorkBriefSchema))
    editions = ma.List(fields.Nested(EditionBriefSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    type = fields.Nested(StoryTypeSchema)
    contributors = ma.List(fields.Nested(ContributorSchema))
    lang = fields.Nested(LanguageSchema)
    awards = ma.List(fields.Nested(AwardedSchema))


class IssueSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Issue schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Issue
        include_fk = True
    # magazine = ma.auto_field()
    editors = ma.List(fields.Nested(PersonBriefSchema))
    size = fields.Nested(PublicationSizeBriefSchema)
    articles = ma.List(fields.Nested(ArticleBriefSchema()))
    stories = ma.List(fields.Nested(ShortBriefSchema()))
    magazine = fields.Nested(MagazineBriefSchema)
    contributors = ma.List(fields.Nested(ContributorSchema))


class MagazineSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Magazine schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Magazine
        include_fk = True
    # issues = ma.auto_field()  # ma.List(fields.Nested(IssueSchema))
    issues = ma.List(fields.Nested(IssueBriefSchema),
                     only=("id", "number", "number_extra", "count", "year",
                           "cover_number"))
    publisher = fields.Nested(PublisherBriefSchema)
    type = fields.Nested(MagazineTypeSchema)


class TagSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Tag schema. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Tag

    works = ma.List(fields.Nested(WorkBriefSchema, exclude=("tags",)))
    articles = ma.List(fields.Nested(ArticleBriefSchema))
    stories = ma.List(fields.Nested(ShortBriefSchema))
    magazines = ma.List(fields.Nested(MagazineBriefSchema))
    people = ma.List(fields.Nested(PersonBriefSchema))
    type = fields.Nested(TagTypeSchema)


class IssueContributorSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Issue contributor schema for person contributions. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Contributor
    person = fields.Nested(PersonBriefSchema(only=('id', 'name', 'alt_name')))
    role = fields.Nested(ContributorRoleSchema)
    description = fields.String()
    real_person = fields.Nested(PersonBriefSchema(
        only=('id', 'name', 'alt_name')))


class MagazineSimpleSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Magazine schema with only id and name. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Magazine
        fields = ('id', 'name')


class IssueContributionSchema(ma.SQLAlchemyAutoSchema):  # type: ignore
    """ Issue schema for person contributions with minimal fields. """
    class Meta:
        """ Metadata for SQLAlchemyAutoSchema. """
        model = Issue
        fields = ('id', 'type', 'number', 'number_extra', 'count', 'year',
                  'cover_number', 'image_src', 'pages', 'size', 'link',
                  'notes', 'title', 'contributors', 'magazine')

    contributors = ma.List(fields.Nested(IssueContributorSchema))
    magazine = fields.Nested(MagazineSimpleSchema)
    size = fields.Nested(PublicationSizeBriefSchema)
