import os

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.pymongo import ModelView
from pymongo import MongoClient
from wtforms import fields, form

db_uri = os.environ["MONGODB_URI"]
client = MongoClient(db_uri.rsplit("/", 1)[0])
db = client[db_uri.rsplit("/", 1)[1]]


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]


class UserForm(form.Form):
    user_id = fields.IntegerField()
    user_name = fields.StringField()
    user_fullname = fields.StringField()
    nickname = fields.StringField()
    joined_at = fields.DateTimeField()


class UserView(ModelView):
    column_list = (
        "user_id",
        "user_name",
        "user_fullname",
        "nickname",
        "joined_at",
    )
    column_editable_list = ["user_name", "user_fullname", "nickname"]
    column_searchable_list = ["user_id", "user_name", "user_fullname", "nickname"]
    form = UserForm


class JokeForm(form.Form):
    kind = fields.StringField()
    text = fields.StringField()
    voice_file_id = fields.StringField()
    accepted = fields.BooleanField()
    creator_nickname = fields.StringField()


class JokeView(ModelView):
    column_list = (
        "kind",
        "text",
        "voice_file_id",
        "accepted",
        "creator_id",
        "creator_nickname",
        "created_at",
    )
    column_filters = ["kind", "accepted"]
    column_searchable_list = ["creator_id", "creator_nickname"]
    column_editable_list = ["text", "accepted", "creator_nickname"]
    form = JokeForm


class JokeViewForm(form.Form):
    kind = fields.StringField()
    text = fields.StringField()
    voice_file_id = fields.StringField()
    accepted = fields.BooleanField()
    creator_nickname = fields.StringField()


class JokeViewView(ModelView):
    column_list = (
        "user_id",
        "joke_id",
        "score",
        "viewed_at",
        "scored_at",
    )
    column_filters = ["score"]
    column_searchable_list = ["user_id", "joke_id"]
    column_editable_list = ["score"]
    form = JokeViewForm


if __name__ == "__main__":
    admin = Admin(app, url="/")
    admin.add_view(UserView(db["users"]))
    admin.add_view(JokeView(db["jokes"]))
    admin.add_view(JokeViewView(db["joke_views"]))

    app.run(host="0.0.0.0", port=5000, debug=True)
