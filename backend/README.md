# Environment setup

## By Pipenv
run `pip install pipenv`to install pipenv

Ensure you are inside the backend folder before preceding.

run `pipenv shell` to load into the virtual environment. This creates a virtual environment if one doesn't already exist

run `pipenv install` to install dependencies

run `flask run` to run the server

if you get the following error
> Error: Could not locate Flask application. You did not provide the FLASK_APP environment variable.

run `export FLASK_APP=app/routes.py` and try again

> Note: you have to run `pipenv shell` every time you open a new terminal

## By Virtualenv
install Virtualenv to your host machine

run `virtualenv venv` to create a virtual environment

run `source venv/bin/active` to activate the virtual environment

install all packages via command `pip install requirements.txt`

run `flask run` to run the server


#Adding New Permissions

Permissions are handled on a page by page basis, in the routes.py file. 

The line "@login_required(perm="can_view_hidden")" determines the permission required for the page, in this case "can_view_hidden"

To add a new permission, open the roles.py file and add the new permission in the permissions class.

E.g. CanEditItems = "can_edit_items"

Then, in forms.py, under the UpdateRoleForm, add the new permission. 

Finally, in routes.py, under editrole, add a new line for the permission in the update section.

E.g. "'permissions.can_edit_items': form.can_edit_items.data,"

Once that is done, you should be able to add the permission to restrict access to pages.