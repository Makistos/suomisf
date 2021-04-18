import os
from dotenv import dotenv_values

#basedir = os.path.abspath(os.path.dirname(__file__))
settings = dotenv_values('.env')


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    #SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BOOKCOVER_DIR = '/static/images/books/'
    PERSONIMG_DIR = '/static/images/people/'
    MAGAZINECOVER_IMG = '/static/images/magazinse/'


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #    'sqlite:///' + os.path.join(basedir, 'suomisf.db')
    SQLALCHEMY_DATABASE_URI = settings['DATABASE_URI']
    BOOKCOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/mep/src/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/magazines/'


class ProdConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False
    USER = os.environ.get('USER') or 'nobody'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector:// {settings['USER']}: {settings['PASSWORD']}@settings['DATABASE_URI']"
    #SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{USER}:{SECRET_KEY}@localhost/suomisf"
    BOOKCOVER_SAVELOC = '/home/Makistos/mysite/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/Makistos/mysite/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = '/home/Makistos/mysite/suomisf/app/static/images/magazines/'


class StagingConfig(Config):
    USER = os.environ.get('USER') or 'nobody'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector:// {settings['USER']}: {settings['PASSWORD']}@settings['DATABASE_URI']"
    # SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{USER}:{SECRET_KEY}@localhost/suomisf"
    BOOKCOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/books/'
    PERSONIMG_SAVELOC = '/home/mep/src/suomisf/app/static/images/people/'
    MAGAZINECOVER_SAVELOC = '/home/mep/src/suomisf/app/static/images/magazines/'
