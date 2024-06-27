import os

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.pymongo import ModelView
from flask_admin.contrib.pymongo.filters import (
    BooleanEqualFilter,
    FilterEqual,
    FilterLike,
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
    is_admin = fields.BooleanField()
    joined_at = fields.DateTimeField()


class UserView(ModelView):
    column_list = (
        "user_id",
        "user_name",
        "user_fullname",
        "nickname",
        "is_admin",
        "joined_at",
    )
    column_filters = [
        FilterEqual("user_id", "User ID"),
        FilterLike("user_name", "User Name"),
        FilterLike("user_fullname", "User Full Name"),
        FilterLike("nickname", "Nickname"),
        BooleanEqualFilter("is_admin", "Is Admin"),
    ]
    column_sortable_list = ["joined_at"]
    column_default_sort = ("joined_at", True)
    form = UserForm


class JokeForm(form.Form):
    kind = fields.StringField()
    text = fields.StringField()
    file_id = fields.StringField()
    accepted = fields.BooleanField()
    visible = fields.BooleanField()
    creator_nickname = fields.StringField()


class JokeView(ModelView):
    column_list = (
        "kind",
        "text",
        "file_id",
        "accepted",
        "visible",
        "creator_id",
        "creator_nickname",
        "created_at",
    )
    column_filters = [
        FilterEqual("kind", "Kind"),
        FilterLike("text", "Text"),
        FilterLike("creator_nickname", "Creator Nickname"),
        BooleanEqualFilter("accepted", "Accepted"),
        BooleanEqualFilter("visible", "Visible"),
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


class RecurringForm(form.Form):
    chat_id = fields.IntegerField()
    chat_type = fields.StringField()
    created_by_user_id = fields.IntegerField()
    interval = fields.StringField()
    created_at = fields.DateTimeField()


class RecurringView(ModelView):
    column_list = (
        "chat_id",
        "chat_type",
        "created_by_user_id",
        "interval",
        "created_at",
    )
    column_filters = [
        FilterEqual("created_by_user_id", "Created by User ID"),
        FilterEqual("chat_id", "Chat ID"),
        FilterEqual("chat_type", "Chat Type"),
        FilterEqual("interval", "Interval"),
    ]
    column_sortable_list = ["created_at"]
    column_default_sort = ("created_at", True)
    form = RecurringForm


if __name__ == "__main__":
    admin = Admin(app, url="/")
    admin.add_view(UserView(db["users"]))
    admin.add_view(JokeView(db["jokes"]))
    admin.add_view(JokeViewView(db["joke_views"]))
    admin.add_view(RecurringView(db["recurrings"]))
    admin.add_view(ActivityView(db["activities"]))

    app.run(host="0.0.0.0", port=5000, debug=True)
