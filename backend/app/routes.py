
from app import app, db_manager,  login_manager
from flask import Flask, render_template, url_for, redirect, request, flash
from app.database_impl.attrib_options import AttributeOption, AttributeTypes
from app.database_impl.items_instances import Item, Instance
from app.database_impl.tags import Tag, TagReference

from bson.objectid import ObjectId
from app.forms import newEntryForm, addTagForm, addInstanceForm, createTagForm, addTagImplForm, \
    updateAttribForm, LoginForm, RegistrationForm, UpdateForm, addRuleForm, searchForm, createTagForm
from app.user_models import User
from app.search_parser import search_string_to_mongodb_query, SearchStringParseError
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
            return redirect(url_for('admin'))
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

	
@app.route('/admin/users', methods=['GET', 'POST'])
@login_required(role="Admin")
def adminusers():
	users = mongo.db.Users.find()
	#table = UserTable(items)
	#table.border = True
	return render_template('admin-pages/user-man/users.html', users=users)
	
@app.route('/admin/users/edit/<id>', methods=['GET', 'POST'])
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
                  { "$set": {
                             'first_name': request.form['first_name'],
                              'last_name': request.form['last_name'],
                              'email': request.form['email'],
                              'role': request.form['role']
                             }
                 })
            flash('User updated successfully!')
            return redirect(url_for('adminusers'))
        return render_template('admin-pages/user-man/edit.html', form=form)
    else:
        return 'Error loading #{id}'.format(id=id)
    return render_template('admin-pages/user-man/edit.html', form=form)
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






#Tag management page
@app.route('/admin/lib-man/tag-man/tag-all', methods=['GET', 'POST'])
@login_required(role="Admin")
def tag_all():
    #all_relations = db_manager.mongo.db.relation_options
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form = addRuleForm()
    add_rule_form.parent.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form.child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form, add_rule_form=add_rule_form, add_implication_form=add_implication_form, tags_collection=tags_collection)

# Function for creating a new tag
@app.route('/admin/lib-man/tag-man/tag-create', methods=['GET', 'POST'])
@login_required(role="Admin")
def tag_create():
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form = addRuleForm()
    add_rule_form.parent.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form.child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    if create_tag_form.validate_on_submit():
        tag_exists = Tag.search_for_by_name(db_manager.mongo, create_tag_form.name.data)
        if tag_exists is None:
            new_tag = Tag(create_tag_form.name.data, [])
            new_tag.write_to_db(db_manager.mongo)
            return redirect(url_for('tag_all'))
        else:
            return 'the tag already exists'
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form, add_rule_form=add_rule_form, add_implication_form=add_implication_form, tags_collection=tags_collection)





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




#Funciton for adding an implication rule
@app.route('/admin/lib-man/tag-man/rule-add', methods=['GET', 'POST'])
@login_required(role="Admin")
def rule_add():
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form = addRuleForm()
    add_rule_form.parent.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    add_rule_form.child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]
    if add_rule_form.validate_on_submit():
        parent_tag = Tag.search_for_by_name(db_manager.mongo, add_rule_form.parent.data)
        child_tag  = Tag.search_for_by_name(db_manager.mongo, add_rule_form.child.data)
        if add_rule_form.parent.data == add_rule_form.child.data:
            return 'A tag cannot imply to itself'
        if parent_tag.implies:
            return 'This parent tag already exists'
        parent_tag.implies.append(TagReference(child_tag))
        parent_tag.write_to_db(db_manager.mongo)
        return redirect(url_for('all_impl'))
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form, add_rule_form=add_rule_form, add_implication_form=add_implication_form, tags_collection=tags_collection)




#------------For the new UI------------

@app.route('/admin', methods=['GET', 'POST'])
@login_required(role="Admin")
def admin():
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
    return render_template('admin-pages/new-home.html', tags_collection=tags_collection, user_count=user_count, recent_items=recent_items, recent_tags=recent_tags,item_count=item_count, tag_count=tag_count, tag_impl_count=tag_impl_count)

#Page for creating a tag
@app.route('/admin/lib-man/tag-man/create-a-tag', methods=['POST','GET'])
@login_required(role="Admin")
def create_tag():
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


#Page for showing all library items
@app.route('/admin/all-items')
@login_required(role="Admin")
def all_items():
    
    items = db_manager.mongo.db.items.find()
    for item in db_manager.mongo.db.items.find():
        this_item = Item.from_dict(item)
        this_item.recalculate_implied_tags(db_manager.mongo)
    return render_template('admin-pages/lib-man/all-items.html', items=items, tags_collection=tags_collection,
                           ObjectId=ObjectId, list=list)

