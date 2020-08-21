from typing import List, Dict, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo


class User:
    id: ObjectId
    display_name: str
    role_ids: List[ObjectId]


class User:
    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.users.create_index([("display_name", pymongo.ASCENDING)], unique=False, sparse=False)

    def __init__(self, display_name: str, role_ids: List[ObjectId]):
        self.id = None
        self.display_name = display_name
        self.role_ids = role_ids

    def to_dict(self) -> Dict:
        result = {
            "display_name": self.display_name,
            "roles": self.role_ids
        }

        if self.id is not None:
            result["_id"] = self.id

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> User:
        cls = User(None, None)

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "display_name" not in value_dict or value_dict["display_name"] is None:
            raise ValueError("User must have display_name")
        cls.display_name = value_dict["display_name"]

        if "role_ids" in value_dict and value_dict["role_ids"] is not None:
            cls.role_ids = value_dict["role_ids"]

        return cls

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
        self.role_ids = new_user.role_ids

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.users.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_display_name(mongo: PyMongo, display_name: str) -> Optional[User]:
        result = mongo.db.users.find_one({"display_name": display_name})
        if result is None:
            return None

        return User.from_dict(result)
