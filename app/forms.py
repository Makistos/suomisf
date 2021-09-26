from wtforms.fields.core import FieldList, FormField
from app.route_helpers import new_session
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                     IntegerField, SelectField, HiddenField, FieldList,
                     TextAreaField, SelectMultipleField, widgets, Form)
from wtforms.validators import (DataRequired, InputRequired, ValidationError,
                                EqualTo, Optional)
from app.orm_decl import PersonLink, User, Person
from app import db
from typing import Any


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class LoginForm(FlaskForm):
    username = StringField('Käyttäjätunnus', validators=[DataRequired()])
    password = StringField('Salasana', validators=[DataRequired()])
    remember_me = BooleanField('Muista minut')
    submit = SubmitField('Kirjaudu')


def validate_username(self, username):
    session = new_session()
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


class SearchBooksForm(FlaskForm):
    authorname = StringField('Kirjoittaja', validators=[Optional()])
    title = StringField('Kirjan nimi', validators=[Optional()])
    orig_title = StringField('Alkukielinen&nbsp;nimi',
                             validators=[Optional()])
    pubyear_start = IntegerField('Painovuosi', validators=[
        Optional()])
    pubyear_end = IntegerField('Painovuosi', validators=[
        Optional()])
    origyear_start = IntegerField('Julkaisuvuosi', validators=[
                                  Optional()])
    origyear_end = IntegerField('Julkaisuvuosi', validators=[
                                Optional()])
    genre = SelectField('Genre', coerce=int)
    nationality = SelectField('Kansallisuus', coerce=int)
    type = SelectField('Tyyppi', coerce=int)
    submit = SubmitField('Hae')


class SearchStoryForm(FlaskForm):
    authorname = StringField('Kirjoittaja', validators=[Optional()])
    title = StringField('Novellin nimi', validators=[Optional()])
    orig_title = StringField('Alkukielinen nimi', validators=[Optional()])
    origyear_start = IntegerField('Julkaisuvuosi', validators=[
                                  Optional()])
    origyear_end = IntegerField('Julkaisuvuosi', validators=[
                                Optional()])
    submit = SubmitField('Hae')

###
# Data entry forms
###


class ArticleForm(FlaskForm):
    id = HiddenField('id')
    title = StringField('Otsikko')
    author = StringField('Kirjoittaja')
    tags = StringField('Aihetunnisteet')
    submit = SubmitField('Tallenna')


class BookseriesForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Nimi')
    orig_name = StringField('Alkukielinen nimi')
    important = BooleanField('Merkittävä')
    submit = SubmitField('Tallenna')


class EditionForm(FlaskForm):
    id = HiddenField('id')
    # workid = HiddenField('workid')
    title = StringField('Nimeke', validators=[DataRequired()])
    subtitle = StringField('Alaotsikko', validators=[Optional()])
    # editors = StringField('Toimittaja')
    pubyear = IntegerField('Julkaisuvuosi', validators=[Optional()])
    # language = StringField('Kieli', validators=[Optional()])
    # publisher = StringField('Kustantaja', validators=[DataRequired(
    #    message='Kustantaja on pakollinen tieto')])
    # translators = StringField('Kääntäjä')
    editionnum = IntegerField('Painos')
    version = IntegerField('Laitos', validators=[Optional()])
    isbn = StringField('ISBN', validators=[Optional()])
    # pubseries = StringField('Kustantajan sarja')
    pubseriesnum = IntegerField('Sarjan numero', validators=[Optional()])
    pages = IntegerField('Sivuja', validators=[Optional()])
    size = IntegerField('Koko', validators=[Optional()])
    # cover = SelectField('Kansi')
    binding = IntegerField('Sidonta', validators=[Optional()])
    dustcover = IntegerField('Ylivetokansi', validators=[Optional()])
    coverimage = IntegerField('Kuvakansi', validators=[Optional()])
    # format = SelectField('Tyyppi')
    # size = SelectField('Koko', coerce=str)
    description = TextAreaField('Kuvaus', validators=[Optional()])
    # artist = StringField('Taiteilija')
    misc = StringField('Muuta', validators=[Optional()])
    imported_string = StringField('Lähde', validators=[Optional()])
    # source = StringField('Lähde')
    # image_src = StringField('Kuva')
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
    number = IntegerField('Numero')
    number_extra = StringField('Numeron tarkenne')
    count = IntegerField('Juokseva numero')
    year = IntegerField('Vuosi')
    cover_number = StringField('Kansinumero')
    image_src = StringField('Kansikuva')
    pages = IntegerField('Sivuja')
    link = StringField('Linkki')
    notes = TextAreaField('Kommentit')
    title = StringField('Otsikko')
    submit = SubmitField('Tallenna')


class MagazineForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Nimi')
    issn = StringField('Issn')
    publisher = StringField('Kustantaja', validators=[
                            DataRequired(message='Kustantaja on pakollinen tieto')])
    description = TextAreaField('Kuvaus')
    link = StringField('Linkki')
    submit = SubmitField('Tallenna')


class NewWorkForm(FlaskForm):
    id = HiddenField('id')
    title = StringField('Nimi', validators=[DataRequired(
        message='Teoksen nimi on pakollinen tieto')])
    subtitle = StringField('Alaotsikko')
    orig_title = StringField('Alkuperäinen nimi')
    pubyear = IntegerField('Julkaisuvuosi', validators=[Optional()])
    language = StringField('Kieli')
    bookseriesnum = StringField('Sarjanumero')
    bookseriesorder = IntegerField(
        'Järjestys sarjassa', validators=[Optional()])
    misc = StringField('Muuta')
    submit = SubmitField('Tallenna')


class PersonLinkForm(Form):
    link = StringField('Linkki')
    description = StringField('Kuvaus')


class PersonForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Kirjailjanimi', validators=[InputRequired()])
    alt_name = StringField('Vaihtoehtoinen nimen muoto')
    fullname = StringField('Koko nimi')
    first_name = StringField('Etunimi')
    last_name = StringField('Sukunimi')
    dob = IntegerField('Syntymävuosi', validators=[Optional()])
    dod = IntegerField('Kuolinvuosi', validators=[Optional()])
    image_attr = StringField('Kuvan lähde', validators=[Optional()])
    bio = TextAreaField('Kuvaus', validators=[Optional()])
    bio_src = StringField('Kuvauksen lähde', validators=[Optional()])
    links = FieldList(FormField(PersonLinkForm), min_entries=1)
    submit = SubmitField('Tallenna')

    # def validate_name(form: Any, field: Any) -> Any:
    #     session = new_session()
    #     other_person = session.query(Person)\
    #                           .filter(Person.name == field.data)\
    #                           .first()
    #     if other_person:
    #         raise ValidationError('Järjestelmässä jo henkilö tällä nimellä')


class PublisherForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Koko nimi')
    name = StringField('Nimi', validators=[DataRequired()])
    fullname = StringField('Koko nimi')
    submit = SubmitField('Tallenna')


class PubseriesForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('Koko nimi')
    name = StringField('Nimi', validators=[
                       DataRequired()])
    publisher = StringField('Julkaisija', validators=[DataRequired()])
    important = BooleanField('Merkittävä')
    submit = SubmitField('Tallenna')


class StoryForm(FlaskForm):
    id = HiddenField('id')
    hidden_work_id = HiddenField('work_id')
    #hidden_edition_id = HiddenField('edition_id')
    #hidden_issue_id = HiddenField('issue_id')
    authors = SelectMultipleField(
        'Kirjoittajat', choices=[], validate_choice=False, coerce=int, default=0)
    title = StringField('Nimi', validators=[DataRequired()])
    orig_title = StringField('Alkuperäinen nimi', validators=[Optional()])
    pubyear = IntegerField('Julkaisuvuosi', validators=[Optional()])
    submit = SubmitField('Tallenna')


class WorkLinkForm(Form):
    link = StringField('Linkki')
    description = StringField('Kuvaus')


class WorkForm(FlaskForm):
    id = HiddenField('id')
    work_id = HiddenField('work_id')
    hidden_author_id = HiddenField('author_id')
    title = StringField('Nimeke', validators=[DataRequired()])
    subtitle = StringField('Alaotsikko')
    orig_title = StringField('Alkuperäinen nimi')
    type = IntegerField('Tyyppi', validators=[Optional()])
    pubyear = IntegerField('Julkaisuvuosi', validators=[Optional()])
    language = StringField('Kieli')
    bookseriesnum = StringField('Sarjanumero')
    bookseriesorder = IntegerField(
        'Järjestys sarjassa', validators=[Optional()])
    # genre = MultiCheckboxField('Genret')
    misc = StringField('Muuta')
    image_src = StringField('Kuva')
    description = TextAreaField('Kuvaus')
    source = StringField('Lähde')
    links = FieldList(FormField(WorkLinkForm), min_entries=1)
    submit = SubmitField('Tallenna')


class WorkAuthorForm(FlaskForm):
    author = StringField('Kirjoittaja', validators=[DataRequired()])
    submit = SubmitField('Lisää')


class WorkStoryForm(FlaskForm):
    title = StringField('Nimi', validators=[DataRequired()])
    submit_story = SubmitField('Lisää')
