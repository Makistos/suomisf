from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, ValidationError, EqualTo
from app.orm_decl import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db

class LoginForm(FlaskForm):
    username = StringField('Käyttäjätunnus', validators=[DataRequired()])
    password = StringField('Salasana', validators=[DataRequired()])
    remember_me = BooleanField('Muista minut')
    submit = SubmitField('Kirjaudu')


class RegistrationForm(FlaskForm):
    username = StringField('Käyttäjätunnus', validators=[DataRequired()])
    password = PasswordField('Salasana', validators=[DataRequired()])
    password2 = PasswordField('Salasana uudestaan',
            validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Rekisteröidy')

    def validate_username(self, username):
        engine = create_engine('sqlite:///suomisf.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        user = session.query(User).filter_by(name=username.data).first()
        if user is not None:
            raise ValidationError('Valitse toinen käyttäjätunnus.')

class BookForm(FlaskForm):
    title = StringField('Nimi')
    author = StringField('Kirjoittaja')
    translator = StringField('Kääntäjä')
    pubyear = IntegerField('Julkaisuvuosi')
    origname = StringField('Alkuperäinen nimi')
    origpubyear = IntegerField('Alkuperäinen julkaisuvuosi')
    edition = IntegerField('Painos')
    publisher = StringField('Kustantaja')
    genre = StringField('Genre')
    rest = StringField('Muuta')
    submit = SubmitField('Lisää')

class PersonForm(FlaskForm):
    name = StringField('Koko nimi')
    firstname = StringField('Etunimi')
    lastname = StringField('Sukunimi')
    dob = IntegerField('Syntymävuosi')
    dod = IntegerField('Kuolinvuosi')
    birthplace = StringField('Kansallisuus')
    submit = SubmitField('Lisää')

class PublisherForm(FlaskForm):
    name = StringField('Nimi', validators=[DataRequired()])
    fullname = StringField('Koko nimi')
    submit = SubmitField('Lisää')

class PubseriesForm(FlaskForm):
    name = StringField('Nimi', validators=[DataRequired()])
    publisher = StringField('Julkaisija', validators=[DataRequired()])
    important = BooleanField('Merkittävä')
    submit = SubmitField('Lisää')

class BookseriesForm(FlaskForm):
    name = StringField('Nimi')
    important = BooleanField('Merkittävä')
    submit = SubmitField('Lisää')

