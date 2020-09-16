
from app import app, db_manager,  login_manager
from flask import Flask, render_template, url_for, redirect, request, flash
from app.database_impl.attrib_options import AttributeOption, AttributeTypes
from app.database_impl.items_instances import Item, Instance
from app.database_impl.tags import Tag, TagReference
from bson.objectid import ObjectId
from app.forms import newEntryForm, addTagForm, addInstanceForm, createTagForm, addTagImplForm, \
    addAttribForm, updateAttribForm, createAttribForm, LoginForm, RegistrationForm, UpdateForm
from app.user_models import User
from flask_pymongo import PyMongo
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash
from functools import wraps
from app.tables import UserTable
from bson.objectid import ObjectId

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
            loguser = User(find_user['email'], find_user['password'], find_user['first_name'], find_user['last_name'], find_user['role'], find_user['_id'])
            login_user(loguser, remember=form.remember_me.data)
            # login_user(find_user, remember=form.remember_me.data)
            flash('You have been logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            return "Login Unsuccessful"
    return render_template('user-pages/login.html', form = form)


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
        find_user =  User.get_by_email(email)
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
    dungeons_pic = url_for('static', filename='img/games/dungeons.jpg')
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
	return 'Page not found 404.'

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
@app.route('/admin')
@login_required(role="Admin")
def admin():
	
	return render_template('admin-pages/home.html')
	
@app.route('/admin/users', methods=['GET', 'POST'])
@login_required(role="Admin")
def adminusers():
	items = mongo.db.Users.find()
	table = UserTable(items)
	table.border = True
	return render_template('admin-pages/users.html', table=table)
	
@app.route('/admin/users/<string:id>', methods=['GET', 'POST'])
def edit(id):
    searcheduser = mongo.db.Users.find_one({'_id': id})

    if searcheduser:
        form = UpdateForm(**searcheduser)
        name = searcheduser['first_name']
        if form.validate_on_submit():
            mongo.db.Users.update_one({'_id': id},
                  { "$set": {
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
		
@app.route('/admin/test')
def testing():
	return render_template('admin-pages/test.html')


@app.route('/admin/lib')
def lib():
    items = db_manager.mongo.db.items.find().limit(10)

    return render_template('admin-pages/lib-man/lib.html', items=items, tags_collection=tags_collection,
                           ObjectId=ObjectId, list=list)


@app.route('/admin/lib-man/lib-edit/<item_id>', methods=['GET', 'POST'])
def lib_edit(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    attributes = item.attributes
    instances = Instance.search_for_by_item(db_manager.mongo, ObjectId(item_id))

    return render_template('admin-pages/lib-man/lib-edit.html', attributes=attributes, instances=instances, item=item,
                           Tag=Tag, tags_collection=tags_collection)


@app.route('/admin/all-attributes')
def all_attributes():
    return render_template('admin-pages/lib-man/attrib-man/all-attributes.html', attrib_collection=attrib_collection)


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


@app.route('/admin/lib-man/delete-attribute/<attrib_name>', methods=['GET', 'POST'])
def delete_attribute(attrib_name):
    attrib = AttributeOption.search_for_by_name(db_manager.mongo, attrib_name)
    attrib.delete_from_db(db_manager.mongo)
    return redirect(url_for('all_attributes'))


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


@app.route('/admin/lib-man/item-remove-attrib/<item_id>/<attrib_name>', methods=['GET', 'POST'])
def item_remove_attrib(item_id, attrib_name):
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]
    del item['attributes'][attrib_name]
    Item.from_dict(item).write_to_db(db_manager.mongo)
    return redirect(url_for('lib_edit', item_id=item_id))


@app.route('/admin/lib-man/lib-add', methods=['GET', 'POST'])
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
            add_tag = TagReference(found_tag.id, [])
            new_item = Item({"name": form.title.data, "author": form.author.data}, [add_tag])
            new_item.write_to_db(db_manager.mongo)
            new_item.recalculate_implied_tags(db_manager.mongo)

            return redirect(url_for('lib'))
        else:
            return 'the item already exists'
    return render_template('admin-pages/lib-man/lib-add.html', form=form)

@app.route('/admin/lib-man/lib-delete/<item_id>')
def lib_delete(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id" : ObjectId(item_id)})[0])
    item.delete_from_db(db_manager.mongo)
    return redirect(url_for('lib'))


@app.route('/admin/lib-man/tag-man/tag-all', methods=['GET', 'POST'])
def tag_all():
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', tags_collection=tags_collection)


@app.route('/admin/lib-man/tag-man/tag-create', methods=['GET', 'POST'])
def tag_create():
    form = createTagForm()
    if form.validate_on_submit():
        tag_exists = Tag.search_for_by_name(db_manager.mongo, form.name.data)
        if tag_exists is None:
            new_tag = Tag(form.name.data, [], [])
            new_tag.write_to_db(db_manager.mongo)
            return 'tag created'
        else:
            return 'the tag already exists'
    return render_template('admin-pages/lib-man/tag-man/tag-create.html', form=form)


# This will completely delete the tag (not removing it from the item)
@app.route('/admin/lib-man/tag-man/tag-delete/<tag_name>')
def tag_delete(tag_name):
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag.delete_from_db(db_manager.mongo)
    return redirect(url_for('tag_all'))


# @app.route('/admin/lib-man/tag-man/tag-edit-param/<tag_name>', methods=['GET', 'POST'])
# def tag_edit_param(tag_name):
#     tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
#     form = addTagParamForm()
#     if form.validate_on_submit():
#         param_type = form.paramType.data
#         # Find the right index for this parameter
#         last_index = -1
#         for param in tag.parameters:
#             if param.index == last_index + 1:
#                 last_index += 1
#                 continue
#             else:
#                 last_index += 1
#                 break
#         if param_type == 'integer':
#             try:
#                 new_param = TagParameter.new_integer(last_index, form.min_value.data, form.max_value.data)
#             except:
#                 return 'Something wrong'
#         elif param_type == 'real number':
#             try:
#                 new_param = TagParameter.new_real(last_index, form.min_value.data, form.max_value.data)
#             except:
#                 return 'Something wrong'
#
#         elif param_type == 'range(integer)':
#             try:
#                 new_param = TagParameter.new_integer_range(last_index, form.min_value.data, form.max_value.data)
#             except:
#                 return 'Something wrong'
#
#         elif param_type == 'range(real)':
#             try:
#                 new_param = TagParameter.new_real_range(last_index, form.min_value.data, form.max_value.data)
#             except:
#                 return 'Something wrong'
#
#         elif param_type == 'enumerated':
#             try:
#                 new_param = TagParameter.new_enum(last_index, [form.enumerate_values1.data, form.enumerate_values2.data,
#                                                                form.enumerate_values3.data])
#             except:
#                 return 'Something wrong'
#         elif param_type == 'string':
#             try:
#                 new_param = TagParameter.new_string(last_index)
#             except:
#                 return 'Something wrong'
#         tag.parameters.append(new_param)
#         tag.write_to_db(db_manager.mongo)
#         return 'tag param updated'
#
#     return render_template('admin-pages/lib-man/tag-man/tag-edit-param.html', tag=tag, form=form)


@app.route('/admin/lib-man/tag-man/tag-edit-impl/<tag_name>', methods=['GET', 'POST'])
def tag_edit_impl(tag_name):
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    form = addTagImplForm()
    if form.validate_on_submit():
        TagReference()
    return render_template('admin-pages/lib-man/tag-man/tag-edit-impl.html', tag=tag, form=form)


@app.route('/admin/lib-man/tag-add/<item_id>', methods=['GET', 'POST'])
def tag_add(item_id):
    form = addTagForm()
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]

    if form.validate_on_submit():
        tag_name = form.selection.data
        found_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
        add_tag = {'tag_id': found_tag.id, 'parameters': []}
        item['tags'].append(add_tag)

        Item.from_dict(item).write_to_db(db_manager.mongo)
        Item.from_dict(item).recalculate_implied_tags(db_manager.mongo)

        return redirect(url_for('lib_edit', item_id=item_id))

    return render_template('admin-pages/lib-man/tag-add.html', form=form, tags_collection=tags_collection, item=item)


# This will completely delete the tag (not removing it from the item)
@app.route('/admin/lib-man/tag-remove/<item_id>/<tag_name>')
def tag_remove(item_id, tag_name):
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]
    item.remove_tag()
    return redirect(url_for('lib_edit', item_id=item_id))


@app.route('/admin/lib-man/instance-add/<item_id>', methods=['GET', 'POST'])
def instance_add(item_id):
    form = addInstanceForm()
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]
    if form.validate_on_submit():
        tag_name = form.selection.data
        found_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
        new_instance = Instance(ObjectId(item_id), {"uuid": form.uuid.data, "damage report": form.damage_report.data},
                                [TagReference(found_tag.id, [])])
        new_instance.write_to_db(db_manager.mongo)
        new_instance.recalculate_implied_tags(db_manager.mongo)
        return redirect(url_for('lib_edit', item_id=item_id))
    return render_template('admin-pages/lib-man/instance-add.html', form=form, item=item,
                           tags_collection=tags_collection)


@app.route('/admin/lib-man/instance-edit/<instance_id>')
def instance_edit(instance_id):
    instance = db_manager.mongo.db.instances.find({"_id": ObjectId(instance_id)})[0]
    if not instance:
        print('there is no current instace')  # to be further implemented
    tags_collection = db_manager.mongo.db.tags
    return render_template('admin-pages/lib-man/instance-edit.html', instance=instance, tags_collection=tags_collection)


@app.route('/admin/lib-man/instance-delete/<item_id>/<instance_id>')
def instance_delete(item_id, instance_id):
    instance = db_manager.mongo.db.instances.find({"_id": ObjectId(instance_id)})[0]
    Instance.from_dict(instance).delete_from_db(db_manager.mongo)
    return redirect(url_for('lib_edit', item_id=item_id))


# -------------------------------------------
#   Error pages, can be futher implemented
# -------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return 'Page not found 404.'


@app.errorhandler(500)
def page_not_found(e):
    return 'Page not found 500.'


#if __name__=='__main__':
#    app.run(debug=True)

