from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_wtf import CSRFProtect
from flask_mail import Mail
import os

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login = LoginManager(app)
login.login_view = 'login'

csrf = CSRFProtect(app)
Bootstrap(app)

mail = Mail(app)

app.config.CSV_FILE_PATH = os.path.abspath(os.path.dirname(__file__) + '/files/data.csv')

from app import models, routes

from app.handlers import Handlers
import click

@app.cli.command("create-user")
@click.option('-u', '--username', default="admin", help='New user username')
@click.option('-e', '--email', help='New user email')
def create_user(username, email):
    user = Handlers.create_user(username, email)
    if user:
        print("User created successfully. Password sent to email.")
    else:
        print("Failed to create user.")
