from functools import wraps

import json
from bson.errors import InvalidId
from bson.objectid import ObjectId
from flask import render_template, url_for, redirect, request, flash, Response
from flask_login import current_user, login_user, logout_user
from gridfs import NoFile
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app import app, db_manager, login_manager
from app.database_impl.attrib_options import AttributeOption, PictureAttribute, SingleLineStringAttribute, \
    MultiLineStringAttribute
from app.database_impl.items_instances import Item, Instance
from app.database_impl.tags import Tag, TagReference

from bson.objectid import ObjectId
from app.forms import newEntryForm, addTagForm, createTagForm, addTagImplForm, \
    updateAttribForm, LoginForm, RegistrationForm, UpdateForm, addRuleForm, \
    addTagParentImplForm, addTagSiblingImplForm, UpdateRoleForm, CreateUserForm, UpdatePasswordForm

from app.search_parser import search_string_to_mongodb_query, SearchStringParseError
from flask_pymongo import PyMongo
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash
from functools import wraps

from app.tables import UserTable
from app.database_impl.users import User
from app.database_impl.roles import Role

from flask_paginate import Pagination, get_page_parameter, get_page_args
tags_collection = db_manager.mongo.db.tags
attrib_collection = db_manager.mongo.db.attrib_options
mongo = db_manager.mongo




# -------------------------------------------
#     Public pages
# -------------------------------------------
@app.route('/')
@app.route('/home')
def home():
    """
    Home route endpoint

    Returns:
        Renders the home.html user page template
    """
    recent_items = []
    for item in db_manager.mongo.db.items.find():
        recent_items.append(item)
    recent_items.reverse()
    recent_items = recent_items[:6]
    return render_template('user-pages/home.html', recent_items=recent_items, Item=Item, name_attrib_option=db_manager.name_attrib, tags_collection=tags_collection)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route endpoint. 
    This allows users to login to their account.

    Parameters
    ----------
        GET:/login
        POST:/login

    Returns
    -------
        Redirects to the admin dashboard if the user is authenticated
        Redirects to the change password page if the user has a temporary password
        Redirects to the login page if the login was unsuccessful
    """
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        find_user = mongo.db.users.find_one({"email": email})
        print("find_user: ", find_user)
        if User.login_valid(db_manager.mongo, email, password):
            loguser = User.from_dict(find_user)
            login_user(loguser, remember=form.remember_me.data)
            flash('You have been logged in!', 'success')
            if loguser.temp:
                flash('You have a temporary password, please update it.')
                return redirect(url_for('changepw'))
            else:
                return redirect(url_for('admin'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            return redirect(url_for('login'))
    return render_template('user-pages/login.html', form=form)


@app.route('/logout')
def logout():
    """
    Logout route endpoint. 
    This allows users to logout of their account

    Returns
    -------
        Redirects to the login page
    """
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('login'))

@app.route('/changepw', methods=['GET', 'POST'])
@login_required
def changepw():
    """
    Change password route endpoint. 
    This allows users to change their password

    Parameters
    ----------
        GET:/changepw
        POST:/changepw

    Returns
    -------
        Redirects to the home page if the password was changed successfully
        Redirects to the password change page if unsuccessful
    """
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        id = current_user.id
        password = generate_password_hash(form.password.data)
        mongo.db.users.update_one({'_id': ObjectId(id)},
                                      {"$set": {
                                            'password': password,
                                            'temp': False
                                      }
                                      })
        flash("Password updated successfully!")
        return redirect(url_for('home'))
    return render_template('user-pages/changepw.html', form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    """
    User registration route endpoint. 
    This allows users create a new account

    Parameters
    ----------
        GET:/register
        POST:/register

    Returns
    -------
        Redirects to the home page if the account was created successfully
        Redirects to the register page if registration failed
    """
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        display_name = form.display_name.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        password = generate_password_hash(form.password.data)
        find_by_email = User.search_for_by_email(db_manager.mongo, email)
        find_by_name = User.search_for_by_display_name(db_manager.mongo, display_name)
        if find_by_email is None and find_by_name is None:
            User.register(db_manager.mongo, display_name, email, password, first_name, last_name)
            flash(f'Account created for {form.email.data}!', 'success')
            return redirect(url_for('home'))
        else:
            if find_by_name is None: 
                flash(f'Account already exists for {form.email.data}!', 'success')
            else:
                flash(f'Account already exists for {form.display_name.data}!', 'success')
    return render_template('user-pages/register.html', title='Register', form=form)

@app.route('/library')
def library():
    """
    Item library route endpoint.

    Returns
    -------
        Renders the library page 
    """
    items = db_manager.mongo.db.items.find()
    items = [Item.from_dict(i) for i in items]

    for item in items:
        item.recalculate_implied_tags(db_manager.mongo)  # Again, thia is NOT be needed

    item_names = {item.id: item.get_attributes_by_option(db_manager.name_attrib)[0].value for item in items}
    item_images = {}
    for item in items:
        picture = item.get_attributes_by_option(db_manager.main_picture)
        if picture:
            item_images[item.id] = url_for('image', oid=str(picture[0].value))
        else:
            item_images[item.id] = url_for('static', filename='img/logo.png')  # TODO supply 'no-image' image?

    return render_template('user-pages/new-library.html', items=items, tags_collection=tags_collection,
                           item_names=item_names, item_images=item_images)


@app.route('/libarary/item_detail/<item_id>', methods=['GET', 'POST'])
def item_detail(item_id):
    """
    Item detail route endpoint. 
    This allows users to view the page for a specific item

    Parameters
    ----------
        GET:/item_detail/<item_id>
        POST:/item_detail/<item_id>

    Returns
    -------
        Renders the page for the item specified by `item_id`
    """
    item = db_manager.mongo.db.items.find_one({"_id": ObjectId(item_id)})
    if item is None:
        return page_not_found(404)
    item = Item.from_dict(item)

    if item.get_attributes_by_option(db_manager.main_picture):
        image_url = url_for('image', oid=str(item.get_attributes_by_option(db_manager.main_picture)[0].value))
    else:
        image_url = url_for('static', filename='img/logo.png')  # TODO supply 'no-image' image?

    return render_template('user-pages/item-detail.html', image_url=image_url, item=item, tags_collection=tags_collection, 
                                name_attribute=db_manager.name_attrib, description_attribute = db_manager.description_attrib)


@app.route('/events')
def events():
    """
    Events route endpoint. 
    This allows users to see the Unigames events

    Returns
    -------
        Renders the page for the Unigames events
    """
    return render_template('user-pages/events.html')

# Roleplaying page
@app.route('/roleplaying')
def roleplaying():
    """
    Roleplaying route endpoint. 
    This allows users to find imformation on roleplaying 

    Returns
    -------
        Renders the page for roleplaying
    """
    return render_template('user-pages/roleplaying.html')


@app.route('/committee')
def committee():
    """
    Committee route endpoint. 
    This allows users to see the Unigames committee members

    Returns
    -------
        Renders the page for the Unigames committee
    """
    return render_template('user-pages/committee.html')

# Lif members page
@app.route('/lifeMembers')
def lifeMembers():
    """
    Life members route endpoint. 
    This allows users to see members awarded with a life membership

    Returns
    -------
        Renders the page for the Unigames life members
    """
    return render_template('user-pages/lifeMembers.html')

# FAQ page
@app.route('/faq')
def faq():
    """
    FAQ route endpoint. 
    This allows users to see the Unigames frequently asked questions

    Returns
    -------
        Renders the page for the Unigames FAQ
    """
    return render_template('user-pages/faq.html')

# Constitution page
@app.route('/constitution')
def constitution():
    """
    Constitution route endpoint. 
    This allows users to see the Unigames constitution

    Returns
    -------
        Renders the page for the Unigames constitution
    """
    return render_template('user-pages/constitution.html')


@app.route('/operations')
def operations():
    """
    Operations route endpoint. 
    This allows users to see the Unigames operations, which contains information for the use of future and current committees

    Returns
    -------
        Renders the page for the Unigames operations
    """
    return render_template('user-pages/operations.html')

# needs to be implemented or deleted
@app.route('/forbidden')
def forbidden():
    """
    Forbidden route endpoint. 
    This page is rendered when unauthenticated users attempt to access restricted pages

    Returns
    -------
        Renders the forbidden page
    """
    return render_template('user-pages/forbidden.html')


@login_manager.unauthorized_handler
def unauthorized():
    """
    Handles unauthorised access to pages

    Returns
    -------
        Redirects to the login page if the user is not authenticated else, redirects to the forbidden page
    """
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('forbidden'))
    return 'Page not found r.'

    
def login_required(perm="ANY"):
    """
    Ensures users can only access pages when logged in
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if (perm != "ANY"):
                hasperm = False
                for r in current_user.role_ids:
                    roleperms = db_manager.mongo.db.roles.find_one({"_id": r})['permissions']
                    print(roleperms)
                    if roleperms[perm]:
                        hasperm = True
                if not hasperm:
                    return login_manager.unauthorized()
            return fn(*args, **kwargs)

        return decorated_view

    return wrapper

