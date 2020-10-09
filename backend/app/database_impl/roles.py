from enum import Enum
from typing import Dict, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo


class Permissions(Enum):
    CanEditItems = "can_edit_items"
    CanEditUsers = "can_edit_users"
    CanViewHidden = "can_view_hidden"

    def __str__(self):
        return self.value


class Role:
    id: ObjectId
    name: str
    priority: int
    permissions: Dict[Permissions, bool]

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.roles.create_index([("name", pymongo.ASCENDING)], unique=True, sparse=False)

    def __init__(self, name: str, priority: int, permissions: Dict[Permissions, bool]):
        self.id = None
        self.name = name
        self.priority = priority
        self.permissions = permissions

    def to_dict(self) -> Dict:
        result = {
            "name": self.name,
            "priority": self.priority,
            "permissions": {str(p): v for p, v in self.permissions.items()}
        }

        if self.id is not None:
            result["_id"] = self.id

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> 'Role':
        cls = Role("", 0, {})

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "name" not in value_dict or value_dict["name"] is None:
            raise ValueError("Role must have name")
        cls.name = value_dict["name"]

        if "priority" not in value_dict or value_dict["priority"] is None:
            raise ValueError("Role must have priority")
        cls.priority = value_dict["priority"]

        if "permissions" in value_dict and value_dict["permissions"] is not None:
            cls.permissions = value_dict["permissions"]

        return cls

    def write_to_db(self, mongo: PyMongo):
        if self.id is None:
            self.id = mongo.db.roles.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.roles.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        new_data = mongo.db.roles.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_role = Role.from_dict(new_data)

        self.name = new_role.name
        self.priority = new_role.priority
        self.permissions = new_role.permissions

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.roles.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, name: str) -> Optional['Role']:
        result = mongo.db.roles.find_one({"name": name})
        if result is None:
            return None

        return Role.from_dict(result)
    
    @classmethod
    def create_new(cls, mongo: PyMongo, name: str, priority: int, can_view_hidden: bool, can_edit_users: bool, can_edit_items: bool):
        role = cls.search_for_by_name(mongo, name)
        if role is None:
            permissions = {}
            permissions['can_view_hidden'] = can_view_hidden
            permissions['can_edit_users'] = can_edit_users
            permissions['can_edit_items'] = can_edit_items
            new_role = cls(name, priority, permissions)
            new_role.id = mongo.db.roles.insert_one(new_role.to_dict()).inserted_id
            return True
        else:
            return False
