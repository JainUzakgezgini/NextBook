from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, DateField, EmailField, IntegerField, PasswordField, StringField, SubmitField, TextAreaField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, Optional, Regexp, ValidationError,
)

from app import db
from app.models import User


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        description="English letters, numbers and . _ - only. No spaces.",
        validators=[
            DataRequired(),
            Length(min=3, max=40),
            Regexp(
                r"^[A-Za-z0-9_.-]+$",
                message="Only English letters (a-z), numbers and . _ - are allowed. "
                        "Spaces and letters like ş, ğ, ü, ö, ç, ı don't work here.",
            ),
        ],
    )
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password",
        description="At least 8 characters.",
        validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")],
    )
    confirm = PasswordField(
        "Repeat password", validators=[DataRequired(), EqualTo("password", message="Passwords don't match.")]
    )
    submit = SubmitField("Create account")

    def validate_username(self, field):
        if db.session.scalar(db.select(User).filter_by(username=field.data)):
            raise ValidationError("That username is taken.")

    def validate_email(self, field):
        if db.session.scalar(db.select(User).filter_by(email=field.data.lower())):
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me logged in")
    submit = SubmitField("Log in")


class SeriesForm(FlaskForm):
    series_name = StringField("Series name", validators=[Optional(), Length(max=200)])
    series_index = IntegerField("This is book number", validators=[Optional(), NumberRange(min=1, max=999)])
    total_books_in_series = IntegerField("Books in the series", validators=[Optional(), NumberRange(min=1, max=999)])
    next_release_date = DateField("Next book comes out on", validators=[Optional()])
    submit = SubmitField("Save series info")

    def validate_total_books_in_series(self, field):
        if field.data and self.series_index.data and field.data < self.series_index.data:
            raise ValidationError("The series can't have fewer books than this book's number.")


class NoteForm(FlaskForm):
    content = TextAreaField(
        "Your note",
        validators=[DataRequired(message="Write something first."), Length(max=4000)],
    )
    is_cliffhanger = BooleanField("Mark as a cliffhanger")
    submit = SubmitField("Save note")
