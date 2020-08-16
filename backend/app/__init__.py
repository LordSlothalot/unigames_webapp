from flask import Flask

from app.database_impl.manager import DatabaseManager

app = Flask(__name__)

db_manager = DatabaseManager(app)
db_manager.test()
