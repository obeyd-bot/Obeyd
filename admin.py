import os

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

from models import Base, Joke, Like, SeenJoke, User

if __name__ == "__main__":
    app = Flask(__name__)
    app.config["FLASK_ADMIN_SWATCH"] = "cerulean"
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["SQLALCHEMY_DATABASE_URI"]

    db = SQLAlchemy(model_class=Base)

    db.init_app(app)

    admin = Admin(app, name="obeyd", template_mode="bootstrap3")
    admin.add_view(ModelView(Joke, db.session))
    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(Like, db.session))
    admin.add_view(ModelView(SeenJoke, db.session))

    app.run(host="0.0.0.0")
