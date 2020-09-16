from flask import Flask

from flask_pymongo import PyMongo
from flask_login import LoginManager
from flask_bootstrap import Bootstrap

from app.database_impl.manager import DatabaseManager

app = Flask(__name__)

#app.config dictionary is a general-purpose place to store config variables
#The SECRET_KEY is needed for loading flask-wtf forms.
app.config['SECRET_KEY'] = 'this should be a password but whatever'

# paris-test
#app.config["MONGO_URI"] = "mongodb://localhost:27017/unigames_webapp_db"
#mongo = PyMongo(app)
#login_manager = LoginManager(app)
#login_manager.login_view = 'login'
#from app import routes


login_manager = LoginManager(app)
login_manager.login_view = 'login'

db_manager = DatabaseManager(app)
db_manager.test()

#create Bootstrap object for easy form implementation
bootstrap = Bootstrap(app)

from app import routes
