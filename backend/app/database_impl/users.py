from typing import List, Dict, Optional

from flask import session
from uuid import uuid4
from werkzeug.security import check_password_hash
from app import login_manager

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo
from app.database_impl.roles import Role



class User:
    id: ObjectId
    display_name: str
    role: Role
    email: str
    password: str
    first_name: str
    last_name: str

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.users.create_index([("display_name", pymongo.ASCENDING)], unique=False, sparse=False)

    def __init__(self, display_name: str, role: Role, email: str, password: str, first_name: str, last_name: str):
        self.id = None
        self.display_name = display_name
        self.role = role
        self.email = email
        self.password = password
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
        return self.display_name
        
    @staticmethod
    def login_valid(mongo: PyMongo, email, password):
        verify_user = User.search_for_by_email(mongo, email)
        if verify_user is not None:
            return check_password_hash(verify_user.password, password)
        return False
        
    @staticmethod
    def check_password(password_hash, password):
        return check_password_hash(password_hash, password)

    def to_dict(self) -> Dict:
        result = {
            "display_name": self.display_name, 
            "role": self.role, 
            "email": self.email, 
            "password": self.password, 
            "first_name": self.first_name, 
            "last_name": self.last_name 
        }

        if self.id is not None:
            result["_id"] = self.id

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> 'User':
        cls = User("", [], "", "", "", "")

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "display_name" not in value_dict or value_dict["display_name"] is None:
            raise ValueError("User must have display_name")
        cls.display_name = value_dict["display_name"]

        if "role" in value_dict and value_dict["role"] is not None:
            cls.role = value_dict["role"]
            
        if "email" in value_dict and value_dict["email"] is not None:
            cls.email = value_dict["email"]
            
        if "password" in value_dict and value_dict["password"] is not None:
            cls.password = value_dict["password"]
        
        if "first_name" in value_dict and value_dict["first_name"] is not None:
            cls.first_name = value_dict["first_name"]
            
        if "last_name" in value_dict and value_dict["last_name"] is not None:
            cls.last_name = value_dict["last_name"]


        return cls
        
    @classmethod
    def register(cls, mongo: PyMongo, display_name, email, password, first_name, last_name):
        user = cls.search_for_by_email(mongo, email)
        if user is None:
            admin = Role.search_for_by_name(mongo, "admin")
            new_user = cls(display_name, admin, email, password, first_name, last_name)
            new_user.id = mongo.db.users.insert_one(new_user.to_dict()).inserted_id
            session['email'] = email
            return True
        else:
            return False

    def write_to_db(self, mongo: PyMongo):
        if self.id is None:
            self.id = mongo.db.users.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.users.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        new_data = mongo.db.users.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_user = User.from_dict(new_data)

        self.display_name = new_user.display_name
        self.role = new_user.role
        self.email = new_user.email
        self.password = new_user.password
        self.first_name = new_user.first_name
        self.last_name = new_user.last_name

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.users.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_display_name(mongo: PyMongo, display_name: str) -> Optional['User']:
        result = mongo.db.users.find_one({"display_name": display_name})
        if result is None:
            return None

        return User.from_dict(result)
        
    @staticmethod
    def search_for_by_email(mongo: PyMongo, email: str) -> Optional['User']:
        result = mongo.db.users.find_one({"email": email})
        if result is None:
            return None

        return User.from_dict(result)
        
    @staticmethod
    def get_by_id(mongo:PyMongo, id):
        result = mongo.db.users.find_one({"_id": id})
        if result is None:
            return None

        return User.from_dict(result)

