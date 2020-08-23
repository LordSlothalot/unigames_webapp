from app import app, db_manager
from flask import render_template, url_for
from app.forms import LoginForm

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
    tags_collection = db_manager.mongo.db.tags

    return render_template('admin-pages/lib.html', items=items, tags_collection=tags_collection, ObjectId=ObjectId, list=list)

    '''
    for looking up tags based on items
    for item in items:
        for tags in item['tags']:
            find_tags = tags_collection.find( { "_id" : tags['tag_id'] }) 
            for find_tag in find_tags:
                print(find_tag['name'])
    '''

@app.route('/admin/lib-edit/<id>')
def lib_edit(id):
    print(id)
    item = db_manager.mongo.db.items.find({"_id" : ObjectId(id)})[0]
    '''
    item_name_attrib = AttributeOption("name", AttributeTypes.SingleLineString)
    items = Item.search_for_by_attribute(db_manager.mongo, item_name_attrib, "Bob's Grand Adventure")
    '''
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
    return render_template('admin-pages/lib-edit.html', tags_collection=tags_collection, title=title, implied_tags=implied_tags, book=book, author=author, item_tags=item_tags, item_implied_tags=item_implied_tags, instances=instances,description=description)

@app.route('/admin/instance-edit/<id>')
def instance_edit(id):
    instance = db_manager.mongo.db.instances.find({"_id" : ObjectId(id)})[0]
    if not instance:
        print('there is no current instace')    #to be further implemented
    tags_collection = db_manager.mongo.db.tags
    return render_template('admin-pages/instance-edit.html', instance=instance, tags_collection=tags_collection)



#-------------------------------------------
#   Error pages, can be futher implemented
#-------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return 'Page not found 404.'

@app.errorhandler(500)
def page_not_found(e):
    return 'Page not found 500.'