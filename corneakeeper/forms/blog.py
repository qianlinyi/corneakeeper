from flask_wtf import FlaskForm
from flask_ckeditor import CKEditorField
from wtforms import StringField, SubmitField, TextAreaField, HiddenField, SelectField
from wtforms.validators import DataRequired, Length, Email, Optional, URL, ValidationError
from corneakeeper.models import Category


class CommentForm(FlaskForm):
    author = StringField('Name', validators=[DataRequired(), Length(1, 30)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(1, 254)])
    site = StringField('Site', validators=[Optional(), URL(), Length(0, 255)])
    body = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField()


class UserCommentForm(CommentForm):
    author = HiddenField()
    email = HiddenField()
    site = HiddenField()


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 60)])
    category = SelectField('Category', coerce=int, default=1)
    body = CKEditorField('Body', validators=[DataRequired()])
    submit = SubmitField()

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.category.choices = [(category.id, category.name)
                                 for category in Category.query.order_by(Category.name).all()]


class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 30)])
    submit = SubmitField()

    def validate_name(self, field):
        if Category.query.filter_by(name=field.data).first():
            raise ValidationError('Name already in use.')


# class CommentForm(FlaskForm):
#     author = StringField('Name', validators=[DataRequired(), Length(1, 30)])
#     email = StringField('Email', validators=[DataRequired(), Email(), Length(1, 254)])
#     site = StringField('Site', validators=[Optional(), URL(), Length(0, 255)])
#     body = TextAreaField('Comment', validators=[DataRequired()])
#     submit = SubmitField()


class LinkForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 30)])
    url = StringField('URL', validators=[DataRequired(), URL(), Length(1, 255)])
    submit = SubmitField()
