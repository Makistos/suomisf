from re import M
from flask.helpers import url_for
from marshmallow import Schema, fields
from app import ma
from app.orm_decl import (Article, ContributorRole, Country, Edition, Issue, Magazine, Person, PublicationSize, Publisher,
                          ShortStory, Tag, User, Work, Article)


class TagSchema(ma.SQLAlchemySchema):
    class Meta:
        fields = ('id', 'name')


class TagBriefSchema(ma.SQLAlchemySchema):
    class Meta:
        fields = ['name']


class ContributorRoleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ContributorRole
    id = fields.Number()
    name = fields.String()


class ContributorRoleBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        fields = ['name']


class CountrySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Country
    id = fields.Number()
    name = fields.String()


class CountryBriefSchema(ma.SQLAlchemySchema):
    class Meta:
        fields = ['name']


class PersonBriefSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Person
    id = fields.Number()
    name = fields.String()
    alt_name = fields.String()
    image_src = fields.String()
    dob = fields.Number()
    dod = fields.Number()
    roles = fields.Pluck("self", "name", many=True)
    nationality = fields.Pluck("self", "name")


class PersonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Person


class MagazineBriefSchema(ma.SQLAlchemySchema):
    class Meta:
        fields = ('id', 'name')


class IssueBriefSchema(ma.SQLAlchemySchema):
    class Meta:
        fields = ('id', 'cover_number', 'title', 'magazine')
    magazine = fields.Nested(MagazineBriefSchema)


class ArticleBriefSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Article
    id = fields.Int()
    title = fields.String()
    author_rel = ma.List(fields.Nested(PersonBriefSchema))
    excerpt = fields.String()
    # issue = fields.Nested(IssueBrief)


class ArticleSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Article
    id = fields.Int()
    title = fields.String()
    person = fields.String()
    author_rel = ma.List(fields.Nested(PersonBriefSchema))
    tags = ma.List(fields.Nested(TagSchema))
    issue = fields.Nested(IssueBriefSchema)
    excerpt = fields.String()


class ShortBriefSchema(ma.SQLAlchemySchema):
    class Meta:
        model = ShortStory

    id = fields.Int()
    title = fields.String()
    orig_title = fields.String()
    pubyear = fields.Int()
    authors = ma.List(fields.Nested(PersonBriefSchema))


class ShortSchema(ma.SQLAlchemySchema):
    class Meta:
        model = ShortStory

    id = fields.Int()
    title = fields.String()
    orig_title = fields.String()
    pubyear = fields.Int()
    authors = ma.List(fields.Nested(PersonBriefSchema))
    translators = ma.List(fields.Nested(PersonBriefSchema))
    tags = ma.List(fields.Nested(TagSchema))
    issues = ma.List(fields.Nested(IssueBriefSchema))
    # works = ma.List(fields.Nested(WorkBriefSchema))
    # editions = ma.List(fields.Nested(EditionBriefSchema))
    # genres = ma.List(fields.Nested(GenreSchema))


class PublicationSizeSchema(ma.SQLAlchemySchema):
    class Meta:
        fields = ('id', 'name')


class EditionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Edition


class ErrorSchema(Schema):
    code = fields.Int(required=True,)
    message = fields.String(required=True,)


class IssueSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Issue
        include_fk = True
    magazine = ma.auto_field()
    editors = ma.List(fields.Nested(PersonBriefSchema))
    size = fields.Nested(PublicationSizeSchema)
    articles = ma.List(fields.Nested(ArticleBriefSchema()))
    stories = ma.List(fields.Nested(ShortBriefSchema()))
    magazine = fields.Nested(MagazineBriefSchema)


class PublisherSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Publisher


class MagazineSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Magazine
        include_fk = True
    issues = ma.auto_field()  # ma.List(fields.Nested(IssueSchema))
    publisher = fields.Nested(PublisherSchema)


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User


class WorkSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Work
