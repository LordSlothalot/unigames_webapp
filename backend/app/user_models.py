from flask import session
from uuid import uuid4
from werkzeug.security import check_password_hash
from app import login_manager, db_manager

mongo = db_manager.mongo

class User:
    def __init__(self, email, password, first_name, last_name, role, _id=None):
        self.email = email
        self.password = password
        self._id = uuid4().hex if _id is None else _id
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        # user level field
    
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
    def register(cls, email, password, first_name, last_name, role):
        user = cls.get_by_email(email)
        if user is None:
            new_user = cls(email, password, first_name, last_name, role)
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
            "last_name": self.last_name,
			"role": self.role
        }

    def save_to_mongo(self):
        mongo.db.Users.insert(self.json())

# @login.user_loader
# def load_user(id):
#     u = mongo.db.Users.find_one({'_id': id})
#     if not u:
#         return None
#     return User(id=u['_id'])

@login_manager.user_loader
def load_user(id):
    return User.get_by_id(id)