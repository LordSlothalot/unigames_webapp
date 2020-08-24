#This file is for specifying forms
from app import db_manager
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextField, validators
from wtforms.validators import DataRequired, Length
from wtforms.fields.html5 import EmailField

#get all tags from the db
all_tags = db_manager.mongo.db.tags.find()

#login form
class LoginForm(FlaskForm):
    email = EmailField('Email', [validators.DataRequired(), validators.Email()])
    password = PasswordField("Password", validators = [DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Login")

#new entry form
class newEntryForm(FlaskForm):
    title = StringField('Title',[validators.DataRequired()])
    author = StringField('Author',[validators.DataRequired()])
    Description = TextField('Description')
    submit = SubmitField('Save')

#add a tag form
class addTagForm(FlaskForm):
    selection = SelectField('Add a tag', choices=[(tag['name'], tag['name']) for tag in all_tags])
    submit = SubmitField('Save')