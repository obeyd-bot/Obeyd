from pathlib import Path
import os

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

from models import Base, Joke, Like

if __name__ == "__main__":
    db_host = os.environ["DB_HOST"]
    db_port = os.environ["DB_PORT"]
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]

    app = Flask(__name__)
    app.config["FLASK_ADMIN_SWATCH"] = "cerulean"
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}",
    )

    db = SQLAlchemy(model_class=Base)

    db.init_app(app)

    admin = Admin(app, name="obeyd", template_mode="bootstrap3")
    admin.add_view(ModelView(Joke, db.session))
    admin.add_view(ModelView(Like, db.session))

    app.run(host="0.0.0.0")
