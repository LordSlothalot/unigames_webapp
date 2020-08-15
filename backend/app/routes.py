from app import app
from flask import render_template
from app.forms import LoginForm

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        #you can make use of the submitted form data now
        print(form.email.data)
        print(form.password.data)
        return 'Need to connect to a database here'
    #pass the form as a parameter as frontend renders
    return render_template('login.html', form = form)




#Error pages, can be futher implemented
@app.errorhandler(404)
def page_not_found(e):
    return 'Page not found 404.'

@app.errorhandler(500)
def page_not_found(e):
    return 'Page not found 500.'
