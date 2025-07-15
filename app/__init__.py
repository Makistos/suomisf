import logging
# from flask_debugtoolbar import DebugToolbarExtension
import os
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_cors import CORS
from flask_jwt_extended import JWTManager

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv('.env', override=True)
config_name = os.getenv('FLASK_ENV', 'development')
if 'ENV' not in app.config:
    app.config['ENV'] = config_name
# app.config['SQLALCHEMY_RECORD_QUERIES'] = True
# app.config['SQLALCHEMY_ECHO'] = True
if os.environ.get('TESTING'):
    app.config.from_object("config.TestingConfig")
elif app.config['ENV'] == "production":
    app.config.from_object("config.ProdConfig")
elif app.config['ENV'] == 'staging':
    app.config.from_object("config.StagingConfig")
else:
    app.config.from_object("config.DevConfig")
# print(f'Db: {app.config["SQLALCHEMY_DATABASE_URI"]}')
# print(f'ENV is set to {app.config["ENV"]}.')
# print(f"Config is {app.config}")
db_url = app.config['SQLALCHEMY_DATABASE_URI']
jwt_secret_key = app.config['JWT_SECRET_KEY']
app.static_folder = 'static'
db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-type'

# migrate = Migrate()
login = LoginManager(app)
bootstrap = Bootstrap(app)
app.debug = True
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True
# csrf = CSRFProtect(app)
WTF_CSRF_CHECK_DEFAULT = False

from app import (api, api_articles, api_awards,  # noqa
                 api_bookseries,
                 api_changes, api_countries, api_issues, api_magazines,
                 api_editions,
                 api_people, api_publishers, api_pubseries,
                 api_roles,
                 api_shorts, api_tags,
                 api_users,
                 api_wishlist, api_works)

# This has to be here, not at the top of application or it won't start!
# toolbar = DebugToolbarExtension(app)

# Uncomment the following line to enable SQLAlchemy query logging
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

if not app.debug and not app.testing:
    if app.config['LOG_TO_STDOUT']:
        FORMAT = "%(levelname)5s in %(module)s:%(funcName)s():%(lineno)s -> " \
                 "%(message)s"
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        # app.logger.addHandler(stream_handler)
    else:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/suomisf.log',
                                           maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.DEBUG)
    FORMAT = "[%(asctime)]%(levelname)5s in %(module)s:%(funcName)s():" \
             "%(lineno)s -> %(message)s"
    logging.basicConfig()

    # app.logger.addHandler(file_handler)
else:
    FORMAT = "%(levelname)5s in %(module)s:%(funcName)s():%(lineno)s -> " \
             "%(message)s"
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logging.basicConfig(format=FORMAT)
    app.logger = logger
