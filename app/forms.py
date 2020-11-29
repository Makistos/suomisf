from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField,\
    IntegerField, SelectField, HiddenField, RadioField, TextAreaField,\
    SelectMultipleField, widgets
from wtforms.validators import DataRequired, ValidationError, EqualTo, Optional
from app.orm_decl import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


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


class SearchForm(FlaskForm):
    work_name = StringField('Nimi')
    work_origname = StringField('Alkup. nimi')
    work_pubyear_after = IntegerField(
        'Alkuperäinen julkaisuvuosi aikaisintaan')
    work_pubyear_before = IntegerField(
        'Alkuperäinen julkaisuvuosi viimeistään')
    work_genre = SelectMultipleField('Genre', default=0)
    work_tag = StringField('Aihetunnistin')

    edition_pubyear_after = IntegerField(
        'Suomalaisen julkaisun vuosi aikaisintaan')
    edition_pubyear_before = IntegerField(
        'Suomalaisen julkaisun vuosi viimeistään')
    edition_editionnum = IntegerField('Painos')

    author_name = StringField('Kirjailijan nimi')
    author_dob_after = IntegerField('Kirjailijan syntymävuosi aikaisintaan')
    author_dob_before = IntegerField('Kirjailijan syntymävuosi viimeistään')
    author_nationality = SelectMultipleField(
        'Kirjailijan kansallisuus', default=0)

    submit = SubmitField('Hae')

###
# Data entry forms
###


class ArticleForm(FlaskForm):
    id = HiddenField('id')
    title = StringField('Otsikko')
    tags = StringField('Aihetunnisteet')


class BookseriesForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Koko nimi')
    name = StringField('Nimi')
    important = BooleanField('Merkittävä')
    submit = SubmitField('Tallenna')


class EditionForm(FlaskForm):
    id = HiddenField('id')
    workid = HiddenField('workid')
    title = StringField('Nimeke', validators=[DataRequired()])
    subtitle = StringField('Alaotsikko')
    editors = StringField('Toimittaja')
    pubyear = IntegerField('Julkaisuvuosi', validators=[Optional()])
    language = StringField('Kieli')
    publisher = StringField('Kustantaja', validators=[DataRequired(
        message='Kustantaja on pakollinen tieto')])
    translators = StringField('Kääntäjä')
    edition = IntegerField('Painos')
    version = IntegerField('Laitos', validators=[Optional()])
    isbn = StringField('ISBN')
    pubseries = StringField('Kustantajan sarja')
    pubseriesnum = IntegerField('Sarjan numero', validators=[Optional()])
    pages = IntegerField('Sivuja', validators=[Optional()])
    cover = SelectField('Kansi')
    binding = SelectField('Sidonta')
    format = SelectField('Tyyppi')
    size = SelectField('Koko', coerce=str)
    description = TextAreaField('Kuvaus')
    #artist = StringField('Taiteilija')
    misc = StringField('Muuta')
    source = StringField('Lähde')
    image_src = StringField('Kuva')
    submit = SubmitField('Tallenna')


class EditionTranslatorForm(FlaskForm):
    id = HiddenField('id')
    translator = StringField('Nimi')
    submit_tr = SubmitField('Tallenna')


class EditionEditorForm(FlaskForm):
    id = HiddenField('id')
    editor = StringField('Nimi')
    submit_ed = SubmitField('Tallenna')


class IssueForm(FlaskForm):
    id = HiddenField('id')
    magazine = StringField('Lehti')
    editor = StringField('Päätoimittaja')
    number = IntegerField('Numero')
    number_extra = StringField('Numeron tarkenne')
    count = IntegerField('Juokseva numero')
    year = IntegerField('Vuosi')
    image_src = StringField('Kansikuva')
    pages = IntegerField('Sivuja')
    size = SelectField('Koko', coerce=str)
    link = StringField('Linkki')
    notes = TextAreaField('Kommentit')
    submit = SubmitField('Tallenna')


class MagazineForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Nimi')
    issn = StringField('Issn')
    publisher = StringField('Kustantaja', validators=[
                            DataRequired(message='Kustantaja on pakollinen tieto')])
    description = TextAreaField('Kuvaus')
    image_src = StringField('Logo')
    banner_src = StringField('Otsakekuva')
    submit = SubmitField('Tallenna')


class PersonForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Kirjailjanimi')
    alt_name = StringField('Koko nimi')
    first_name = StringField('Etunimi')
    last_name = StringField('Sukunimi')
    image_src = StringField('Kuva')
    image_attr = StringField('Kuvan lähde')
    dob = IntegerField('Syntymävuosi', validators=[Optional()])
    dod = IntegerField('Kuolinvuosi', validators=[Optional()])
    nationality = StringField('Kansallisuus')
    other_names = StringField('Vaihtoehtoiset nimen kirjoitusasut')
    tags = StringField('Aihetunnisteet')
    bio = TextAreaField('Kuvaus', validators=[Optional()])
    bio_src = StringField('Kuvauksen lähde')
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


class StoryForm(FlaskForm):
    id = HiddenField('id')
    author = StringField('Kirjoittaja', validators=[DataRequired])
    copy_author = BooleanField('Sama kuin teoksella')
    title = StringField('Nimi')
    orig_title = StringField('Alkuperäinen nimi')
    language = StringField('Kieli')
    pubyear = IntegerField('Julkaisuvuosi')
    submit_story = SubmitField('Tallenna')


class WorkForm(FlaskForm):
    id = HiddenField('id')
    work_id = HiddenField('work_id')
    author = StringField('Kirjoittaja', validators=[DataRequired()])
    title = StringField('Nimeke', validators=[DataRequired()])
    subtitle = StringField('Alaotsikko')
    orig_title = StringField('Alkuperäinen nimi')
    editors = StringField('Toimittaja(t)')
    pubyear = IntegerField('Julkaisuvuosi', validators=[Optional()])
    language = StringField('Kieli')
    bookseries = StringField('Kirjasarja')
    bookseriesnum = StringField('Sarjanumero')
    bookseriesorder = IntegerField('Järjestys sarjassa')
    collection = BooleanField('Novellikokoelma')
    genre = SelectMultipleField('Genret')
    #genre = MultiCheckboxField('Genret')
    misc = StringField('Muuta')
    image_src = StringField('Kuva')
    description = TextAreaField('Kuvaus')
    source = StringField('Lähde')
    submit = SubmitField('Tallenna')


class WorkAuthorForm(FlaskForm):
    author = StringField('Kirjoittaja', validators=[DataRequired()])
    submit = SubmitField('Lisää')


class WorkStoryForm(FlaskForm):
    title = StringField('Nimi', validators=[DataRequired()])
    submit_story = SubmitField('Lisää')