#Function for delete an item
#checked OK
@app.route('/admin/lib-man/lib-delete/<item_id>')
@login_required(role="Admin")
def lib_delete(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id" : ObjectId(item_id)})[0])
    item.delete_from_db(db_manager.mongo)
    flash('Item has been deleted successfully')
    return redirect(url_for('all_items'))

#Page for showing all implications
#checked OK
@app.route('/admin/tag-man/all-impl')
@login_required(role="Admin")
def all_impl():
    return render_template('admin-pages/lib-man/tag-man/all-impl.html',  tags_collection=tags_collection)

#Page for showing all tags
#checked OK
@app.route('/admin/lib-man/tag-man/all-tags')
@login_required(role="Admin")
def all_tags():
    return render_template('admin-pages/lib-man/tag-man/all-tags.html', tags_collection=tags_collection)

#Page for tag search
#checked OK
@app.route('/admin/lib-man/tag-man/search-item', methods=['GET', 'POST'])
@login_required(role="Admin")
def search_item():
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

#Page for editing a tag and it's implications
# Need to debug
@app.route('/admin/lib-man/tag-man/edit-tag/<tag_name>')
@login_required(role="Admin")
def edit_tag(tag_name):
    this_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag = this_tag.to_dict()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]

    if add_implication_form.validate_on_submit():
        parent_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
        child_tag = Tag.search_for_by_name(db_manager.mongo, add_implication_form.select_child.data)
        if add_implication_form.select_child.data == tag_name:
            flash("A tag cannot imply itself!")
            return redirect(url_for('edit_tag', tag_name=tag_name))
        elif str(child_tag.id)  in cur_child:
            flash("This implication already exists!")
            return redirect(url_for('edit_tag', tag_name=tag_name))
        else:

            tag_ref = TagReference(child_tag.id)
            parent_tag.implies.append(tag_ref)
            parent_tag.write_to_db(db_manager.mongo)
            return redirect(url_for('edit_tag', tag_name=tag_name))
    return render_template('admin-pages/lib-man/tag-man/edit-tag.html', add_implication_form=add_implication_form, tag=tag, tags_collection=tags_collection)


#Library item edit page
@app.route('/admin/lib-man/lib-edit/<item_id>', methods=['GET', 'POST'])
@login_required(role="Admin")
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


