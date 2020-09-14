from bson.objectid import ObjectId
from flask import render_template, url_for, redirect

from app import app, db_manager
from app.database_impl.attrib_options import AttributeOption, AttributeTypes
from app.database_impl.items_instances import Item, Instance
from app.database_impl.tags import Tag, TagReference
from app.forms import LoginForm, newEntryForm, addTagForm, addInstanceForm, createTagForm, addTagImplForm, \
    addAttribForm, updateAttribForm, createAttribForm

# -------------------------------------------
#     User pages
# -------------------------------------------

tags_collection = db_manager.mongo.db.tags
attrib_collection = db_manager.mongo.db.attrib_options


@app.route('/')
@app.route('/index')
def index():
    return render_template('user-pages/index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # you can make use of the submitted form data now
        print(form.email.data)
        print(form.password.data)
        return 'Need to connect to a database here'
    # pass the form as a parameter as frontend renders
    return render_template('user-pages/login.html', form=form)


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


# -------------------------------------------
#     Admin pages
# -------------------------------------------
@app.route('/admin')
def admin():
    name = "Michale"

    return render_template('admin-pages/home.html', name=name)

#Library management page
@app.route('/admin/lib')
def lib():
    items = db_manager.mongo.db.items.find().limit(10)

    return render_template('admin-pages/lib-man/lib.html', items=items, tags_collection=tags_collection,
                           ObjectId=ObjectId, list=list)


#Library item edit page
@app.route('/admin/lib-man/lib-edit/<item_id>', methods=['GET', 'POST'])
def lib_edit(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id": ObjectId(item_id)})[0])
    attributes = item.attributes
    instances = Instance.search_for_by_item(db_manager.mongo, ObjectId(item_id))

    return render_template('admin-pages/lib-man/lib-edit.html', attributes=attributes, instances=instances, item=item,
                           Tag=Tag, tags_collection=tags_collection)


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

#Library add item page
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
            add_tag = TagReference(found_tag.id)
            new_item = Item({"name": form.title.data, "author": form.author.data}, [add_tag])
            new_item.write_to_db(db_manager.mongo)
            new_item.recalculate_implied_tags(db_manager.mongo)

            return redirect(url_for('lib'))
        else:
            return 'the item already exists'
    return render_template('admin-pages/lib-man/lib-add.html', form=form)

#Function for delete an item on library page
@app.route('/admin/lib-man/lib-delete/<item_id>')
def lib_delete(item_id):
    item = Item.from_dict(db_manager.mongo.db.items.find({"_id" : ObjectId(item_id)})[0])
    item.delete_from_db(db_manager.mongo)
    return redirect(url_for('lib'))

#Tag management page
@app.route('/admin/lib-man/tag-man/tag-all', methods=['GET', 'POST'])
def tag_all():
    #all_relations = db_manager.mongo.db.relation_options
    all_tags = db_manager.mongo.db.tags.find()
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices=[(tag['name'], tag['name']) for tag in all_tags]
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form, add_implication_form=add_implication_form, tags_collection=tags_collection)

@app.route('/admin/lib-man/tag-man/tag-create', methods=['GET', 'POST'])
def tag_create():
    print("create tag")
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    if create_tag_form.validate_on_submit():
        tag_exists = Tag.search_for_by_name(db_manager.mongo, create_tag_form.name.data)
        if tag_exists is None:
            new_tag = Tag(create_tag_form.name.data, [])
            new_tag.write_to_db(db_manager.mongo)
            return redirect(url_for('tag_all'))
        else:
            return 'the tag already exists'
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form, add_implication_form=add_implication_form, tags_collection=tags_collection)

# Function for deleting the tag (not removing it from the item)
@app.route('/admin/lib-man/tag-man/tag-delete/<tag_name>')
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
    return redirect(url_for('tag_all'))

#Function for adding an implicaiton rule
@app.route('/admin/lib-man/tag-man/implication-add/<tag_name>/<cur_child>', methods=['GET', 'POST'])
def implication_add(tag_name, cur_child):
    all_tags = db_manager.mongo.db.tags.find()
    create_tag_form = createTagForm()
    add_implication_form = addTagImplForm()
    add_implication_form.select_child.choices=[(tag['name'], tag['name']) for tag in all_tags]
    parent_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    child_tag = Tag.search_for_by_name(db_manager.mongo, add_implication_form.select_child.data)

    if add_implication_form.validate_on_submit():
        if add_implication_form.select_child.data is tag_name:
            return "A tag cannot imply itself!"
        elif str(child_tag.id)  in cur_child:
            return "This implication already exists!"
        else:
            tag_ref = TagReference(child_tag.id)
            parent_tag.implies.append(tag_ref)
            parent_tag.write_to_db(db_manager.mongo)
            return redirect(url_for('tag_all'))
    return render_template('admin-pages/lib-man/tag-man/tag-all.html', create_tag_form=create_tag_form, add_implication_form=add_implication_form, tags_collection=tags_collection)

@app.route('/admin/lib-man/tag-man/implication-delete/<tag_name>')
def implication_delete(tag_name):
    tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
    tag.implies = []
    tag.write_to_db(db_manager.mongo)
    return redirect(url_for('tag_all'))


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


#-------------------
#Probable garbage

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
