#This file is for specifying forms

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextField, validators
from wtforms.validators import DataRequired, Length, EqualTo, Email
from wtforms.fields.html5 import EmailField
# from app.routes import User

#login form
class LoginForm(FlaskForm):
    email = EmailField('Email', validators = [DataRequired(), Email()])
    password = PasswordField("Password", validators = [DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Login")

class RegistrationForm(FlaskForm):
    first_name = TextField('First Name', validators = [DataRequired()])
    last_name = TextField('Last Name', validators = [DataRequired()])
    email = EmailField('Email', validators = [DataRequired(), Email()])
    password = PasswordField("Password", validators = [DataRequired()])
    password2 = PasswordField("Repeat Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField('Register')

    # def validate_username(self, username):
    #     User.objects()
	
class UpdateForm(FlaskForm):
    first_name = TextField('First Name', validators = [DataRequired()])
    last_name = TextField('Last Name', validators = [DataRequired()])
    email = EmailField('Email', validators = [DataRequired(), Email()])
    role = TextField('Role', validators = [DataRequired()])
    submit = SubmitField('Update')