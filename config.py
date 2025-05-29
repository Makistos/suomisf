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
    MAGAZINECOVER_IMG = '/static/images/magazinse/'
    ENV = os.environ.get('FLASK_ENV') or 'debug'


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
