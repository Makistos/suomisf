from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError, EqualTo
from app.orm_decl import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
