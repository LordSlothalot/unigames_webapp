from flask import Flask

from app.database_impl.manager import DatabaseManager

app = Flask(__name__)


#app.config dictionary is a general-purpose place to store config variables
#The SECRET_KEY is needed for loading flask-wtf forms.
app.config['SECRET_KEY'] = 'this should be a password but whatever'

db_manager = DatabaseManager(app)
db_manager.test()


from app import routes
