from app import app
from flask import Flask, render_template, url_for, redirect, request, flash, session
from app.forms import LoginForm, RegistrationForm
from flask_pymongo import PyMongo
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse
from uuid import uuid4


app.config["MONGO_URI"] = "mongodb://localhost:27017/unigames_webapp_db"

mongo = PyMongo(app)
login = LoginManager(app)
login.login_view = 'login'

class User:
    def __init__(self, email, password, first_name, last_name, _id=None):
        self.email = email
        self.password = password
        self._id = uuid4().hex if _id is None else _id
        self.first_name = first_name
        self.last_name = last_name
    
    @staticmethod
    def is_authenticated():
        return True

    @staticmethod
    def is_active():
        return True

    @staticmethod
    def is_anonymous():
        return False

    def get_id(self):
        return self._id

    @staticmethod
    def check_password(password_hash, password):
        return check_password_hash(password_hash, password)

    @classmethod
    def get_by_email(cls, email):
        data = mongo.db.Users.find_one({"email": email})
        if data is not None:
            return cls(**data)

    @classmethod
    def get_by_id(cls, _id):
        data = mongo.db.Users.find_one({"_id": _id})
        if data is not None:
            return cls(**data)

    @staticmethod
    def login_valid(email, password):
        verify_user = User.get_by_email(email)
        if verify_user is not None:
            return check_password_hash(verify_user.password, password)
        return False

    @classmethod
    def register(cls, email, password, first_name, last_name):
        user = cls.get_by_email(email)
        if user is None:
            new_user = cls(email, password, first_name, last_name)
            new_user.save_to_mongo()
            session['email'] = email
            return True
        else:
            return False

    def json(self):
        return {
            "_id": self._id,
            "email": self.email,
            "password": self.password,
            "first_name": self.first_name,
            "last_name": self.last_name
        }

    def save_to_mongo(self):
        mongo.db.Users.insert(self.json())

    @login.user_loader
    def load_user(email):
        u = mongo.db.Users.find_one({'email': email})
        if not u:
            return None
        return User(email=u['email'])



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