import abc
from enum import IntEnum
from typing import Dict, Optional, List, Union

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo


class AttributeTypes(IntEnum):
    """
    Enum class for attibute types
    """
    Invalid = 0
    SingleLineString = 1
    MultiLineString = 2
    SingleLineInteger = 3
    Picture = 4
    # TODO: Add more supported types, such as pictures, UUID and some other stuff


class Attribute(metaclass=abc.ABCMeta):
    """
    A class for item attibutes
    """

    attrib_type: AttributeTypes
    """
    The type of attribute
    """

    option_id: ObjectId
    value = None

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
        """
	    Deserialising a MongoDB compliant dictionary into a data structure for use in python functions

        Parameters
        ----------
            value_dict
                The dictionary to be deserialised

        Returns
        -------
            The deserialised data structure
        """
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
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        return {"option_id": self.option_id, "attrib_type": self.attrib_type}


class SingleLineStringAttribute(Attribute):
    """
    A class to represent single line string attributes
    """

    def __init__(self, option_id: Union['AttributeOption', ObjectId], text: str):
        super().__init__(option_id, AttributeTypes.SingleLineString)
        self.value = text

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        return {**super().to_dict(), "value": self.value}


class MultiLineStringAttribute(Attribute):
    """
    A class to represent multi line string attributes
    """

    def __init__(self, option_id: Union['AttributeOption', ObjectId], text: List[str]):
        super().__init__(option_id, AttributeTypes.MultiLineString)
        self.value = text

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        return {**super().to_dict(), "value": self.value}


class SingleLineIntegerAttribute(Attribute):
    """
    A class to represent single line integer attributes
    """

    def __init__(self, option_id: Union['AttributeOption', ObjectId], val: int):
        super().__init__(option_id, AttributeTypes.SingleLineInteger)
        self.value = val

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        return {**super().to_dict(), "value": self.value}


class PictureAttribute(Attribute):
    """
    A class to represent a picture attribute
    """

    def __init__(self, option_id: Union['AttributeOption', ObjectId], picture_file_id: ObjectId):
        super().__init__(option_id, AttributeTypes.Picture)
        self.value = picture_file_id

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        return {**super().to_dict(), "value": self.value}


class AttributeOption:
    id: ObjectId = None
    """
    The attribute id
    """

    hidden: bool = False
    """
    Hides the attribute if True
    """

    attribute_name: str = None
    """
    The name of the attribute
    """

    attribute_type: AttributeTypes = AttributeTypes.Invalid
    """
    The type of attribute
    """

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
        """
	    Deserialising a MongoDB compliant dictionary into a data structure for use in python functions

        Parameters
        ----------
            value_dict
                The dictionary to be deserialised

        Returns
        -------
            The deserialised data structure
        """
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
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
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
        """
        Writes the attribute to the database if it's `id` doesn't exist, 
        otherwise it will overwrite the attribute with the same `id`

        Parameters
        ----------
            mongo
                the mongo database
        """
        if self.id is None:
            self.id = mongo.db.attrib_options.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.attrib_options.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        """
        Updates the attribute in the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the attribute's id is None
            False if the attribute does not exist in the database
        """
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
        """
        Removes the attribute from the database

        Parameters
        ----------
            mongo
                The database

        Returns
        -------
            False if the attribute does not exist, or has not been deleted
            True if the the attribute has been deleted
        """
        if self.id is None:
            return False

        return mongo.db.attrib_options.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, attribute_name: str) -> Optional['AttributeOption']:
        """
        Finds an attribute in the database with the specified name

        Parameters
        ----------
            mongo
                The mongo database
            name
                The name to be searched by

        Returns
        -------
            None if an attribute has not been found
            The attribute if it exists in the database
        """
        result = mongo.db.attrib_options.find_one({"attribute_name": attribute_name.lower()})
        if result is None:
            return None
        return AttributeOption.from_dict(result)
