from app import app, db_manager
from flask import render_template, url_for, redirect
from app.forms import LoginForm, newEntryForm, addTagForm

from app.database_impl.attrib_options import AttributeOption, AttributeTypes
from app.database_impl.items_instances import Item, TagReference, Instance
from app.database_impl.relations import RelationOption, Relation
from app.database_impl.roles import Role, Permissions
from app.database_impl.tags import Tag, TagParameter, TagImplication, TagParameterImpl
from app.database_impl.users import User

from bson.objectid import ObjectId

#-------------------------------------------
#     User pages
#-------------------------------------------

tags_collection = db_manager.mongo.db.tags

@app.route('/')
@app.route('/index')
def index():
    return render_template('user-pages/index.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        #you can make use of the submitted form data now
        print(form.email.data)
        print(form.password.data)
        return 'Need to connect to a database here'
    #pass the form as a parameter as frontend renders
    return render_template('user-pages/login.html', form = form)


@app.route('/library')
def library():
    #get urls for images, they are supposed to be retrieved from the db
    dungeons_pic = url_for('static', filename='img/games/dungeons.jpg')
    stars_pic = url_for('static', filename='img/games/stars-without-number.jpg')
    pulp_pic = url_for('static', filename='img/games/pulp-cthulhu.jpg')
    #pass them to the rendering page
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

#-------------------------------------------
#     Admin pages
#-------------------------------------------
@app.route('/admin')
def admin():
    return render_template('admin-pages/home.html')

@app.route('/admin/lib')
def lib():

    items = db_manager.mongo.db.items.find().limit(10)

    return render_template('admin-pages/lib-man/lib.html', items=items, tags_collection=tags_collection, ObjectId=ObjectId, list=list)


@app.route('/admin/lib-man/lib-edit/<id>')
def lib_edit(id):
    print(id)
    item = db_manager.mongo.db.items.find({"_id" : ObjectId(id)})[0]
    '''
    item_name_attrib = AttributeOption("name", AttributeTypes.SingleLineString)
    items = Item.search_for_by_attribute(db_manager.mongo, item_name_attrib, "Bob's Grand Adventure")
    '''
    #The following is actually not needed, just pass the item to the html

    #get attribute name 
    title = item['attributes']['name']
    #get attribute author
    author = item['attributes']['author']

    #get attribute tags
    item_tags = item['tags']
    #get attribute implied tags
    implied_tags = item['implied_tags']
    #get attribute implied tags
    item_implied_tags = item['implied_tags']

    
    #get instances
    instances = Instance.search_for_by_item(db_manager.mongo, ObjectId(id))
    if not instances:
        print('there is no current instance')   #to be further implemented

    
    tags_collection = db_manager.mongo.db.tags

    book = "abc"
    
    genre = "gene"
    tags = "tags"
    description = "description"
    return render_template('admin-pages/lib-man/lib-edit.html', item=item, tags_collection=tags_collection, title=title, implied_tags=implied_tags, book=book, author=author, item_tags=item_tags, item_implied_tags=item_implied_tags, instances=instances,description=description)

@app.route('/admin/lib-man/instance-edit/<id>')
def instance_edit(id):
    instance = db_manager.mongo.db.instances.find({"_id" : ObjectId(id)})[0]
    if not instance:
        print('there is no current instace')    #to be further implemented
    tags_collection = db_manager.mongo.db.tags
    return render_template('admin-pages/lib-man/instance-edit.html', instance=instance, tags_collection=tags_collection)


@app.route('/admin/lib-man/lib-add', methods=['GET', 'POST'])
def lib_add():
    form = newEntryForm()
    if form.validate_on_submit():
        title = form.title.data
        author = form.author.data
        description = form.Description.data     # to be added
        #search for an item with the same title
        item_name_attrib = AttributeOption.search_for_by_name(db_manager.mongo, "name")
        item_exists = Item.search_for_by_attribute(db_manager.mongo, item_name_attrib, title)
        if not item_exists:
            new_item = Item({"name": title, "author" : author}, [])
            new_item.write_to_db(db_manager.mongo)
            print('db written successful')
            return redirect(url_for('lib'))
        else:
            print('the item already exists')
    return render_template('admin-pages/lib-man/lib-add.html', form=form)



@app.route('/admin/lib-man/tag-add/<item_id>', methods=['GET', 'POST'])
def tag_add(item_id):
    form = addTagForm()
    item = db_manager.mongo.db.items.find({"_id" : ObjectId(item_id)})[0]
    tags_collection = db_manager.mongo.db.tags
    print(item)

    if form.validate_on_submit():
        tag_name = form.selection.data
        found_tag = Tag.search_for_by_name(db_manager.mongo, tag_name)
        add_tag = {'tag_id': found_tag.id, 'parameters': []}
        item['tags'].append(add_tag)
        print(item)
        
        Item.from_dict(item).write_to_db(db_manager.mongo)
        Item.from_dict(item).recalculate_implied_tags(db_manager.mongo)
        print('updated')
        return redirect(url_for('lib_edit', id=item_id))
        
        
    return render_template('admin-pages/lib-man/tag-add.html', form=form, tags_collection=tags_collection, item=item)


#-------------------------------------------
#   Error pages, can be futher implemented
#-------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return 'Page not found 404.'

@app.errorhandler(500)
def page_not_found(e):
    return 'Page not found 500.'