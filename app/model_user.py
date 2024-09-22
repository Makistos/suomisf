from marshmallow import fields, Schema

from app import ma
class UserbooksSchema(ma.SQLAlchemySchema):
    description = ma.String()
    edition_id = ma.Integer()
    title = ma.String()
    version = ma.String()
    editionnum = ma.String()
    pubyear = ma.Integer()
    value = ma.Integer()
    author_str = ma.String()
    publisher_id = ma.Integer()
    publisher_name = ma.String()

