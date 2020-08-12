from flask import Flask


app = Flask(__name__)


#app.config dictionary is a general-purpose place to store config variables
#The SECRET_KEY is needed for loading flask-wtf forms. 
app.config['SECRET_KEY'] = 'this should be a password but whatever'

from app import routes