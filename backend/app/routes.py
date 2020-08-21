from app import app, mongo, login
from flask import Flask, render_template, url_for, redirect, request, flash
from app.forms import LoginForm, RegistrationForm
from app.user_models import User
from flask_pymongo import PyMongo
from flask_login import LoginManager, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods = ['GET', 'POST'])
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
            loguser = User(find_user['_id'], find_user['email'], find_user['password'], find_user['first_name'], find_user['last_name'])
            login_user(loguser)
            flash('You have been logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            return "Login Unsuccessful"
    return render_template('login.html', form = form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        first_name = "testname"
        last_name = "testname2"
        password = generate_password_hash(form.password.data)
        find_user =  User.get_by_email(email)
        if find_user is None:
            User.register(email, password, first_name, last_name)
            flash(f'Account created for {form.email.data}!', 'success')
            return redirect(url_for('index'))
        else:
            flash(f'Account already exists for {form.email.data}!', 'success')
    return render_template('register.html', title='Register', form=form)



#Error pages, can be futher implemented
@app.errorhandler(404)
def page_not_found(e):
    return 'Page not found 404.'

@app.errorhandler(500)
def page_not_found(e):
    return 'Page not found 500.'

if __name__=='__main__':
    app.run(debug=True)