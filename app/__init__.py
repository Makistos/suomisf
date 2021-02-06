from app import (orm_decl, routes, routes_article, routes_books,
                 routes_editions, routes_issue, routes_magazine, routes_person,
                 routes_publisher, routes_series, routes_stories, routes_works)
import logging
#from flask_debugtoolbar import DebugToolbarExtension
import os
from logging.handlers import RotatingFileHandler

from config import Config
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

#from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
if app.config['ENV'] == "production":
    app.config.from_object("config.ProdConfig")
elif app.config['ENV'] == 'staging':
    app.config.from_object("config.StagingConfig")
else:
    app.config.from_object("config.DevConfig")
print(f'ENV is set to {app.config["ENV"]}.')
app.static_folder = 'static'
db = SQLAlchemy(app)
#migrate = Migrate()
login = LoginManager(app)
bootstrap = Bootstrap(app)
app.debug = True
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True
#csrf = CSRFProtect(app)
WTF_CSRF_CHECK_DEFAULT = False


# This has to be here, not at the top of application or it won't start!

#toolbar = DebugToolbarExtension(app)

if not app.debug and not app.testing:
    if app.config['LOG_TO_STDOUT']:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
    else:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/suomisf.log',
                                           maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('SuomiSF startup')
