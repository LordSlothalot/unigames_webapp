#This file is for specifying forms
from app import db_manager
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextField, validators, TextAreaField, SelectMultipleField, widgets
from wtforms.validators import DataRequired, Length, EqualTo, Email
from wtforms.fields.html5 import EmailField
# from app.routes import User

import pdoc

#get all tags from the db
all_roles = db_manager.mongo.db.roles.find()
#get all tag parameters
#all_tag_params = db_manager.mongo.db.
#get all attributes
all_attirb = db_manager.mongo.db.attrib_options.find()

#login form
class LoginForm(FlaskForm):
    """
    Form for user login
    """

    email = EmailField('Email', validators = [DataRequired(), Email()])
    password = PasswordField("Password", validators = [DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Login")


class RegistrationForm(FlaskForm):
    """
    Form for user registration
    """

    display_name = TextField('Display Name', validators = [DataRequired()])
    first_name = TextField('First Name')
    last_name = TextField('Last Name')
    email = EmailField('Email', validators = [DataRequired(), Email()])
    password = PasswordField("Password", validators = [DataRequired()])
    password2 = PasswordField("Repeat Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField('Register')
    
    
class UpdatePasswordForm(FlaskForm):
    """
    Form for user password reset
    """
    password = PasswordField("Password", validators = [DataRequired()])
    password2 = PasswordField("Repeat Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField('Register')

    # def validate_username(self, username):
    #     User.objects()
	
class UpdateForm(FlaskForm):
    """
    Form for users to update their details
    """
    display_name = TextField('Display Name', validators = [DataRequired()]) 
    first_name = TextField('First Name')
    last_name = TextField('Last Name')
    email = EmailField('Email', validators = [DataRequired(), Email()])
    role = SelectField('Role', choices=[(role['name'], role['name']) for role in all_roles])
    submit = SubmitField('Update')
    delete = SubmitField('Delete')
    
class CreateUserForm(FlaskForm):
    """
    Form to create a new user account
    """
    display_name = TextField('Display Name', validators = [DataRequired()])
    first_name = TextField('First Name')
    last_name = TextField('Last Name')
    email = EmailField('Email', validators = [DataRequired(), Email()])
    password = PasswordField("Password", validators = [DataRequired()])
    password2 = PasswordField("Repeat Password", validators=[DataRequired(), EqualTo("password")])
    role = SelectField('Role', choices=[(role['name'], role['name']) for role in all_roles])
    submit = SubmitField('Register')
    
class UpdateRoleForm(FlaskForm):
    """
    Form to update a user role
    """
    name = TextField('Name', validators = [DataRequired()]) 
    priority = TextField('Priority', validators = [DataRequired()])
    can_view_hidden = BooleanField('Can View Hidden')
    can_edit_items = BooleanField('Can Edit Items')
    can_edit_users = BooleanField('Can Edit Users')
    submit = SubmitField('Update')
    delete = SubmitField('Delete')

#new entry form
class newEntryForm(FlaskForm):
    title = StringField('Title',[validators.DataRequired()])
    description = TextAreaField('Description')
    selection = SelectMultipleField('Attach multiple tags')
    submit = SubmitField('Save')

#add a tag form
class addTagForm(FlaskForm):
    selection = SelectField('Add a tag')
    submit = SubmitField('Save')

#create a tag form
class createTagForm(FlaskForm):
    name = StringField('New tag', [validators.DataRequired()])
    #paramValue = StringField('Tag paramter value (corresponds with the parameter type above)')
    submit = SubmitField('Add')

#add tag's implications form
class addTagParentImplForm(FlaskForm):
    select_parent = SelectField('Select its parent tag')
    submit = SubmitField('Add implying tag')

#add tag's implications form
class addTagSiblingImplForm(FlaskForm):
    select_sibling = SelectField('Select its sibling tag')
    submit = SubmitField('Add implied tag')

#add tag's implications form
class addTagImplForm(FlaskForm):
    select_child = SelectField('Select its child tag')
    submit = SubmitField('Add implied tag')

#update attribute for an item form
class updateAttribForm(FlaskForm):
    attrib_value = TextAreaField('New attribute value')
    submit = SubmitField('Update')


#add an implication rul
class addRuleForm(FlaskForm):
    parent = SelectField('Parent tag')
    child = SelectField('Child tag')
    submit = SubmitField('Save implication')
