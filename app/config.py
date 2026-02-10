""" Configuration classes. """
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    """ Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    # SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BOOKCOVER_DIR = '/static/images/books/'
    PERSONIMG_DIR = '/static/images/people/'
    MAGAZINECOVER_IMG = '/static/images/magazinse/'
    ENV = os.environ.get('FLASK_ENV') or 'debug'


class DevConfig(Config):
    """ Development configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'suomisf.db')
    BOOKCOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/mep/src/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = \
        '/home/mep/src/suomisf/app/static/images/magazines/'


class ProdConfig(Config):
    """ Production configuration class."""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite://' + os.path.join(basedir, 'suomisf.db')
    BOOKCOVER_SAVELOC = '/home/Makistos/mysite/app/static/images/books/'
    PERSONIMG_SAVELOC = \
        '/home/Makistos/mysite/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = \
        '/home/Makistos/mysite/suomisf/app/static/images/magazines/'


class StagingConfig(Config):
    """ Staging configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite://' + os.path.join(basedir, 'suomisf.db')
    BOOKCOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/mep/src/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = \
        '/home/mep/src/suomisf/app/static/images/magazines/'


class TestConfig(Config):
    """ Testing configuration class for API tests."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'postgresql://test_user:test_pass@localhost:5432/suomisf_test'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key-not-for-production'
    JWT_SECRET_KEY = 'test-jwt-secret-key'
    BOOKCOVER_SAVELOC = '/tmp/suomisf_test/images/books/'
    PERSONIMG_SAVELOC = '/tmp/suomisf_test/images/people/'
    MAGAZINECOVER_SAVELOC = '/tmp/suomisf_test/images/magazines/'
