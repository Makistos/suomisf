import logging
# from flask_debugtoolbar import DebugToolbarExtension
import os

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
db_url = app.config['SQLALCHEMY_DATABASE_URI']
print(f'Db: {db_url}')
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
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True
# csrf = CSRFProtect(app)
WTF_CSRF_CHECK_DEFAULT = False

from app import (api, api_articles, api_awards,  # noqa
                 api_bookseries,
                 api_changes, api_countries, api_issues, api_magazines,
                 api_editions,
                 api_kirjasampo,
                 api_people, api_publishers, api_pubseries,
                 api_roles,
                 api_shorts, api_tags,
                 api_users, api_wikimedia,
                 api_wishlist, api_works, api_stats, api_pageview)

# This has to be here, not at the top of application or it won't start!
# toolbar = DebugToolbarExtension(app)

# Uncomment the following line to enable SQLAlchemy query logging
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

if not app.testing:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s in "
        "%(module)s:%(funcName)s():%(lineno)d — %(message)s"
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Logging initialised")
