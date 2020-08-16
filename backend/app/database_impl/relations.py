from enum import Enum
from typing import List, Dict, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo

from app.database_impl.tags import TagImplication


class RelationOption:
    id: ObjectId = None
    name: str = None
    # Contains base parameters (if any), will be overridden/supplemented by an instance of the relation
    implies: List[TagImplication] = []


class RelationOption:
    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.relation_options.create_index([("name", pymongo.ASCENDING)], unique=True, sparse=False)
        pass

    def __init__(self, name: str, implies: List[TagImplication]):
        self.id = None
        self.name = name
        self.implies = implies

    def to_dict(self) -> Dict:
        result = {
            "name": self.name,
            "implies": [i.to_dict() for i in self.implies]
        }

        if self.id is not None:
            result["_id"] = self.id

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> RelationOption:
        cls = RelationOption(None, None)

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "name" not in value_dict or value_dict["name"] is None:
            raise ValueError("Relation Option needs a 'name'")

        cls.name = value_dict["name"]

        if "implies" in value_dict and value_dict["implies"] is not None:
            cls.implies = [TagImplication.from_dict(i) for i in value_dict["implies"]]

        return cls

    def write_to_db(self, mongo: PyMongo):
        if self.id is None:
            self.id = mongo.db.relation_options.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.relation_options.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        new_data = mongo.db.relation_options.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_relation_option = RelationOption.from_dict(new_data)

        self.name = new_relation_option.name
        self.implies = new_relation_option.implies

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.relation_options.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, name: str) -> Optional[RelationOption]:
        result = mongo.db.relation_options.find_one({"name": name})
        if result is None:
            return None

        return RelationOption.from_dict(result)


class RelationType(Enum):
    Invalid = 0
    Item = 1
    Instance = 2


class Relation:
    id: ObjectId = None
    user_id: ObjectId = None
    option_id: ObjectId = None
    relation_type: RelationType = RelationType.Invalid
    # Contains the overriding/supplementing values for the impl
    implies: List[TagImplication] = []


class Relation:
    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.relations.create_index([("user_id", pymongo.ASCENDING)], unique=False, sparse=False)
        mongo.db.relations.create_index([("item_id", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.relations.create_index([("instance_id", pymongo.ASCENDING)], unique=False, sparse=True)
        pass

    def __init__(self):
        self.id = None
        self.user_id = None
        self.option_id = None
        self.relation_type = RelationType.Invalid
        self.implies = []

    @staticmethod
    def new_item(user_id: ObjectId, option_id: ObjectId, item_id: ObjectId, implies: List[TagImplication]) -> Relation:
        cls = Relation()

        cls.id = None
        cls.user_id = user_id
        cls.option_id = option_id
        cls.relation_type = RelationType.Item
        cls.item_id = item_id
        cls.implies = implies

        return cls

    @staticmethod
    def new_instance(user_id: ObjectId, option_id: ObjectId, instance_id: ObjectId,
                     implies: List[TagImplication]) -> Relation:
        cls = Relation()

        cls.id = None
        cls.user_id = user_id
        cls.option_id = option_id
        cls.relation_type = RelationType.Instance
        cls.instance_id = instance_id
        cls.implies = implies

        return cls

    def to_dict(self) -> Dict:
        result = {
            "user_id": self.user_id,
            "option_id": self.option_id,
            "implies": [i.to_dict() for i in self.implies]
        }

        if self.id is not None:
            result["_id"] = self.id

        if self.relation_type == RelationType.Item:
            result["item_id"] = self.item_id
        elif self.relation_type == RelationType.Instance:
            result["instance_id"] = self.instance_id
        else:
            raise ValueError("Can not create dict of relation with invalid type")

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> Relation:
        cls = Relation()

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "user_id" not in value_dict or value_dict["user_id"] is None:
            raise ValueError("Relation needs a 'user_id'")

        cls.user_id = value_dict["user_id"]

        if "option_id" not in value_dict or value_dict["option_id"] is None:
            raise ValueError("Relation needs a 'option_id'")

        cls.option_id = value_dict["option_id"]

        if "implies" in value_dict and value_dict["implies"] is not None:
            cls.implies = [TagImplication.from_dict(i) for i in value_dict["implies"]]

        if "item_id" in value_dict:
            if value_dict["item_id"] is None:
                raise ValueError("Can not make relation with None 'item_id'")
            cls.item_id = value_dict["item_id"]
            cls.relation_type = RelationType.Item
        elif "instance_id" in value_dict:
            if value_dict["instance_id"] is None:
                raise ValueError("Can not make relation with None 'instance_id'")
            cls.instance_id = value_dict["instance_id"]
            cls.relation_type = RelationType.Instance
        else:
            raise ValueError("Can not make relation with neither 'item_id' or 'instance_id'")

        return cls

    def write_to_db(self, mongo: PyMongo):
        if self.id is None:
            self.id = mongo.db.relations.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.relations.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        new_data = mongo.db.relations.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_relation = Relation.from_dict(new_data)

        self.user_id = new_relation.user_id
        self.option_id = new_relation.option_id
        self.implies = new_relation.implies
        self.relation_type = new_relation.relation_type
        if new_relation.relation_type == RelationType.Item:
            self.item_id = new_relation.item_id
        elif new_relation.relation_type == RelationType.Instance:
            self.instance_id = new_relation.instance_id
        else:
            ValueError("Should never get here")

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.relations.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_user_id(mongo: PyMongo, user_id: ObjectId) -> List[Relation]:
        result = mongo.db.relations.find({"user_id": user_id})
        if result is None or not result:
            return []

        return [Relation.from_dict(r) for r in result]

    @staticmethod
    def search_for_by_item_id(mongo: PyMongo, item_id: ObjectId) -> List[Relation]:
        result = mongo.db.relations.find({"item_id": item_id})
        if result is None or not result:
            return []

        return [Relation.from_dict(r) for r in result]

    @staticmethod
    def search_for_by_instance_id(mongo: PyMongo, instance_id: ObjectId) -> List[Relation]:
        result = mongo.db.relations.find({"instance_id": instance_id})
        if result is None or not result:
            return []

        return [Relation.from_dict(r) for r in result]
