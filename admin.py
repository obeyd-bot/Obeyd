from pathlib import Path
import os

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

from models import Base, Joke, Like

if __name__ == "__main__":
    app = Flask(__name__)
    app.config["FLASK_ADMIN_SWATCH"] = "cerulean"
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{os.path.join(Path(__file__).parent.resolve(), 'db.sqlite')}"
    )

    db = SQLAlchemy(model_class=Base)

    db.init_app(app)

    admin = Admin(app, name="obeyd", template_mode="bootstrap3")
    admin.add_view(ModelView(Joke, db.session))
    admin.add_view(ModelView(Like, db.session))

    app.run()
