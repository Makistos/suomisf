from flask.helpers import url_for
from marshmallow import Schema, fields
from app import ma
from app.orm_decl import (Article, Edition, Issue, Magazine, Person, Publisher,
                          ShortStory, Tag, User, Work)


class TagSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Tag


class PersonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Person


class ArticleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Article


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
    #magazine = fields.Nested(MagazineSchema)


class MagazineSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Magazine
        include_fk = True
    issues = ma.List(fields.Nested(IssueSchema))


class PublisherSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Publisher


class ShortSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ShortStory
    authors = PersonSchema(many=True)

    id = fields.Int()
    orig_title = fields.String()
    pubyear = fields.Int()
    title = fields.String()


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User


class WorkSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Work
