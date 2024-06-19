import os

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.pymongo import ModelView
from flask_admin.contrib.pymongo.filters import (
    BooleanEqualFilter,
    FilterLike,
    FilterEqual,
)
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
    column_filters = [
        FilterEqual("user_id", "User ID"),
        FilterLike("user_name", "User Name"),
        FilterLike("user_fullname", "User Full Name"),
        FilterLike("nickname", "Nickname"),
    ]
    column_sortable_list = ["joined_at"]
    column_default_sort = ("joined_at", True)
    form = UserForm


class JokeForm(form.Form):
    kind = fields.StringField()
    text = fields.StringField()
    file_id = fields.StringField()
    accepted = fields.BooleanField()
    creator_nickname = fields.StringField()


class JokeView(ModelView):
    column_list = (
        "kind",
        "text",
        "file_id",
        "accepted",
        "creator_id",
        "creator_nickname",
        "created_at",
    )
    column_filters = [
        FilterEqual("kind", "Kind"),
        FilterLike("text", "Text"),
        FilterLike("creator_nickname", "Creator Nickname"),
        BooleanEqualFilter("accepted", "Accepted"),
    ]
    column_sortable_list = ["created_at"]
    column_default_sort = ("created_at", True)
    form = JokeForm


class JokeViewForm(form.Form):
    kind = fields.StringField()
    text = fields.StringField()
    file_id = fields.StringField()
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
    column_filters = [
        FilterEqual("user_id", "User ID"),
        FilterEqual("joke_id", "Joke ID"),
        FilterEqual("score", "Score"),
    ]
    column_sortable_list = ["score", "viewed_at", "scored_at"]
    column_default_sort = ("score", True)
    form = JokeViewForm


class ActivityForm(form.Form):
    kind = fields.StringField()
    user_id = fields.IntegerField()
    user_name = fields.StringField()
    chat_type = fields.StringField()
    chat_id = fields.IntegerField()
    chat_name = fields.StringField()
    created_at = fields.DateTimeField()


class ActivityView(ModelView):
    column_list = (
        "kind",
        "user_id",
        "user_name",
        "chat_type",
        "chat_id",
        "chat_name",
        "data",
        "created_at",
    )
    column_filters = [
        FilterEqual("kind", "Kind"),
        FilterEqual("user_id", "User ID"),
        FilterLike("user_name", "User Name"),
        FilterEqual("chat_type", "Chat Type"),
        FilterEqual("chat_id", "Chat ID"),
        FilterLike("chat_name", "Chat Name"),
    ]
    column_sortable_list = ["created_at"]
    column_default_sort = ("created_at", True)
    form = ActivityForm


if __name__ == "__main__":
    admin = Admin(app, url="/")
    admin.add_view(UserView(db["users"]))
    admin.add_view(JokeView(db["jokes"]))
    admin.add_view(JokeViewView(db["joke_views"]))
    admin.add_view(ActivityView(db["activities"]))

    app.run(host="0.0.0.0", port=5000, debug=True)
