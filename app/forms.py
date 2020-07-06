from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField,\
IntegerField, SelectField, HiddenField, RadioField, TextAreaField,\
SelectMultipleField
from wtforms.validators import DataRequired, ValidationError, EqualTo, Optional
from app.orm_decl import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db

class LoginForm(FlaskForm):
    username = StringField('Käyttäjätunnus', validators=[DataRequired()])
    password = StringField('Salasana', validators=[DataRequired()])
    remember_me = BooleanField('Muista minut')
    submit = SubmitField('Kirjaudu')


def validate_username(self, username):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    user = session.query(User).filter_by(name=username.data).first()
    if user is not None:
        raise ValidationError('Valitse toinen käyttäjätunnus.')

class RegistrationForm(FlaskForm):
    username = StringField('Käyttäjätunnus', validators=[DataRequired()])
    password = PasswordField('Salasana', validators=[DataRequired()])
    password2 = PasswordField('Salasana uudestaan',
            validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Rekisteröidy')


class UserForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Koko nimi')
    name = StringField('Käyttäjätunnus', validators=[DataRequired()])
    password = PasswordField('Salasana')
    password2 = PasswordField('Salasana uudestaan',
            validators=[EqualTo('password')])
    is_admin = BooleanField('Ylläpitäjä')
    submit = SubmitField('Päivitä')


class WorkForm(FlaskForm):
    id = HiddenField('id')
    author = StringField('Kirjoittaja(t)', validators=[DataRequired()])
    title = StringField('Nimeke', validators=[DataRequired()])
    subtitle = StringField('Alaotsikko')
    orig_title = StringField('Alkuperäinen nimi')
    editors = StringField('Toimittaja(t)')
    pubyear = IntegerField('Julkaisuvuosi', validators=[Optional()])
    language = StringField('Kieli')
    bookseries = StringField('Kirjasarja')
    bookseriesnum = StringField('Sarjanumero')
    bookseriesorder = IntegerField('Järjestys sarjassa')
    genre = StringField('Genre')
    collection = RadioField('Kokoelma')
    misc = StringField('Muuta')
    image_src = StringField('Kuva')
    description = TextAreaField('Kuvaus')
    source = StringField('Lähde')
    submit = SubmitField('Tallenna')

class WorkAuthorForm(FlaskForm):
    author = StringField('Kirjoittaja', validators=[DataRequired()])
    submit = SubmitField('Lisää')

class EditionForm(FlaskForm):
    id = HiddenField('id')
    title = StringField('Nimeke', validators=[DataRequired()])
    editors = StringField('Toimittaja(t)')
    pubyear = IntegerField('Julkaisuvuosi', validators=[Optional()])
    language = StringField('Kieli')
    publisher = StringField('Kustantaja', validators=[DataRequired(
        message ='Kustantaja on pakollinen tieto')])
    translators = StringField('Kääntäjä(t)')
    edition = IntegerField('Painos')
    isbn = StringField('ISBN')
    pubseries = SelectField('Kustantajan sarja', coerce=str)
    pubseriesnum = IntegerField('Sarjan numero', validators=[Optional()])
    pages = IntegerField('Sivuja')
    misc = StringField('Muuta')
    source = StringField('Lähde')
    image_src = StringField('Kuva')
    submit = SubmitField('Tallenna')

class PersonForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Kirjailjanimi')
    alt_name = StringField('Koko nimi')
    first_name = StringField('Etunimi')
    last_name = StringField('Sukunimi')
    image_src = StringField('Kuva')
    dob = IntegerField('Syntymävuosi', validators=[Optional()])
    dod = IntegerField('Kuolinvuosi', validators=[Optional()])
    nationality = StringField('Kansallisuus')
    other_names = StringField('Vaihtoehtoiset nimen kirjoitusasut')
    tags = StringField('Aihetunnisteet')
    submit = SubmitField('Tallenna')

class PublisherForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Koko nimi')
    name = StringField('Nimi', validators=[DataRequired()])
    fullname = StringField('Koko nimi')
    submit = SubmitField('Tallenna')

class PubseriesForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Koko nimi')
    name = StringField('Nimi', validators=[DataRequired()])
    publisher = StringField('Julkaisija', validators=[DataRequired()])
    important = BooleanField('Merkittävä')
    submit = SubmitField('Tallenna')

class BookseriesForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Koko nimi')
    name = StringField('Nimi')
    important = BooleanField('Merkittävä')
    submit = SubmitField('Tallenna')

class SearchForm(FlaskForm):
    work_name = StringField('Nimi')
    work_origname = StringField('Alkup. nimi')
    work_pubyear_after = IntegerField('Julk. vuosi aikaisintaan')
    work_pubyear_before = IntegerField('Julk. vuosi viimeistään')
    work_genre = SelectMultipleField('Genre')
    work_tag = StringField('Aihetunnistin')

    edition_name = StringField('Nimi')
    edition_pubyear_after = IntegerField('Julk. vuosi aikaisintaan')
    edition_pubyear_before = IntegerField('Julk. vuosi viimeistään')
    edition_editionnum = IntegerField('Painos')

    author_name = StringField('Nimi')
    author_dob_after = IntegerField('Syntymävuosi aikaisintaan')
    author_dob_before = IntegerField('Syntymävuosi viimeistään')
    author_nationality = SelectMultipleField('Kansallisuus')
    author_alive = SelectField('Elossa')

    submit = SubmitField('Hae')
