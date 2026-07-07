""" Configuration file. """
import os
# from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    """ Base configuration class. """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_TOKEN')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    # SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BOOKCOVER_DIR = '/static/images/books/'
    MAGAZINECOVER_DIR = '/static/images/magazines/'
    PERSONIMG_DIR = '/static/images/people/'
    MAGAZINECOVER_IMG = '/static/images/magazines/'
    ENV = os.environ.get('FLASK_ENV') or 'debug'

    # Outbound email (password reset). MAIL_BACKEND 'log' writes the message
    # to the application log instead of sending, so the feature works before
    # an SMTP server is configured. Set MAIL_BACKEND=smtp once SMTP is ready.
    MAIL_BACKEND = os.environ.get('MAIL_BACKEND', 'log')
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '25'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', '') == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or None
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or None
    MAIL_FROM = os.environ.get('MAIL_FROM', 'noreply@sofistes.net')
    # Base URL of the frontend, used to build the reset link in the email.
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    # How long a password-reset link stays valid (seconds).
    PASSWORD_RESET_MAX_AGE = int(
        os.environ.get('PASSWORD_RESET_MAX_AGE', '3600'))


class DevConfig(Config):  # pylint: disable=too-few-public-methods
    """ Development configuration class. """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_TOKEN')
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'suomisf.db')
    BOOKCOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/mep/src/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = \
        '/home/mep/src/suomisf/app/static/images/magazines/'


class ProdConfig(Config):  # pylint: disable=too-few-public-methods
    """ Production configuration class. """
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_TOKEN')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite://' + os.path.join(basedir, 'suomisf.db')
    BOOKCOVER_SAVELOC = '/home/mep/suomisf/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/mep/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = '/home/mep/suomisf/app/static/images/magazines/'


class StagingConfig(Config):  # pylint: disable=too-few-public-methods
    """ Staging configuration class. """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_TOKEN')
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite://' + os.path.join(basedir, 'suomisf.db')
    BOOKCOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/mep/src/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = \
        '/home/mep/src/suomisf/app/static/images/magazines/'


class TestingConfig(Config):  # pylint: disable=too-few-public-methods
    """ Testing configuration class. """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_TOKEN')
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_TEST') or \
        'sqlite://' + os.path.join(basedir, 'suomisf.db')
    BOOKCOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/mep/src/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = \
        '/home/mep/src/suomisf/app/static/images/magazines/'
