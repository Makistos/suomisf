from flask.helpers import url_for
from marshmallow import Schema, fields
from app import ma
from app.orm_decl import (Article, Edition, Issue, Magazine, Person, PublicationSize, Publisher,
                          ShortStory, Tag, User, Work, Article)


class TagSchema(ma.SQLAlchemySchema):
    class Meta:
        fields = ('id', 'name')


class PersonSchemaSimple(ma.SQLAlchemySchema):
    class Meta:
        fields = ('id', 'name', 'alt_name', 'image_src')


class PersonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Person


class ArticleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Article
    tags = ma.List(ma.Nested(TagSchema))
    author_rel = ma.List(fields.Nested(PersonSchema))


class ShortSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ShortStory
    authors = ma.List(fields.Nested(PersonSchema))

    id = fields.Int()
    orig_title = fields.String()
    pubyear = fields.Int()
    title = fields.String()


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
    editors = ma.List(fields.Nested(PersonSchema))
    size = fields.Nested(PublicationSizeSchema)
    articles = ma.auto_field()
    stories = ma.auto_field()


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
