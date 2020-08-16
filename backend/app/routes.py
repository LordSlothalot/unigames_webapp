from app import app
from flask import render_template, url_for
from app.forms import LoginForm


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
    name = "Michale"

    return render_template('admin-pages/home.html', name=name)

@app.route('/admin/lib')
def lib():
    return render_template('admin-pages/lib.html')


#-------------------------------------------
#   Error pages, can be futher implemented
#-------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return 'Page not found 404.'

@app.errorhandler(500)
def page_not_found(e):
    return 'Page not found 500.'