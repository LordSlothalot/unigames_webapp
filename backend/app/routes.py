from functools import wraps

from bson.errors import InvalidId
from bson.objectid import ObjectId
from flask import render_template, url_for, redirect, request, flash, Response
from flask_login import current_user, login_user, logout_user
from gridfs import NoFile
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app import app, db_manager, login_manager
from app.database_impl.attrib_options import AttributeOption, PictureAttribute
from app.database_impl.items_instances import Item, Instance
from app.database_impl.tags import Tag, TagReference
from app.forms import newEntryForm, addTagForm, createTagForm, addTagImplForm, \
    updateAttribForm, LoginForm, RegistrationForm, UpdateForm, addRuleForm, serachForm
from app.search_parser import search_string_to_mongodb_query
from app.tables import UserTable
from app.user_models import User

# -------------------------------------------
#     User pages
# -------------------------------------------

tags_collection = db_manager.mongo.db.tags
attrib_collection = db_manager.mongo.db.attrib_options
mongo = db_manager.mongo


@app.route('/')
@app.route('/index')
def index():
    return render_template('user-pages/index.html')


# upload and view code taken and modified from here: https://gist.github.com/artisonian/492713
# needs refinement from here, but this is to give those who need it a head start
@app.route('/image/<oid>')
def image(oid):
    try:
        file = db_manager.fs.get(ObjectId(oid))
        return Response(file, mimetype=file.content_type, direct_passthrough=True)
    except NoFile or InvalidId:
        return page_not_found()


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
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
    files = [db_manager.fs.get_last_version(file) for file in db_manager.fs.list()]
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        find_user = mongo.db.Users.find_one({"email": email})
        print("find_user: ", find_user)
        if User.login_valid(email, password):
            loguser = User(find_user['email'], find_user['password'], find_user['first_name'], find_user['last_name'],
                           find_user['role'], find_user['_id'])
            login_user(loguser, remember=form.remember_me.data)
            # login_user(find_user, remember=form.remember_me.data)
            flash('You have been logged in!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            return "Login Unsuccessful"
    return render_template('user-pages/login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        password = generate_password_hash(form.password.data)
        find_user = User.get_by_email(email)
        if find_user is None:
            User.register(email, password, first_name, last_name, "Admin")
            flash(f'Account created for {form.email.data}!', 'success')
            return redirect(url_for('index'))
        else:
            flash(f'Account already exists for {form.email.data}!', 'success')
    return render_template('user-pages/register.html', title='Register', form=form)


@app.route('/library')
def library():
    # get urls for images, they are supposed to be retrieved from the db
    # dungeons_pic = url_for('static', filename='img/games/dungeons.jpg')

    # This would normally be acquired via the attribute in the item when iterating the items
    dungeons_pic = url_for('image', oid=str([a for a in Item.from_dict(
        db_manager.mongo.db.items.find_one({"attributes.option_id": db_manager.main_picture.id})).attributes if
                                             isinstance(a,
                                                        PictureAttribute) and a.option_id == db_manager.main_picture.id][
                                                0].picture_file_id))

    stars_pic = url_for('static', filename='img/games/stars-without-number.jpg')
    pulp_pic = url_for('static', filename='img/games/pulp-cthulhu.jpg')
    # pass them to the rendering page
    return render_template('user-pages/library.html', dungeons_pic=dungeons_pic, stars_pic=stars_pic, pulp_pic=pulp_pic)


@app.route('/events')
def events():
    return render_template('user-pages/events.html')


@app.route('/join')
def join():
    return render_template('user-pages/join.html')


@app.route('/committee')
def committee():
    return render_template('user-pages/committee.html')


@app.route('/lifeMembers')
def lifeMembers():
    return render_template('user-pages/lifeMembers.html')


@app.route('/constitution')
def constitution():
    return render_template('user-pages/constitution.html')


@app.route('/operations')
def operations():
    return render_template('user-pages/operations.html')


@app.route('/forbidden')
def forbidden():
    return render_template('user-pages/forbidden.html')


@login_manager.unauthorized_handler
def unauthorized():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if ((current_user.role != "Admin")):
        return redirect(url_for('forbidden'))
    return 'Page not found r.'


def login_required(role="ANY"):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if ((current_user.role != role) and (role != "ANY")):
                return login_manager.unauthorized()
            return fn(*args, **kwargs)

        return decorated_view

    return wrapper


# -------------------------------------------
#     Admin pages
# -------------------------------------------
@app.route('/admin', methods=['GET', 'POST'])
@login_required(role="Admin")
def admin():
    form = serachForm()
    result = []
    if form.validate_on_submit():
        result = search_string_to_mongodb_query(db_manager.mongo, form.searchInput.data)
    return render_template('admin-pages/home.html', form=form, result=result)


@app.route('/admin/users', methods=['GET', 'POST'])
@login_required(role="Admin")
def adminusers():
    items = mongo.db.Users.find()
    table = UserTable(items)
    table.border = True
    return render_template('admin-pages/users.html', table=table)


@app.route('/admin/users/<string:id>', methods=['GET', 'POST'])
@login_required(role="Admin")
def edit(id):
    searcheduser = mongo.db.Users.find_one({'_id': id})

    if searcheduser:
        form = UpdateForm(**searcheduser)
        name = searcheduser['first_name']
        if form.validate_on_submit():
            if form.delete.data:
                return redirect(url_for('deleteuser', id=id))
            mongo.db.Users.update_one({'_id': id},
                                      {"$set": {
                                          'first_name': request.form['first_name'],
                                          'last_name': request.form['last_name'],
                                          'email': request.form['email'],
                                          'role': request.form['role']
                                      }
                                      })
            flash('User updated successfully!')
            return redirect(url_for('adminusers'))
        return render_template('admin-pages/edit.html', form=form)
    else:
        return 'Error loading #{id}'.format(id=id)


@app.route('/admin/users/delete/<string:id>')
@login_required(role="Admin")
def deleteuser(id):
    searcheduser = mongo.db.Users.find_one({'_id': id})
    if searcheduser:
        mongo.db.Users.delete_one({'_id': id})
        flash('User deleted successfully!')
        return redirect(url_for('adminusers'))
    else:
        return 'Error loading #{id}'.format(id=id)


@app.route('/admin/test')
@login_required(role="Admin")
def testing():
    return render_template('admin-pages/test.html')


# Library management page
@app.route('/admin/lib')
@login_required(role="Admin")
def lib():
    items = db_manager.mongo.db.items.find()

    return render_template('admin-pages/lib-man/lib.html', items=items, tags_collection=tags_collection,
                           ObjectId=ObjectId, list=list)


# Library item edit page
@app.route('/admin/lib-man/lib-edit/<item_id>', methods=['GET', 'POST'])
@login_required(role="Admin")
def lib_edit(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    item.recalculate_implied_tags(db_manager.mongo)
    attributes = item.attributes
    form = addTagForm()
    form.selection.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    if form.validate_on_submit():
        tag_to_attach = Tag.search_for_by_name(db_manager.mongo, form.selection.data)
        for tag_ref in item.tags:
            if str(tag_ref.tag_id) == str(tag_to_attach.id):
                return 'this tag already attached to the item!'
        item.tags.append(TagReference(tag_to_attach))
        item.write_to_db(db_manager.mongo)

    return render_template('admin-pages/lib-man/lib-edit.html', attributes=attributes, form=form, item=item,
                           item_id=item_id,
                           Tag=Tag, tags_collection=tags_collection)


# function for removing a tag from an item
@app.route('/admin/lib-man/item-remove-tag/<item_id>/<tag_name>', methods=['GET', 'POST'])
@login_required(role="Admin")
def item_remove_tag(item_id, tag_name):
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    for tag_ref in item.tags:
        if tag_ref.tag_id == tag.id:
            item.remove_tag(tag_ref)
            item.write_to_db(db_manager.mongo)
    return redirect(url_for('lib_edit', item_id=item_id))


# Library add item page
@app.route('/admin/lib-man/lib-add', methods=['GET', 'POST'])
@login_required(role="Admin")
def lib_add():
    form = newEntryForm()
    all_tags = db_manager.mongo.db.tags.find()
    if form.validate_on_submit():
        # search for an item with the same title
        item_name_attrib = AttributeOption.search_for_by_name(db_manager.mongo, "name")
        item_exists = Item.search_for_by_attribute(db_manager.mongo, item_name_attrib, form.title.data)
        if not item_exists:
            # find the matching tag
            tag_name = form.selection.data
            found_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
            add_tag = TagReference(found_tag.id)
            new_instance = Instance([], [])
            new_item = Item({"name": form.title.data, "author": form.author.data}, [add_tag], [new_instance])
            new_item.write_to_db(db_manager.mongo)
            new_item.recalculate_implied_tags(db_manager.mongo)

            return redirect(url_for('lib'))
        else:
            return 'the item already exists'
    return render_template('admin-pages/lib-man/lib-add.html', form=form)


# Function for delete an item on library page
@app.route('/admin/lib-man/lib-delete/<item_id>')
@login_required(role="Admin")
def lib_delete(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    item.delete_from_db(db_manager.mongo)
    return redirect(url_for('lib'))


# Tag management page
@app.route('/admin/lib-man/tag-man/tag-all', methods=['GET', 'POST'])
@login_required(role="Admin")
def tag_all():
    # all_relations = db_manager.mongo.db.relation_options
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form = addRuleForm()
    add_rule_form.parent.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form.child.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form,
                           add_rule_form=add_rule_form, add_implication_form=add_implication_form,
                           tags_collection=tags_collection)


# Function for creating a new tag
@app.route('/admin/lib-man/tag-man/tag-create', methods=['GET', 'POST'])
@login_required(role="Admin")
def tag_create():
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form = addRuleForm()
    add_rule_form.parent.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form.child.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    if create_tag_form.validate_on_submit():
        tag_exists = Tag.search_for_by_name(db_manager.mongo, create_tag_form.name.data)
        if tag_exists is None:
            new_tag = Tag(create_tag_form.name.data, [])
            new_tag.write_to_db(db_manager.mongo)
            return redirect(url_for('tag_all'))
        else:
            return 'the tag already exists'
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form,
                           add_rule_form=add_rule_form, add_implication_form=add_implication_form,
                           tags_collection=tags_collection)


# Function for deleting the tag (not removing it from the item)
@app.route('/admin/lib-man/tag-man/tag-delete/<tag_name>')
@login_required(role="Admin")
def tag_delete(tag_name):
    tag_to_delete = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag_to_delete.delete_from_db(db_manager.mongo)
    implication_dropped = 0

    for tag in tags_collection.find():
        for implication in tag['implies']:
            if str(implication) == str(tag_to_delete.id):
                tag['implies'].remove(implication)
                Tag.from_dict(tag).write_to_db(db_manager.mongo)
                implication_dropped += 1  # need to add user notification
    return redirect(url_for('tag_all'))


# Function for adding an implicaiton to a tag
@app.route('/admin/lib-man/tag-man/implication-add/<tag_name>/<cur_child>', methods=['GET', 'POST'])
@login_required(role="Admin")
def implication_add(tag_name, cur_child):
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form = addRuleForm()
    add_rule_form.parent.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form.child.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    parent_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    child_tag = Tag.search_for_by_name(db_manager.mongo, add_implication_form.select_child.data)

    if add_implication_form.validate_on_submit():
        if add_implication_form.select_child.data is tag_name:
            return "A tag cannot imply itself!"
        elif str(child_tag.id) in cur_child:
            return "This implication already exists!"
        else:
            tag_ref = TagReference(child_tag.id)
            parent_tag.implies.append(tag_ref)
            parent_tag.write_to_db(db_manager.mongo)
            return redirect(url_for('tag_all'))
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form,
                           add_rule_form=add_rule_form, add_implication_form=add_implication_form,
                           tags_collection=tags_collection)


@app.route('/admin/lib-man/implication-remove/<tag_name>/<implied_id>', methods=['GET', 'POST'])
@login_required(role="Admin")
def implication_remove(tag_name, implied_id):
    tag = Tag.from_dict(db_manager.mongo.db.tags.find({"name": tag_name})[0])
    implied_tag = Tag.from_dict(db_manager.mongo.db.tags.find({"_id": ObjectId(implied_id)})[0])
    for tag_ref in tag.implies:
        if tag_ref.tag_id == implied_tag.id:
            tag.remove_implied_tag(tag_ref)
            tag.write_to_db(db_manager.mongo)
    return redirect(url_for('tag_all'))


# Funciton for adding an implication rule
@app.route('/admin/lib-man/tag-man/rule-add', methods=['GET', 'POST'])
@login_required(role="Admin")
def rule_add():
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form = addRuleForm()
    add_rule_form.parent.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form.child.choices = [(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    if add_rule_form.validate_on_submit():
        parent_tag = Tag.search_for_by_name(db_manager.mongo, add_rule_form.parent.data)
        child_tag = Tag.search_for_by_name(db_manager.mongo, add_rule_form.child.data)
        if add_rule_form.parent.data == add_rule_form.child.data:
            return 'A tag cannot refer to itself'
        if parent_tag.implies:
            return 'This parent tag already exists'
        parent_tag.implies.append(TagReference(child_tag))
        parent_tag.write_to_db(db_manager.mongo)
        return redirect(url_for('tag_all'))
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form,
                           add_rule_form=add_rule_form, add_implication_form=add_implication_form,
                           tags_collection=tags_collection)


# Funciton for deleting an implication rule
@app.route('/admin/lib-man/tag-man/rule-delete/<tag_name>')
@login_required(role="Admin")
def rule_delete(tag_name):
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag.implies = []
    tag.write_to_db(db_manager.mongo)
    return redirect(url_for('tag_all'))


# basically for updating Name and Author of an item
@app.route('/admin/lib-man/item-update-attrib/<item_id>/<attrib_name>', methods=['GET', 'POST'])
@login_required(role="Admin")
def item_update_attrib(item_id, attrib_name):
    form = updateAttribForm()
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]
    if form.validate_on_submit():
        update_attrib = {attrib_name: form.attrib_value.data}
        item['attributes'].update(update_attrib)
        Item.from_dict(item).write_to_db(db_manager.mongo)
        return redirect(url_for('lib_edit', item_id=item_id))
    return render_template('admin-pages/lib-man/item-add-attrib.html', form=form)


# -------------------------------------------
#   Error pages, can be futher implemented
# -------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return 'Page not found 404.'


@app.errorhandler(500)
def page_not_found(e):
    return 'Page not found 500.'


# if __name__=='__main__':
#    app.run(debug=True)


# Unfortunately attributes are gone
'''
#Attribute management page
@app.route('/admin/all-attributes')
def all_attributes():
    return render_template('admin-pages/lib-man/attrib-man/all-attributes.html', attrib_collection=attrib_collection)

#Page for creating an attribute
@app.route('/admin/lib-man/create-attribute', methods=['GET', 'POST'])
def create_attribute():
    form = createAttribForm()
    if form.validate_on_submit():
        attrib_name = form.attrib_name.data
        attrib_type = form.attrib_type.data
        new_attrib = AttributeOption.search_for_by_name(db_manager.mongo, attrib_name)
        if new_attrib is None:
            if attrib_type == 'Single-line string':
                new_attrib = AttributeOption(attrib_name, AttributeTypes.SingleLineString)
            elif attrib_type == 'Multi-line string':
                new_attrib = AttributeOption(attrib_name, AttributeTypes.MultiLineString)
            elif attrib_type == 'Integer':
                new_attrib = AttributeOption(attrib_name, AttributeTypes.SingleLineInteger)
            new_attrib.write_to_db(db_manager.mongo)
        else:
            return 'Attribute already exists!'
        return redirect(url_for('all_attributes'))
    return render_template('admin-pages/lib-man/attrib-man/create-attribute.html', form=form)

#Function for deleting an attribute
@app.route('/admin/lib-man/delete-attribute/<attrib_name>', methods=['GET', 'POST'])
def delete_attribute(attrib_name):
    attrib = AttributeOption.search_for_by_name(db_manager.mongo, attrib_name)
    attrib.delete_from_db(db_manager.mongo)
    return redirect(url_for('all_attributes'))

#Page for library item to add an attribute
@app.route('/admin/lib-man/item-add-attrib/<item_id>', methods=['GET', 'POST'])
def item_add_attrib(item_id):
    form = addAttribForm()
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]
    if form.validate_on_submit():
        attrib_name = form.attrib_name.data
        new_attrib = {attrib_name: form.attrib_value.data}
        item['attributes'].update(new_attrib)
        Item.from_dict(item).write_to_db(db_manager.mongo)
        return redirect(url_for('lib_edit', item_id=item_id))
    return render_template('admin-pages/lib-man/item-add-attrib.html', form=form)

#Update attribute detail (attribute management)
@app.route('/admin/lib-man/item-update-attrib/<item_id>/<attrib_name>', methods=['GET', 'POST'])
def item_update_attrib(item_id, attrib_name):
    form = updateAttribForm()
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]
    if form.validate_on_submit():
        update_attrib = {attrib_name: form.attrib_value.data}
        item['attributes'].update(update_attrib)
        Item.from_dict(item).write_to_db(db_manager.mongo)
        return redirect(url_for('lib_edit', item_id=item_id))
    return render_template('admin-pages/lib-man/item-add-attrib.html', form=form)

#function for removing an attribute from an item
@app.route('/admin/lib-man/item-remove-attrib/<item_id>/<attrib_name>', methods=['GET', 'POST'])
def item_remove_attrib(item_id, attrib_name):
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]
    del item['attributes'][attrib_name]
    Item.from_dict(item).write_to_db(db_manager.mongo)
    return redirect(url_for('lib_edit', item_id=item_id))
'''
