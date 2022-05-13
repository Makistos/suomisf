from unicodedata import category
from marshmallow import Schema, fields
from app import ma
from app.orm_decl import (Article, Award, AwardCategory, Awarded, BindingType, Bookseries, ContributorRole, Country, Edition,
                          EditionImage, Genre, Issue, Log, Magazine, Person, PersonLink,
                          PublicationSize, Publisher, Pubseries, ShortStory, Tag, User,
                          Work, Article, StoryType, WorkLink, Format)

# Brief schemas should not include any relationships to other
# tables. These exists to get around the issue with Python that
# you can't have two entities using each other. It is impossible
# to get the one defined first to "see" the other. Plus this will
# minimize data transfer. So brief schemas is used by other schemas
# to implement nested data structures.

# Some exceptions are required. Therefore ordering of these
# definitions might well be critical.


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User


class LogSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Log
    user = fields.Nested(UserSchema)


class ErrorSchema(Schema):
    code = fields.Int(required=True,)
    message = fields.String(required=True,)


class BindingBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = BindingType


class FormatBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Format


class BookseriesBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Bookseries


class EditionImageBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = EditionImage


class PersonLinkBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PersonLink


class PublicationSizeBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PublicationSize


class StoryTypeBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = StoryType


class TagBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Tag


class WorkLinkBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = WorkLink


class ContributorRoleBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ContributorRole


class CountryBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Country


class GenreBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Genre


class PersonBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Person
    id = fields.Number()
    name = fields.String()
    alt_name = fields.String()
    fullname = fields.String()
    image_src = fields.String()
    dob = fields.Number()
    dod = fields.Number()
    roles = fields.Pluck("self", "name", many=True)
    nationality = fields.String(attribute='nationalityname')
    workcount = fields.Number()
    storycount = fields.Number()


class WorkEditionBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Edition

    editors = ma.List(fields.Nested(PersonBriefSchema))
    translators = ma.List(fields.Nested(PersonBriefSchema))
    images = ma.List(fields.Nested(EditionImageBriefSchema))


class WorkBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Work
    id = fields.Number()
    title = fields.String()
    orig_title = fields.String()
    author_str = fields.String()
    editions = ma.List(fields.Nested(WorkEditionBriefSchema))
    authors = ma.List(fields.Nested(PersonBriefSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    bookseries = fields.Nested(BookseriesBriefSchema)


class EditionBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Edition

    work = ma.List(fields.Nested(WorkBriefSchema))
    editors = ma.List(fields.Nested(PersonBriefSchema))
    images = ma.List(fields.Nested(EditionImageBriefSchema))


class MagazineBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Magazine


class IssueBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Issue
        #include_fk = True
    magazine = fields.Nested(MagazineBriefSchema)


class ShortBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ShortStory

    #id = fields.Int()
    #title = fields.String()
    #orig_title = fields.String()
    #pubyear = fields.Int()
    authors = ma.List(fields.Nested(PersonBriefSchema))
    type = fields.Nested(StoryTypeBriefSchema)
    issues = ma.List(fields.Nested(IssueBriefSchema))
    editions = ma.List(fields.Nested(EditionBriefSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))


class ArticleBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Article
    id = fields.Int()
    title = fields.String()
    author_rel = ma.List(fields.Nested(PersonBriefSchema))
    excerpt = fields.String()


class AwardBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Award


class AwardCategorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = AwardCategory


class PublisherBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Publisher


class PubseriesBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Pubseries


# Full schemas. Mainly used to be returned as the main object
# type in API calls. This makes is super easy to retrieve all
# relevant data for certain object types.

class AwardedSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Awarded
    award = fields.Nested(AwardBriefSchema)
    person = fields.Nested(PersonBriefSchema)
    work = fields.Nested(WorkBriefSchema)
    category = fields.Nested(AwardCategorySchema)
    story = fields.Nested(ShortBriefSchema)


class BookseriesSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Bookseries
    works = ma.List(fields.Nested(WorkBriefSchema))


class TagSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Tag

    works = ma.List(fields.Nested(WorkBriefSchema))
    articles = ma.List(fields.Nested(ArticleBriefSchema))
    stories = ma.List(fields.Nested(ShortBriefSchema))
    magazines = ma.List(fields.Nested(MagazineBriefSchema))
    people = ma.List(fields.Nested(PersonBriefSchema))


class EditionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
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


class WorkSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Work
    editions = ma.List(fields.Nested(EditionSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    bookseries = fields.Nested(BookseriesBriefSchema)
    tags = ma.List(fields.Nested(TagBriefSchema))
    language_name = fields.Nested(CountryBriefSchema)
    authors = ma.List(fields.Nested(PersonBriefSchema))
    links = ma.List(fields.Nested(WorkLinkBriefSchema))
    stories = ma.List(fields.Nested(ShortBriefSchema))
    translators = ma.List(fields.Nested(PersonBriefSchema))
    awards = ma.List(fields.Nested(AwardedSchema))


class ArticleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Article
    id = fields.Int()
    title = fields.String()
    person = fields.String()
    author_rel = ma.List(fields.Nested(PersonBriefSchema))
    tags = ma.List(fields.Nested(TagBriefSchema))
    issue = fields.Nested(IssueBriefSchema)
    excerpt = fields.String()


class PersonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Person
    real_names = ma.List(fields.Nested(PersonBriefSchema))
    aliases = ma.List(fields.Nested(PersonBriefSchema))
    links = ma.List(fields.Nested(PersonLinkBriefSchema))
    works = ma.List(fields.Nested(WorkSchema))
    stories = ma.List(fields.Nested(ShortBriefSchema))
    edits = ma.List(fields.Nested(EditionSchema))
    translations = ma.List(fields.Nested(EditionSchema))
    chief_editor = ma.List(fields.Nested(IssueBriefSchema))
    articles = ma.List(fields.Nested(ArticleSchema))
    magazine_stories = ma.List(fields.Nested(ShortBriefSchema))
    translated_stories = ma.List(fields.Nested(ShortBriefSchema))
    appears_in = ma.List(fields.Nested(ArticleBriefSchema))
    personal_awards = ma.List(fields.Nested(AwardBriefSchema))
    nationality = fields.Nested(CountryBriefSchema)
    awarded = ma.List(fields.Nested(AwardedSchema))


class ShortSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ShortStory

    authors = ma.List(fields.Nested(PersonBriefSchema))
    translators = ma.List(fields.Nested(PersonBriefSchema))
    tags = ma.List(fields.Nested(TagSchema))
    issues = ma.List(fields.Nested(IssueBriefSchema))
    works = ma.List(fields.Nested(WorkBriefSchema))
    editions = ma.List(fields.Nested(EditionBriefSchema))
    genres = ma.List(fields.Nested(GenreBriefSchema))
    type = fields.Nested(StoryTypeBriefSchema)


class IssueSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Issue
        include_fk = True
    magazine = ma.auto_field()
    editors = ma.List(fields.Nested(PersonBriefSchema))
    size = fields.Nested(PublicationSizeBriefSchema)
    articles = ma.List(fields.Nested(ArticleBriefSchema()))
    stories = ma.List(fields.Nested(ShortBriefSchema()))
    magazine = fields.Nested(MagazineBriefSchema)


class MagazineSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Magazine
        include_fk = True
    issues = ma.auto_field()  # ma.List(fields.Nested(IssueSchema))
    publisher = fields.Nested(PublisherBriefSchema)
