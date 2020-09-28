import abc
from enum import IntEnum
from typing import Dict, Optional, List, Union

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo


class AttributeTypes(IntEnum):
    Invalid = 0
    SingleLineString = 1
    MultiLineString = 2
    SingleLineInteger = 3
    Picture = 4
    # TODO: Add more supported types, such as pictures, UUID and some other stuff


class Attribute(metaclass=abc.ABCMeta):
    attrib_type: AttributeTypes
    option_id: ObjectId

    def __init__(self, option_id: Union['AttributeOption', ObjectId], attrib_type: AttributeTypes):
        if isinstance(option_id, ObjectId):
            self.option_id = option_id
        else:
            if option_id.attribute_type != attrib_type:
                raise ValueError("Expected Attribute Types to match")
            self.option_id = option_id.id

        self.attrib_type = attrib_type

    @staticmethod
    def from_dict(dict_value: Dict) -> 'Attribute':

        if "option_id" not in dict_value or dict_value["option_id"] is None:
            raise ValueError("Requires an option_id field")
        option_id = dict_value["option_id"]

        if "attrib_type" not in dict_value or dict_value["attrib_type"] is None:
            raise ValueError("Requires an attrib_type field")
        attrib_type = dict_value["attrib_type"]

        value = dict_value["value"]

        if attrib_type == AttributeTypes.Invalid:
            raise ValueError("Requires valid attrib_type")
        elif attrib_type == AttributeTypes.SingleLineString:
            return SingleLineStringAttribute(option_id, value)
        elif attrib_type == AttributeTypes.MultiLineString:
            return MultiLineStringAttribute(option_id, value)
        elif attrib_type == AttributeTypes.SingleLineInteger:
            return SingleLineIntegerAttribute(option_id, value)
        elif attrib_type == AttributeTypes.Picture:
            return PictureAttribute(option_id, value)

    @abc.abstractmethod
    def to_dict(self) -> Dict:
        return {"option_id": self.option_id, "attrib_type": self.attrib_type}


class SingleLineStringAttribute(Attribute):
    text: str

    def __init__(self, option_id: Union['AttributeOption', ObjectId], text: str):
        super().__init__(option_id, AttributeTypes.SingleLineString)
        self.text = text

    def to_dict(self) -> Dict:
        return {**super().to_dict(), "value": self.text}


class MultiLineStringAttribute(Attribute):
    text: List[str]

    def __init__(self, option_id: Union['AttributeOption', ObjectId], text: List[str]):
        super().__init__(option_id, AttributeTypes.MultiLineString)
        self.text = text

    def to_dict(self) -> Dict:
        return {**super().to_dict(), "value": self.text}


class SingleLineIntegerAttribute(Attribute):
    val: int

    def __init__(self, option_id: Union['AttributeOption', ObjectId], val: int):
        super().__init__(option_id, AttributeTypes.SingleLineInteger)
        self.val = val

    def to_dict(self) -> Dict:
        return {**super().to_dict(), "value": self.val}


class PictureAttribute(Attribute):
    picture_file_id: ObjectId

    def __init__(self, option_id: Union['AttributeOption', ObjectId], picture_file_id: ObjectId):
        super().__init__(option_id, AttributeTypes.Picture)
        self.picture_file_id = picture_file_id

    def to_dict(self) -> Dict:
        return {**super().to_dict(), "value": self.picture_file_id}


class AttributeOption:
    id: ObjectId = None
    hidden: bool = False
    attribute_name: str = None
    attribute_type: AttributeTypes = AttributeTypes.Invalid

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.attrib_options.create_index([("attribute_name", pymongo.ASCENDING)], unique=True)

    def __init__(self, attribute_name: str, attribute_type: AttributeTypes, hidden: bool = False):
        self.id = None
        self.hidden = hidden
        self.attribute_name = attribute_name
        self.attribute_type = attribute_type

    @staticmethod
    def from_dict(value_dict: Dict) -> 'AttributeOption':
        cls = AttributeOption("", AttributeTypes.Invalid)

        if "attribute_name" not in value_dict or value_dict["attribute_name"] is None:
            raise ValueError("the dict must contain a non null 'attribute_name'")

        if "attribute_type" not in value_dict or value_dict["attribute_type"] is None:
            raise ValueError("the dict must contain a non null 'attribute_type'")

        cls.id = value_dict["_id"]
        cls.hidden = ("hidden" in value_dict and value_dict["hidden"])
        cls.attribute_name = value_dict["attribute_name"]
        cls.attribute_type = AttributeTypes(value_dict["attribute_type"])

        return cls

    def to_dict(self) -> Dict:
        result = {
            "attribute_name": self.attribute_name.lower(),
            "attribute_type": int(self.attribute_type)
        }

        if self.hidden:
            result["hidden"] = True

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

        self.hidden = new_item_attribute.hidden
        self.attribute_name = new_item_attribute.attribute_name
        self.attribute_name = new_item_attribute.attribute_name

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.attrib_options.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, attribute_name: str) -> Optional['AttributeOption']:
        result = mongo.db.attrib_options.find_one({"attribute_name": attribute_name.lower()})
        if result is None:
            return None
        return AttributeOption.from_dict(result)