# -------------------------------------------
#     File and Image processing
# -------------------------------------------

# upload and view code taken and modified from here: https://gist.github.com/artisonian/492713
# needs refinement from here, but this is to give those who need it a head start
@app.route('/image/<oid>')
def image(oid):
    """
    Title: A simple GridFS server built with Flask
    Author: Leroy Campbell
    Date: 2010
    Availability: https://gist.github.com/artisonian/492713
    """
    try:
        file = db_manager.fs.get(ObjectId(oid))
        return Response(file, mimetype=file.content_type, direct_passthrough=True)
    except NoFile or InvalidId:
        return page_not_found(404)


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    """
    Title: A simple GridFS server built with Flask
    Author: Leroy Campbell
    Date: 2010
    Availability: https://gist.github.com/artisonian/492713
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image(): 
    """
    Title: A simple GridFS server built with Flask
    Author: Leroy Campbell
    Date: 2010
    Availability: https://gist.github.com/artisonian/492713
    """
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            oid = db_manager.fs.put(file, content_type=file.content_type, filename=filename)
            return redirect(url_for('image', oid=str(oid)))
    return '''
        <!DOCTYPE html>
        <html>
        <head>
        <title>Upload new file</title>
        </head>
        <body>
        <h1>Upload new file</h1>
        <form action="" method="post" enctype="multipart/form-data">
        <p><input type="file" name="file"></p>
        <p><input type="submit" value="Upload"></p>
        </form>
        <a href="%s">All files</a>
        </body>
        </html>
        ''' % url_for('images')


@app.route('/images')
def images():
    """
    Title: A simple GridFS server built with Flask
    Author: Leroy Campbell
    Date: 2010
    Availability: https://gist.github.com/artisonian/492713
    """
    files = db_manager.fs.find()
    file_list = "\n".join(['<li><a href="%s">%s</a></li>' % \
                           (url_for('image', oid=str(file._id)), file.name) \
                           for file in files])
    return '''
    <!DOCTYPE html>
    <html>
    <head>
    <title>Files</title>
    </head>
    <body>
    <h1>Files</h1>
    <ul>
    %s
    </ul>
    <a href="%s">Upload new file</a>
    </body>
    </html>
    ''' % (file_list, url_for('upload_image'))



# -------------------------------------------
#     Admin pages
# -------------------------------------------

@app.route('/admin', methods=['GET', 'POST'])
@login_required(perm="can_view_hidden")
def admin():
    """
    Admin route endpoint. 
    This allows users who have logged in to view the admin page

    Parameters
    ----------
        GET:/admin
        POST:/admin

    Returns
    -------
        Renders the admin home page
    """
    item_count = 0
    tag_count = 0
    user_count = 0
    tag_impl_count = 0
    recent_items = []
    for item in db_manager.mongo.db.items.find():
        item_count += 1
        recent_items.append(item)
    tags = db_manager.mongo.db.tags.find()
    recent_tags = []
    for tag in tags:
        tag_count += 1
        recent_tags.append(tag)
        if tag['implies']:
            tag_impl_count += 1
    for user in db_manager.mongo.db.Users.find():
        user_count +=1
    recent_items.reverse()
    recent_items = recent_items[:6]
    recent_tags.reverse()
    recent_tags = recent_tags[:6]
    return render_template('admin-pages/new-home.html', tags_collection=tags_collection, user_count=user_count, recent_items=recent_items, recent_tags=recent_tags,item_count=item_count, tag_count=tag_count, tag_impl_count=tag_impl_count, name_attrib_option=db_manager.name_attrib, Item=Item)

#### Following pages for User Management ####

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required(perm="can_view_hidden")
def adminusers():
    """
    Admin users route endpoint. 
    This allows authenticated users to view all users

    Parameters
    ----------
        GET:/admin/users
        POST:/admin/users

    Returns
    -------
        Renders the admin users home page
    """
    users = mongo.db.users.find()
    rolescursor = mongo.db.roles.find()
    rolesdic = {}
    for r in rolescursor:
        rolesdic[r['_id']] = r['name']
    return render_template('admin-pages/user-man/users.html', users=users, rolesdic=rolesdic)


@app.route('/admin/users/edit/<id>', methods=['GET', 'POST'])
@login_required(perm="can_view_hidden")
def edit(id):
    """
    Admin user edit route endpoint. 
    This allows authenticated users edit users

    Parameters
    ----------
        GET:/admin/users/edit/<id>
        POST:/admin/users/edit/<id>

    Returns
    -------
        Renders the user edit page
    """
    searcheduser = mongo.db.users.find_one({'_id': ObjectId(id)})
    rid = mongo.db.roles.find_one(searcheduser['role_ids'][0])
    rolename = rid['name']
    searcheduser['role'] = rolename

    if searcheduser:
        form = UpdateForm(**searcheduser)
        form.role.choices = [(role['name'], role['name']) for role in db_manager.mongo.db.roles.find()]
        if form.validate_on_submit():
            if form.delete.data:
                return redirect(url_for('deleteuser', id=id))
            print(Role.search_for_by_name(db_manager.mongo, form.role.data).id)
            mongo.db.users.update_one({'_id': ObjectId(id)},
                                      {"$set": {
                                          'display_name': form.display_name.data,
                                          'first_name': form.first_name.data,
                                          'last_name': form.last_name.data,
                                          'email': form.email.data,
                                          'role_ids': [Role.search_for_by_name(db_manager.mongo, form.role.data).id]
                                      }
                                      })
            flash('User updated successfully!')
            return redirect(url_for('adminusers'))
        return render_template('admin-pages/user-man/edit.html', form=form)
    else:
        return 'Error loading #{id}'.format(id=id)
    return render_template('admin-pages/user-man/edit.html', form=form)
    
    
@app.route('/admin/users/createuser', methods=['GET', 'POST'])
@login_required(perm="can_edit_users")
def createuser():
    """
    Admin create user route endpoint. 
    This allows users with the `can_edit_users` permission to create new users

    Parameters
    ----------
        GET:/admin/users/createuser
        POST:/admin/users/createuser

    Returns
    -------
        Renders the create user page
    """
    form = CreateUserForm()
    form.role.choices = [(role['name'], role['name']) for role in db_manager.mongo.db.roles.find()]
    if form.validate_on_submit():
        email = form.email.data
        display_name = form.display_name.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        password = generate_password_hash(form.password.data)
        role = form.role.data
        find_by_email = User.search_for_by_email(db_manager.mongo, email)
        find_by_name = User.search_for_by_display_name(db_manager.mongo, display_name)
        if find_by_email is None and find_by_name is None:
            User.register(db_manager.mongo, display_name, email, password, first_name, last_name, role, True)
            flash(f'Account created for {form.email.data}!', 'success')
            return redirect(url_for('adminusers'))
        else:
            if find_by_name is None: 
                flash(f'Account already exists for {form.email.data}!', 'success')
            else:
                flash(f'Account already exists for {form.display_name.data}!', 'success')
        return render_template('admin-pages/user-man/createuser.html', form=form)
    return render_template('admin-pages/user-man/createuser.html', form=form) 
 
@app.route('/admin/users/delete/<string:id>')
@login_required(perm="can_edit_users")
def deleteuser(id):
    """
    Delete user route endpoint. 
    This allows users with the `can_edit_users` permission to delete users

    Parameters
    ----------
        GET:/admin/users/delete/<string:id>
        POST:/admin/users/delete/<string:id>

    Returns
    -------
        Redirects to the admin user page if the user is deleted successfully, else return an error
    """
    searcheduser = mongo.db.users.find_one({'_id': ObjectId(id)})
    if searcheduser:
        mongo.db.users.delete_one({'_id': ObjectId(id)})
        flash('User deleted successfully!')
        return redirect(url_for('adminusers'))
    else:
        return 'Error loading #{id}'.format(id=id)
    
@app.route('/admin/users/roles')
@login_required(perm="can_view_hidden")
def roles():
    """
    User role route endpoint. 
    This allows users with the `can_view_hidden` permission to view user roles

    Parameters
    ----------
        GET:/admin/users/roles
        POST:/admin/users/roles

    Returns
    -------
        Renders the roles page
    """
    roles = mongo.db.roles.find()
    return render_template('admin-pages/user-man/roles.html', roles=roles)
    
@app.route('/admin/users/editrole/<id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_users")
def editrole(id):
    """
    Edit role route endpoint. 
    This allows users with the `can_edit_users` permission to edit user roles

    Parameters
    ----------
        GET:/admin/users/editrole/<id>
        POST:/admin/users/editrole/<id>

    Returns
    -------
        Renders the edit roles page
    """
    searchedrole = mongo.db.roles.find_one({'_id': ObjectId(id)})
    print(searchedrole)
    for key in searchedrole['permissions']:
        searchedrole[key] = searchedrole['permissions'][key]
    print(searchedrole)

    if searchedrole:
        if searchedrole['name'] == 'admin' or searchedrole['name'] == 'everyone':
            flash('Error: Cannot edit default roles')
            return redirect(url_for('roles'))
        form = UpdateRoleForm(**searchedrole)
        if form.validate_on_submit():
            if form.delete.data:
                return redirect(url_for('deleterole', id=id))
            mongo.db.roles.update_one({'_id': ObjectId(id)},
                                      {"$set": {
                                          'name': form.name.data,
                                          'priority': form.priority.data,
                                          'permissions.can_edit_items': form.can_edit_items.data,
                                          'permissions.can_edit_users': form.can_edit_users.data,
                                          'permissions.can_view_hidden': form.can_view_hidden.data
                                      }
                                      })
            flash('Role updated successfully!')
            return redirect(url_for('roles'))
        return render_template('admin-pages/user-man/editrole.html', form=form)
    else:
        return 'Error loading #{id}'.format(id=id)
    return render_template('admin-pages/user-man/editrole.html', form=form)
    
@app.route('/admin/users/deleterole/<string:id>')
@login_required(perm="can_edit_users")
def deleterole(id):
    """
    Delete role route endpoint. 
    This allows users with the `can_edit_users` permission to delete user roles

    Parameters
    ----------
        GET:/admin/users/deleterole/<string:id>
        POST:/admin/users/deleterole/<string:id>

    Returns
    -------
        Redirects to the roles page if the role was deleted successfully, else return an error
    """
    searchedrole = mongo.db.roles.find_one({'_id': ObjectId(id)})
    if searchedrole:
        if searchedrole['name'] == 'admin' or searchedrole['name'] == 'everyone':
            flash('Error: Cannot delete default roles')
            return redirect(url_for('roles'))
        mongo.db.roles.delete_one({'_id': ObjectId(id)})
        flash('User deleted successfully!')
        return redirect(url_for('roles'))
    else:
        return 'Error loading #{id}'.format(id=id)
        
@app.route('/admin/users/createrole/', methods=['GET', 'POST'])
@login_required(perm="can_edit_users")
def createrole():
    """
    Create role route endpoint. 
    This allows users with the `can_edit_users` permission to create user roles

    Parameters
    ----------
        GET:/admin/users/createrole
        POST:/admin/users/createrole

    Returns
    -------
        Redirects to the roles page if the role was created successfully
        Redirects to the create role page if a role with the specified name already exists
    """
    form = UpdateRoleForm()
    if form.validate_on_submit():
        if(Role.search_for_by_name(db_manager.mongo, form.name.data) is None):
            Role.create_new(db_manager.mongo, form.name.data, form.priority.data, form.can_edit_items.data, form.can_edit_users.data, form.can_view_hidden.data)
            flash('Role updated successfully!')
            return redirect(url_for('roles'))
        else:
            flash('A role with that name already exists')
            return redirect(url_for('createrole'))
    return render_template('admin-pages/user-man/createrole.html', form=form)

@app.route('/admin/test')
@login_required(perm="can_view_hidden")
def testing():
    return render_template('admin-pages/test.html')


#### Following pages for Tag and Implication Management ####




# Page for creating a tag
@app.route('/admin/lib-man/tag-man/create-a-tag', methods=['POST','GET'])
@login_required(perm="can_edit_items")
def create_tag():
    """
    Create tag route endpoint. 
    This allows users with the `can_edit_items` permission to create a new tag

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/create-a-tag
        POST:/admin/lib-man/tag-man/create-a-tag

    Returns
    -------
        Redirects to the tags pags if the tag is created successfully
        'you cannot create an empty tag' if the tag name is empty
        'the tag already exists' if the tag already exists
    """
    form = createTagForm()
    if form.validate_on_submit():
        if form.name.data.isspace() or form.name.data is '':
            return 'you cannot create an empty tag'
        tag_exists = Tag.search_for_by_name(db_manager.mongo, form.name.data)
        if tag_exists is None:
            new_tag = Tag(form.name.data, [])
            new_tag.write_to_db(db_manager.mongo)
            return redirect(url_for('all_tags'))
        else:
            return 'the tag already exists'
    return render_template('admin-pages/lib-man/tag-man/create-tag.html', form=form)


# Page for showing all implications
@app.route('/admin/tag-man/all-impl')
@login_required(perm="can_view_hidden")
def all_impl():
    """
    Show implication route endpoint. 
    This allows users with the `can_view_hidden` permission to view all implications

    Parameters
    ----------
        GET:/admin/tag-man/all-impl
        POST:/admin/tag-man/all-impl

    Returns
    -------
        Renders the implications page
    """
    return render_template('admin-pages/lib-man/tag-man/all-impl.html',  tags_collection=tags_collection)


def get_tags(tags, offset=0, per_page=10):
    """
    Function to get the tags for pagination

    Parameters
    ----------
        tags
            List of all tags in the database
        offset
            The offset number of tags
        per_page
            the number of tags to show per page

    Returns
    -------
        A list of tags
    """
    return tags[offset: offset + per_page]

# Page for showing all tags
@app.route('/admin/lib-man/tag-man/all-tags')
@login_required(perm="can_view_hidden")
def all_tags():
    """
    Show tags route endpoint. 
    This allows users with the `can_view_hidden` permission to view all tags

    Parameters
    ----------
        GET:/admin/tag-man/all-tags
        POST:/admin/tag-man/all-tags

    Returns
    -------
        Renders the tags page
    """
    tags = tags_collection.find()
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    total = tags_collection.count()
    page = request.args.get(get_page_parameter(), type=int, default=1)
    pagination_tags = get_tags(tags, offset=offset, per_page=per_page)
    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')
    return render_template('admin-pages/lib-man/tag-man/all-tags.html', tags=tags, pagination=pagination)

# Page for tag search
@app.route('/admin/lib-man/tag-man/search-item', methods=['GET', 'POST'])
@login_required(perm="can_view_hidden")
def search_item():
    """
    Item search route endpoint. 
    This allows users with the `can_view_hidden` permission to search for items in the admin item library

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/search-item
        POST:/admin/lib-man/tag-man/search-item

    Returns
    -------
        Renders the item search page
    """
    searchString = request.form.get('tagSearchInput')
    is_input = False
    is_result = False
    result = []
    db_results =[]
    print(searchString)
    if searchString is not None and searchString is not '':
        result = search_string_to_mongodb_query(db_manager.mongo, searchString)
        is_input = True
        if isinstance(result,list) :
            is_result=False
            result = str(result[0])[23:]
        else:
            flash('Search result retrieved from the database!')
            is_result = True
            db_results = db_manager.mongo.db.items.find(result)
    return render_template('admin-pages/lib-man/tag-man/search-item.html', is_input=is_input, is_result=is_result, result=result, searchString=searchString, db_results=db_results, tags_collection=tags_collection)


# Page for creating an implication
@app.route('/admin/lib-man/tag-man/create-impl', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def create_impl():
    """
    Create implication route endpoint. 
    This allows users with the `can_edit_items` permission to create implications

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/create-impl
        POST:/admin/lib-man/tag-man/create-impl

    Returns
    -------
        Redirects to the create implication page if the parent tag is the same as the child tag
        Redirects to the create implication page if the parent tag already exists as a parent
        Redirects to the all implications page if the implication was created successfully
    """
    form = addRuleForm()
    form.parent.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    form.child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    if form.validate_on_submit():
        parent_tag = Tag.search_for_by_name(db_manager.mongo, form.parent.data)
        child_tag  = Tag.search_for_by_name(db_manager.mongo, form.child.data)
        if form.parent.data == form.child.data:
            flash('A tag cannot imply to itself')
            return redirect(url_for('create_impl'))
        if parent_tag.implies:
            flash('This parent tag already exists as a parent')
            return redirect(url_for('create_impl'))
        parent_tag.implies.append(TagReference(child_tag))
        parent_tag.write_to_db(db_manager.mongo)
        for item in db_manager.mongo.db.items.find():
            this_item = Item.from_dict(item)
            this_item.recalculate_implied_tags(db_manager.mongo)
        flash('Implication added successfully, all items implication are updated')
        return redirect(url_for('all_impl'))
    return render_template('admin-pages/lib-man/tag-man/create-implication.html', form=form)

# Page for editing a tag and it's implications
@app.route('/admin/lib-man/tag-man/edit-tag/<tag_name>')
@login_required(perm="can_edit_items")
def edit_tag(tag_name):
    """
    Edit tag route endpoint. 
    This allows users with the `can_edit_items` permission to edit tags

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/edit-tag/<tag_name>
        POST:/admin/lib-man/tag-man/edit-tag/<tag_name>

    Returns
    -------
        Renders the edit tag page
    """
    this_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    sibling_list = [Tag.from_dict(t) for t in tags_collection.find({"$and": [{"implies": this_tag.id}, {"_id": {"$in": [t.tag_id for t in this_tag.implies]}}]})]
    implied_by_list = [Tag.from_dict(t) for t in tags_collection.find({"$and": [{"implies": this_tag.id}, {"_id": {"$not": {"$in": [t.tag_id for t in this_tag.implies]}}}]})]
    implied_list = [t for t in this_tag.implies if t.tag_id not in [it.id for it in sibling_list]]
    add_parent_implication_form = addTagParentImplForm()
    add_parent_implication_form.select_parent.choices=[(tag['_id'], tag['name']) for tag in db_manager.mongo.db.tags.find({"$and": [{"_id": {"$ne": this_tag.id}}, {"_id": {"$not": {"$in": [t.id for t in implied_by_list]}}}]})]
    add_sibling_implication_form = addTagSiblingImplForm()
    add_sibling_implication_form.select_sibling.choices=[(tag['_id'], tag['name']) for tag in db_manager.mongo.db.tags.find({"$and": [{"_id": {"$ne": this_tag.id}}, {"_id": {"$not": {"$in": [t.id for t in sibling_list]}}}]})]
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices=[(tag['_id'], tag['name']) for tag in db_manager.mongo.db.tags.find({"$and": [{"_id": {"$ne": this_tag.id}}, {"_id": {"$not": {"$in": [t.tag_id for t in this_tag.implies]}}}]})]
    return render_template('admin-pages/lib-man/tag-man/edit-tag.html', add_implication_form=add_implication_form,add_parent_implication_form=add_parent_implication_form,add_sibling_implication_form=add_sibling_implication_form, tag=this_tag, tags_collection=tags_collection,sibling_list=sibling_list,implied_by_list=implied_by_list,implied_list=implied_list, Tag=Tag)


#### Following pages for Item Management ####

# Page for showing all library items
@app.route('/admin/all-items')
@login_required(perm="can_view_hidden")
def all_items():
    """
    View all items route endpoint. 
    This allows users with the `can_view_hidden` permission to view all items

    Parameters
    ----------
        GET:/admin/all-items
        POST:/admin/all-items

    Returns
    -------
        Renders the all items page
    """
    items = db_manager.mongo.db.items.find()
    items = [Item.from_dict(i) for i in items]
    for item in items:
        item.recalculate_implied_tags(db_manager.mongo)  # Again, thia is NOT be needed
    item_names = {item.id: item.get_attributes_by_option(db_manager.name_attrib)[0].value for item in items}
    item_images = {}
    for item in items:
        picture = item.get_attributes_by_option(db_manager.main_picture)
        if picture:
            item_images[item.id] = url_for('image', oid=str(picture[0].value))
        else:
            item_images[item.id] = url_for('static', filename='img/logo.png')  # TODO supply 'no-image' image?
    return render_template('admin-pages/lib-man/all-items.html', items=items, tags_collection=tags_collection,
                           item_names=item_names, item_images=item_images)

# Page for creating an item
@app.route('/admin/lib-man/create-item', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def create_item():
    """
    Create item route endpoint. 
    This allows users with the `can_edit_items` permission to create items

    Parameters
    ----------
        GET:/admin/lib-man/create-item
        POST:/admin/lib-man/create-item

    Returns
    -------
        Redirects to the create item page if the item already exists
        Redirects to the all items page if the implication was created successfully
    """
    form = newEntryForm()
    form.selection.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    all_tags = db_manager.mongo.db.tags.find()
    if form.validate_on_submit():
        # search for an item with the same title
        # TODO: Ask client: Do we really care if things have the same name?
        item_exists = Item.search_for_by_attribute(db_manager.mongo, db_manager.name_attrib, form.title.data)
        if not item_exists:
            # find the matching tag
            tags = []
            for tag in form.selection.data:
                found_tag = Tag.search_for_by_name(db_manager.mongo, tag)
                tags.append(TagReference(found_tag.id))
            description = form.description.data.split('\r\n')
            new_item = Item([SingleLineStringAttribute(db_manager.name_attrib, form.title.data),
                             MultiLineStringAttribute(db_manager.description_attrib, description)],
                            tags, [])
            new_item.write_to_db(db_manager.mongo)
            new_item.recalculate_implied_tags(db_manager.mongo)
            return redirect(url_for('all_items'))
        else:
            flash('the item: ' + form.title.data + ' already exists')
            return redirect(url_for('create_item'))
    return render_template('admin-pages/lib-man/create-item.html', form=form)

# Library item edit page
@app.route('/admin/lib-man/lib-edit/<item_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def lib_edit(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    item.recalculate_implied_tags(db_manager.mongo)
    attributes = item.attributes
    form = addTagForm()
    form.selection.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    if form.validate_on_submit():
        tag_to_attach = Tag.search_for_by_name(db_manager.mongo, form.selection.data)
        for tag_ref in item.tags:
            if str(tag_ref.tag_id) == str(tag_to_attach.id):
                flash('This tag already attached to the item!')
        item.tags.append(TagReference(tag_to_attach))
        item.write_to_db(db_manager.mongo)
    return render_template('admin-pages/lib-man/lib-edit.html', attributes=attributes, form=form, item=item, item_id=item_id,
                           Tag=Tag, tags_collection=tags_collection)


# Page for editing an item and it's tags
@app.route('/admin/lib-man/<item_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def edit_item(item_id):
    """
    Item edit route endpoint. 
    This allows users with the `can_edit_items` permission to edit items

    Parameters
    ----------
        GET:/admin/lib-man/<item_id>
        POST:/admin/lib-man/<item_id>

    Returns
    -------
        Redirects to the edit item page if the item was updated successfully
    """
    item = db_manager.mongo.db.items.find_one({"_id": ObjectId(item_id)})
    if item is None:
        return page_not_found(404)
    item = Item.from_dict(item)
    item.recalculate_implied_tags(db_manager.mongo)
    attributes = [a for a in item.attributes if a.option_id != db_manager.main_picture.id]
    attribute_options = db_manager.mongo.db.attrib_options.find({"_id": {"$in": [a.option_id for a in attributes]}})
    attribute_options = {a.id: a for a in [AttributeOption.from_dict(a) for a in attribute_options]}
    if item.get_attributes_by_option(db_manager.main_picture):
        image_url = url_for('image', oid=str(item.get_attributes_by_option(db_manager.main_picture)[0].value))
    else:
        image_url = url_for('static', filename='img/logo.png')  # TODO supply 'no-image' image?
    form = addTagForm()
    form.selection.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    if form.validate_on_submit():
        tag_to_attach = Tag.search_for_by_name(db_manager.mongo, form.selection.data)
        for tag_ref in item.tags:
            if str(tag_ref.tag_id) == str(tag_to_attach.id):
                flash('this tag already attached to the item!')
                return redirect(url_for('edit_item', item_id=item_id))
        item.tags.append(TagReference(tag_to_attach))
        item.write_to_db(db_manager.mongo)
        item.recalculate_implied_tags(db_manager.mongo)
        flash('Tag added successfully! Tag implications have been recalculated.')
        return redirect(url_for('edit_item', item_id=item_id))
    return render_template('admin-pages/lib-man/edit-item.html', attribute_options=attribute_options, form=form, item=item,
                           item_id=item_id, tags_collection=tags_collection, image_url=image_url, name_attribute=db_manager.name_attrib)

# Page for updating Name or Description of an item
@app.route('/admin/lib-man/item-update-attrib/<item_id>/<attrib_option_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def item_update_attrib(item_id, attrib_option_id):
    """
    Item attribute update route endpoint. 
    This allows users with the `can_edit_items` permission to update the attributes of an item

    Parameters
    ----------
        GET:/admin/lib-man/item-update-attrib/<item_id>/<attrib_option_id>
        POST:/admin/lib-man/item-update-attrib/<item_id>/<attrib_option_id>

    Returns
    -------
        Redirects to the edit item page if the attribute was updated successfully
    """
    form = updateAttribForm()
    item = db_manager.mongo.db.items.find_one({"_id": ObjectId(item_id)})
    if item is None:
        return page_not_found(404)
    item = Item.from_dict(item)
    attribute_option = db_manager.mongo.db.attrib_options.find_one({"_id": ObjectId(attrib_option_id)})
    if attribute_option is None:
        return page_not_found(404)
    attribute_option = AttributeOption.from_dict(attribute_option)
    if form.validate_on_submit():
        if ObjectId(attrib_option_id) == db_manager.name_attrib:
            item_name_attrib = AttributeOption.search_for_by_name(db_manager.mongo, "name")
            item_exists = Item.search_for_by_attribute(db_manager.mongo, item_name_attrib, form.attrib_value.data)
            if item_exists:
                flash('An item with the same name already exists!')
                return redirect(url_for('item_update_attrib', item_id=item_id, attrib_option_id=attrib_option_id))
        if not item.get_attributes_by_option(ObjectId(attrib_option_id)):
            return page_not_found(404)

        attribute = item.get_attributes_by_option(ObjectId(attrib_option_id))[0]
        if attribute:
            listOfString = form.attrib_value.data.split('\r\n')
            attribute.value = listOfString
            print(listOfString)
            item.write_to_db(db_manager.mongo)
            flash('Item updated')
            return redirect(url_for('edit_item', item_id=item_id))
        else:
            return page_not_found(404)
    return render_template('admin-pages/lib-man/item-add-attrib.html', form=form, attrib_name=attribute_option.attribute_name)


#---------------------------
#  All functions
#---------------------------

# Function for editing item image
@app.route('/admin/lib-man/image-edit/<item_id>', methods=['POST'])
@login_required(perm="can_edit_items")
def lib_item_image_edit(item_id):
    """
    Item image edit route endpoint. 
    This allows users with the `can_edit_items` permission to update the image of an item

    Parameters
    ----------
        GET:/admin/lib-man/image-edit/<item_id>
        POST:/admin/lib-man/image-edit/<item_id>

    Returns
    -------
        Redirects to the edit item page if the image was updated successfully
    """
    item = db_manager.mongo.db.items.find_one({"_id": ObjectId(item_id)})
    if item is None:
        return page_not_found(404)
    item = Item.from_dict(item)
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        oid = db_manager.fs.put(file, content_type=file.content_type, filename=filename)
        attribute = item.get_attributes_by_option(db_manager.main_picture)
        if attribute:
            attribute = attribute[0]
            db_manager.fs.delete(attribute.value)
            attribute.value = oid
        else:
            item.attributes.append(PictureAttribute(db_manager.main_picture, oid))
        item.write_to_db(db_manager.mongo)
    return redirect(url_for('edit_item', item_id=str(item_id)))


# Function for adding an implicaiton to a tag
@app.route('/admin/lib-man/tag-man/parent-implication-add/<child_tag_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def parent_implication_add(child_tag_id):
    """
    Tag implication add route endpoint. 
    This allows users with the `can_edit_items` permission to add an implication to a tag

    Parameters
    ----------
        GET:/admin/lib-man/parent-implication-add/<child_tag_id>
        POST:/admin/lib-man/parent-implication-add/<child_tag_id>

    Returns
    -------
        Redirects to the tag edit page if the parent tag is the same as the child tag
        Redirects to the tag edit page if the implication already exists
        Redirects to the tag edit page if the implication was created successfully
    """
    add_implication_form = addTagParentImplForm()
    child_tag = db_manager.mongo.db.tags.find_one({"_id": ObjectId(child_tag_id)})
    if child_tag is None:
        return page_not_found(404)
    child_tag = Tag.from_dict(child_tag)

    parent_tag = db_manager.mongo.db.tags.find_one({"_id": ObjectId(add_implication_form.select_parent.data)})
    if parent_tag is None:
        return page_not_found(404)
    parent_tag = Tag.from_dict(parent_tag)

    if parent_tag.id == child_tag.id:
        flash("A tag cannot imply itself!")
        return redirect(url_for('edit_tag', tag_name=parent_tag.name))
    elif child_tag.id in [t.tag_id for t in parent_tag.implies]:
        flash("This implication already exists!")
        return redirect(url_for('edit_tag', tag_name=child_tag.name))
    else:
        tag_ref = TagReference(child_tag.id)
        parent_tag.implies.append(tag_ref)
        parent_tag.write_to_db(db_manager.mongo)
        return redirect(url_for('edit_tag', tag_name=child_tag.name))


# function for removing a tag from an item
@app.route('/admin/lib-man/item-remove-tag/<item_id>/<tag_name>',methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def item_remove_tag(item_id, tag_name):
    """
    Item tag remove route endpoint. 
    This allows users with the `can_edit_items` permission to remove a tag from an item

    Parameters
    ----------
        GET:/admin/lib-man/item-remove-tag/<item_id>/<tag_name>
        POST:/admin/lib-man/item-remove-tag/<item_id>/<tag_name>

    Returns
    -------
        Redirects to the tag edit page if the tag was removed successfully
    """
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    for tag_ref in item.tags:
        if tag_ref.tag_id == tag.id:
            item.remove_tag(tag_ref)
            item.write_to_db(db_manager.mongo)
            item.recalculate_implied_tags(db_manager.mongo)
            flash('Tag deleted successfully! Tag implications has been recalculated.')
    return redirect(url_for('edit_item', item_id=item_id))

# Function for hiding an item
@app.route('/admin/lib-man/item_hide/<item_id>')
@login_required(perm="can_edit_items")
def item_hide(item_id):
    """
    Item hide route endpoint. 
    This allows users with the `can_edit_items` permission to hide items from users who cannot view hidden items

    Parameters
    ----------
        GET:/admin/lib-man/item_hide/<item_id>
        POST:/admin/lib-man/item_hide/<item_id>

    Returns
    -------
        Redirects to the tag edit page
    """
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id" : ObjectId(item_id)})[0])
    item.hide(db_manager.mongo)
    return redirect(url_for('edit_item', item_id=item_id))

# Function for removing an item from the library
@app.route('/admin/lib-man/image-remove/<item_id>', methods=['POST'])
@login_required(perm="can_edit_items")
def lib_item_image_remove(item_id):
    """
    Item image remove route endpoint. 
    This allows users with the `can_edit_items` permission to remove the image from an item

    Parameters
    ----------
        GET:/admin/lib-man/image-remove/<item_id>
        POST:/admin/lib-man/image-remove/<item_id>

    Returns
    -------
        Redirects to the item edit page
    """
    item = db_manager.mongo.db.items.find_one({"_id": ObjectId(item_id)})
    if item is None:
        return page_not_found(404)
    item = Item.from_dict(item)
    attribute = item.get_attributes_by_option(db_manager.main_picture)
    if attribute:
        attribute = attribute[0]
        db_manager.fs.delete(attribute.value)
        item.attributes = [a for a in item.attributes if a.option_id != db_manager.main_picture.id]
        item.write_to_db(db_manager.mongo)
    return redirect(url_for('edit_item', item_id=str(item_id)))

# Funciton for deleting an implication rule on Tag's detail page
@app.route('/admin/lib-man/tag-man/parent-rule-delete/<tag_name>')
@login_required(perm="can_edit_items")
def parent_rule_delete(tag_name):
    """
    Implication remove route endpoint. 
    This allows users with the `can_edit_items` permission to remove an implication rule from a tag

    Parameters
    ----------
        GET:/admin/lib-man/parent-rule-delete/<tag_name>
        POST:/admin/lib-man/parent-rule-delete/<tag_name>

    Returns
    -------
        Redirects to the tag edit page
    """
    child_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tags = db_manager.mongo.db.tags.find({"implies": child_tag.id})
    for tag in tags:
        tag = Tag.from_dict(tag)
        tag.implies = [tag for tag in tag.implies if tag.tag_id != child_tag.id]
        tag.write_to_db(db_manager.mongo)
    flash('The parent implications for tag '+ tag_name + ' has been cleared')
    return redirect(url_for('edit_tag',tag_name=tag_name))

# Funciton for deleting an implication rule on Tag's detail page
@app.route('/admin/lib-man/tag-man/sibling-rule-delete/<tag_name>')
@login_required(perm="can_edit_items")
def sibling_rule_delete(tag_name):
    """
    Bi-implication remove route endpoint. 
    This allows users with the `can_edit_items` permission to remove a bi-implication rule from a tag

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/sibling-rule-delete/<tag_name>
        POST:/admin/lib-man/tag-man/sibling-rule-delete/<tag_name>

    Returns
    -------
        Redirects to the tag edit page
    """
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    to_remove = []
    for implied in tag.implies:
        implied = Tag.from_dict(db_manager.mongo.db.tags.find_one({"_id": implied.tag_id}))
        if tag.id in [t.tag_id for t in implied.implies]:
            to_remove.append(implied.id)
            implied.implies = [i for i in implied.implies if i.tag_id != tag.id]
            implied.write_to_db(db_manager.mongo)
    tag.implies = [i for i in tag.implies if i.tag_id not in to_remove]
    tag.write_to_db(db_manager.mongo)
    flash('The Bi-implications for tag '+ tag_name + ' has been cleared')
    return redirect(url_for('edit_tag',tag_name=tag_name))

# Function for adding an implicaiton to a tag
@app.route('/admin/lib-man/tag-man/sibling-implication-add/<parent_tag_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def sibling_implication_add(parent_tag_id):
    """
    Bi-implication add route endpoint. 
    This allows users with the `can_edit_items` permission to add a bi-implication rule for a tag

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/sibling-rule-add/<parent_tag_id>
        POST:/admin/lib-man/tag-man/sibling-rule-add/<parent_tag_id>

    Returns
    -------
        Redirects to the tag edit page
    """
    add_sibling_implication_form = addTagSiblingImplForm()
    parent_tag = db_manager.mongo.db.tags.find_one({"_id": ObjectId(parent_tag_id)})
    if parent_tag is None:
        return page_not_found(404)
    parent_tag = Tag.from_dict(parent_tag)
    child_tag = db_manager.mongo.db.tags.find_one({"_id": ObjectId(add_sibling_implication_form.select_sibling.data)})
    if child_tag is None:
        return page_not_found(404)
    child_tag = Tag.from_dict(child_tag)
    if parent_tag.id == child_tag.id:
        flash("A tag cannot imply itself!")
        return redirect(url_for('edit_tag', tag_name=parent_tag.name))
    elif child_tag.id in [t.tag_id for t in parent_tag.implies] and parent_tag.id in [t.tag_id for t in child_tag.implies]:
        flash("This implication already exists!")
        return redirect(url_for('edit_tag', tag_name=parent_tag.name))
    else:
        if child_tag.id not in [t.tag_id for t in parent_tag.implies]:
            child_tag_ref = TagReference(child_tag.id)
            parent_tag.implies.append(child_tag_ref)
            parent_tag.write_to_db(db_manager.mongo)
        if parent_tag.id not in [t.tag_id for t in child_tag.implies]:
            parent_tag_ref = TagReference(parent_tag.id)
            child_tag.implies.append(parent_tag_ref)
            child_tag.write_to_db(db_manager.mongo)
        return redirect(url_for('edit_tag', tag_name=parent_tag.name))

# Function for  deleting a tag compeltely
@app.route('/admin/lib-man/tag-man/tag-delete/<tag_name>')
@login_required(perm="can_edit_items")
def tag_delete(tag_name):
    """
    Tag delete route endpoint. 
    This allows users with the `can_edit_items` permission to delete a tag

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/tag-delete/<tag_name>
        POST:/admin/lib-man/tag-man/tag-delete/<tag_name>

    Returns
    -------
        Redirects to the tags page
    """
    tag_to_delete = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag_to_delete.delete_from_db(db_manager.mongo)
    implication_dropped = 0
    for tag in tags_collection.find():
        for implication in tag['implies']:
            if str(implication) == str(tag_to_delete.id):
                tag['implies'].remove(implication)
                Tag.from_dict(tag).write_to_db(db_manager.mongo)
                implication_dropped += 1        # need to add user notification
    flash('Tag: ' + str(tag_name) + ' dropped, ' + str(implication_dropped) + ' implications are affected.')
    return redirect(url_for('all_tags'))

# Funciton for deleting an implication rule on Tag's detail page
@app.route('/admin/lib-man/tag-man/rule-delete/<tag_name>')
@login_required(perm="can_edit_items")
def rule_delete(tag_name):
    """
    Rule delete route endpoint. 
    This allows users with the `can_edit_items` permission to delete an implication rule from a tag

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/rule-delete/<tag_name>
        POST:/admin/lib-man/tag-man/rule-delete/<tag_name>

    Returns
    -------
        Redirects to the edit tag page
    """
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag.implies = []
    tag.write_to_db(db_manager.mongo)
    flash('The implications for tag '+ tag_name + ' has been cleared')
    return redirect(url_for('edit_tag',tag_name=tag_name))

# Funciton for deleting an implication rule on Tag Implication page
@app.route('/admin/lib-man/tag-man/impl_delete/<tag_name>')
@login_required(perm="can_edit_items")
def impl_delete(tag_name):
    """
    Implication delete route endpoint. 
    This allows users with the `can_edit_items` permission to delete an implication rule from the implication page

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/impl_delete/<tag_name>
        POST:/admin/lib-man/tag-man/impl_delete/<tag_name>

    Returns
    -------
        Redirects to the implications page
    """
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag.implies = []
    tag.write_to_db(db_manager.mongo)
    flash('The implications for tag '+ tag_name + ' has been deleted')
    return render_template('admin-pages/lib-man/tag-man/all-impl.html',  tags_collection=tags_collection)

#  Function for removing an implication from a parent tag
@app.route('/admin/lib-man/implication-remove/<tag_name>/<implied_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def parent_implication_remove(tag_name, implied_id):
    """
    Parent implication delete route endpoint. 
    This allows users with the `can_edit_items` permission to delete an implication from a parent tag

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/implication-remove/<tag_name>/<implied_id>
        POST:/admin/lib-man/tag-man/implication-remove/<tag_name>/<implied_id>

    Returns
    -------
        Redirects to the tag edit page
    """
    tag = Tag.from_dict(db_manager.mongo.db.tags.find({"name": tag_name})[0])
    implied_tag = Tag.from_dict(db_manager.mongo.db.tags.find({"_id": ObjectId(implied_id)})[0])
    for tag_ref in tag.implies:
        if tag_ref.tag_id == implied_tag.id:
            tag.remove_implied_tag(tag_ref)
            tag.write_to_db(db_manager.mongo)
    return redirect(url_for('edit_tag', tag_name=implied_tag.name))

@app.route('/admin/lib-man/sibling-implication-remove/<tag_name>/<sibling_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def sibling_implication_remove(tag_name, sibling_id):
    """
    Bi-implication delete route endpoint. 
    This allows users with the `can_edit_items` permission to delete a Bi-implication from a parent tag

    Parameters
    ----------
        GET:/admin/lib-man/sibling-implication-remove/<tag_name>/<sibling_id>
        POST:/admin/lib-man/sibling-implication-remove/<tag_name>/<sibling_id>

    Returns
    -------
        Redirects to the tag edit page
    """
    tag = Tag.from_dict(db_manager.mongo.db.tags.find({"name": tag_name})[0])
    sibling_tag = Tag.from_dict(db_manager.mongo.db.tags.find_one({"_id": ObjectId(sibling_id)}))
    tag.implies = [i for i in tag.implies if i.tag_id != sibling_tag.id]
    sibling_tag.implies = [i for i in sibling_tag.implies if i.tag_id != tag.id]
    tag.write_to_db(db_manager.mongo)
    sibling_tag.write_to_db(db_manager.mongo)
    return redirect(url_for('edit_tag', tag_name=tag_name))

# Function for adding an implicaiton to a tag
@app.route('/admin/lib-man/tag-man/implication-add/<parent_tag_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def implication_add(parent_tag_id):
    """
    Implication add route endpoint. 
    This allows users with the `can_edit_items` permission to add an implication to a tag

    Parameters
    ----------
        GET:/admin/lib-man/tag-man/implication-add/<parent_tag_id>
        POST:/admin/lib-man/tag-man/implication-add/<parent_tag_id>

    Returns
    -------
        Redirects to the tag edit page
    """
    add_implication_form = addTagImplForm()
    parent_tag = db_manager.mongo.db.tags.find_one({"_id": ObjectId(parent_tag_id)})
    if parent_tag is None:
        return page_not_found(404)
    parent_tag = Tag.from_dict(parent_tag)

    child_tag = db_manager.mongo.db.tags.find_one({"_id": ObjectId(add_implication_form.select_child.data)})
    if child_tag is None:
        return page_not_found(404)
    child_tag = Tag.from_dict(child_tag)

    if parent_tag.id == child_tag.id:
        flash("A tag cannot imply itself!")
        return redirect(url_for('edit_tag', tag_name=parent_tag.name))
    elif child_tag.id in [t.tag_id for t in parent_tag.implies]:
        flash("This implication already exists!")
        return redirect(url_for('edit_tag', tag_name=parent_tag.name))
    else:
        tag_ref = TagReference(child_tag.id)
        parent_tag.implies.append(tag_ref)
        parent_tag.write_to_db(db_manager.mongo)
        return redirect(url_for('edit_tag', tag_name=parent_tag.name))

#Function for removing an implication from a tag
@app.route('/admin/lib-man/implication-remove/<tag_name>/<implied_id>', methods=['GET', 'POST'])
@login_required(perm="can_edit_items")
def implication_remove(tag_name, implied_id):
    """
    Implication delete route endpoint. 
    This allows users with the `can_edit_items` permission to remove an implication from a tag

    Parameters
    ----------
        GET:/admin/lib-man/implication-remove/<tag_name>/<implied_id>
        POST:/admin/lib-man/implication-remove/<tag_name>/<implied_id>

    Returns
    -------
        Redirects to the tag edit page
    """
    tag = Tag.from_dict(db_manager.mongo.db.tags.find({"name": tag_name})[0])
    implied_tag = Tag.from_dict(db_manager.mongo.db.tags.find({"_id": ObjectId(implied_id)})[0])
    for tag_ref in tag.implies:
        if tag_ref.tag_id == implied_tag.id:
            tag.remove_implied_tag(tag_ref)
            tag.write_to_db(db_manager.mongo)
    return redirect(url_for('edit_tag', tag_name=tag_name))

# Function for delete an item
@app.route('/admin/lib-man/lib-delete/<item_id>')
@login_required(perm="can_edit_items")
def lib_delete(item_id):
    """
    Item delete route endpoint. 
    This allows users with the `can_edit_items` permission to delete an item

    Parameters
    ----------
        GET:/admin/lib-man/lib-delete/<item_id>
        POST:/admin/lib-man/lib-delete/<item_id>

    Returns
    -------
        Redirects to the items page
    """
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id" : ObjectId(item_id)})[0])
    item.delete_from_db(db_manager.mongo)
    flash('Item has been deleted successfully')
    return redirect(url_for('all_items'))

# -------------------------------------------
#   Error pages 
# -------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('admin-pages/error.html')

@app.errorhandler(500)
def page_not_found(e):
    return render_template('admin-pages/error.html')

@login_manager.user_loader
def load_user(did):
    return User.search_for_by_display_name(db_manager.mongo, did)
    
