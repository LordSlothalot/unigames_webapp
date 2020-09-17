from __future__ import annotations

from enum import IntEnum
from typing import Dict, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo


class AttributeTypes(IntEnum):
    Invalid = 0
    SingleLineString = 1
    MultiLineString = 2
    SingleLineInteger = 3
    # TODO: Add more supported types, such as pictures, UUID and some other stuff


class AttributeOption:
    id: ObjectId = None
    attribute_name: str = None
    attribute_type: AttributeTypes = AttributeTypes.Invalid

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.attrib_options.create_index([("attribute_name", pymongo.ASCENDING)], unique=True)

    def __init__(self, attribute_name: str, attribute_type: AttributeTypes):
        self.id = None
        self.attribute_name = attribute_name
        self.attribute_type = attribute_type

    @staticmethod
    def from_dict(value_dict: Dict) -> AttributeOption:
        cls = AttributeOption(None, None)

        if "attribute_name" not in value_dict or value_dict["attribute_name"] is None:
            raise ValueError("the dict must contain a non null 'attribute_name'")

        if "attribute_type" not in value_dict or value_dict["attribute_type"] is None:
            raise ValueError("the dict must contain a non null 'attribute_type'")

        cls.id = value_dict["_id"]
        cls.attribute_name = value_dict["attribute_name"]
        cls.attribute_type = AttributeTypes(value_dict["attribute_type"])

        return cls

    def to_dict(self) -> Dict:
        result = {
            "attribute_name": self.attribute_name.lower(),
            "attribute_type": int(self.attribute_type)
        }
        if self.id is not None:
            result["_id"] = self.id

        return result

    def write_to_db(self, mongo: PyMongo):
        if self.id is None:
            self.id = mongo.db.attrib_options.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.attrib_options.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        new_data = mongo.db.attrib_options.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_item_attribute = AttributeOption.from_dict(new_data)

        self.attribute_name = new_item_attribute.attribute_name
        self.attribute_name = new_item_attribute.attribute_name

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.attrib_options.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, attribute_name: str) -> Optional[AttributeOption]:
        result = mongo.db.attrib_options.find_one({"attribute_name": attribute_name.lower()})
        if result is None:
            return None
        return AttributeOption.from_dict(result)