#Page for editing an item and it's tags
#curretnly in use
#need to recalculate impl
@app.route('/admin/lib-man/<item_id>', methods=['GET', 'POST'])
@login_required(role="Admin")
def edit_item(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    item.recalculate_implied_tags(db_manager.mongo)
    attributes = item.attributes
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
    return render_template('admin-pages/lib-man/edit-item.html', attributes=attributes, form=form, item=item, item_id=item_id,
                           Tag=Tag, tags_collection=tags_collection)


#function for removing a tag from an item
#checked OK
@app.route('/admin/lib-man/item-remove-tag/<item_id>/<tag_name>',methods=['GET', 'POST'])
@login_required(role="Admin")
def item_remove_tag(item_id, tag_name):
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    for tag_ref in item.tags:
        if tag_ref.tag_id == tag.id:
            item.remove_tag(tag_ref)
            item.write_to_db(db_manager.mongo)
            item.recalculate_implied_tags(db_manager.mongo)
            flash('Tag deleted successfully! Tag implications has been recalculated.')
    return redirect(url_for('edit_item', item_id=item_id))

#Function for adding an implicaiton to a tag
# no longer used 
@app.route('/admin/lib-man/tag-man/implication-add/<tag_name>/<cur_child>', methods=['GET', 'POST'])
@login_required(role="Admin")
def implication_add(tag_name, cur_child):
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices=[(tag['name'], tag['name']) for tag in db_manager.mongo.db.tags.find()]

    parent_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    child_tag = Tag.search_for_by_name(db_manager.mongo, add_implication_form.select_child.data)

    if add_implication_form.validate_on_submit():
        if add_implication_form.select_child.data is tag_name:
            flash("A tag cannot imply itself!")
            return redirect(url_for('implication_add', tag_name=tag_name, cur_child=cur_child))
        elif str(child_tag.id)  in cur_child:
            flash("This implication already exists!")
            return redirect(url_for('implication_add', tag_name=tag_name, cur_child=cur_child))
        else:
            tag_ref = TagReference(child_tag.id)
            parent_tag.implies.append(tag_ref)
            parent_tag.write_to_db(db_manager.mongo)
            return redirect(url_for('edit_tag', tag_name=tag_name))
    return render_template('admin-pages/lib-man/tag-man/edit-tag.html', add_implication_form=add_implication_form, tag=tag, tags_collection=tags_collection)


# Function for deleting the tag (not removing it from the item)
# checked OK
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
                implication_dropped += 1        # need to add user notification
    flash('Tag: ' + str(tag_name) + ' dropped, ' + str(implication_dropped) + ' implications are affected.')
    return redirect(url_for('all_tags'))

#Page for creating an implication
#checked OK
@app.route('/admin/lib-man/tag-man/create-impl', methods=['GET', 'POST'])
@login_required(role="Admin")
def create_impl():
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

        '''
        print(parent_tag)
        items_to_recalculate = Item.search_for_by_tag(db_manager.mongo, parent_tag)
        print(items_to_recalculate)
        for item in items_to_recalculate:
            print(item.recalculate_implied_tags(db_manager.mongo))

        '''
        
        for item in db_manager.mongo.db.items.find():
            this_item = Item.from_dict(item)
            this_item.recalculate_implied_tags(db_manager.mongo)
        
        flash('Implication added successfully, all items implication are updated')
        
        return redirect(url_for('all_impl'))
    return render_template('admin-pages/lib-man/tag-man/create-implication.html', form=form)


#Funciton for deleting an implication rule on Tag's detail page
@app.route('/admin/lib-man/tag-man/rule-delete/<tag_name>')
@login_required(role="Admin")
def rule_delete(tag_name):
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag.implies = []
    tag.write_to_db(db_manager.mongo)
    flash('The implications for tag '+ tag_name + ' has been cleared')
    return redirect(url_for('edit_tag',tag_name=tag_name))

#Funciton for deleting an implication rule on Tag Implication page
@app.route('/admin/lib-man/tag-man/impl_delete/<tag_name>')
@login_required(role="Admin")
def impl_delete(tag_name):
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag.implies = []
    tag.write_to_db(db_manager.mongo)
    flash('The implications for tag '+ tag_name + ' has been deleted')
    return render_template('admin-pages/lib-man/tag-man/all-impl.html',  tags_collection=tags_collection)

#Page for updating Name or Description of an item
#checked OK
@app.route('/admin/lib-man/item-update-attrib/<item_id>/<attrib_name>', methods=['GET', 'POST'])
@login_required(role="Admin")
def item_update_attrib(item_id, attrib_name):
    form = updateAttribForm()
    item = db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0]
    if form.validate_on_submit():
        if attrib_name == 'name':
            item_name_attrib = AttributeOption.search_for_by_name(db_manager.mongo, "name")
            item_exists = Item.search_for_by_attribute(db_manager.mongo, item_name_attrib, form.attrib_value.data)
            if item_exists:
                flash('An item with the same name already exists!')
                return redirect(url_for('item_update_attrib', item_id=item_id, attrib_name=attrib_name))
        update_attrib = {attrib_name: form.attrib_value.data}
        item['attributes'].update(update_attrib)
        Item.from_dict(item).write_to_db(db_manager.mongo)
        flash('Item updated')
        return redirect(url_for('edit_item', item_id=item_id, attrib_name=attrib_name))
    return render_template('admin-pages/lib-man/item-add-attrib.html', form=form, attrib_name=attrib_name)



#Page for creating an item
#checked OK
@app.route('/admin/lib-man/create-item', methods=['GET', 'POST'])
@login_required(role="Admin")
def create_item():
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
            new_instance = Instance([],[])
            new_item = Item({"name": form.title.data, "description": form.description.data}, [add_tag], [new_instance])
            new_item.write_to_db(db_manager.mongo)
            new_item.recalculate_implied_tags(db_manager.mongo)
            return redirect(url_for('all_items'))
        else:
            flash('the item: ' + form.title.data + ' already exists')
            return redirect(url_for('create_item'))
    return render_template('admin-pages/lib-man/create-item.html', form=form)



# -------------------------------------------
#   Error pages, can be futher implemented
# -------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('admin-pages/error.html')


@app.errorhandler(500)
def page_not_found(e):
    return render_template('admin-pages/error.html')


#if __name__=='__main__':
#    app.run(debug=True)


