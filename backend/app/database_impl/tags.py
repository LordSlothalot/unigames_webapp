from enum import IntEnum
from typing import List, Dict, Optional, Union

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo


class TagReference:
    tag_id: ObjectId = None

    def __init__(self, tag: Union[ObjectId, 'Tag']):
        if isinstance(tag, Tag):
            self.tag_id = tag.id
        else:
            self.tag_id = tag


class Tag:
    """
    A class to represent tags associated with items
    """

    id: ObjectId = None
    """
    The tag id
    """

    name: str = None
    """
    The name of the tag
    """

    implies: List[TagReference] = []
    """
    List of tags this tag implies
    """

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.tags.create_index([("name", pymongo.ASCENDING)], unique=True)

    def __init__(self, name: str, implies: List[TagReference]):
        self.id = None
        self.name = name
        self.implies = implies

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        result = {
            "name": self.name.lower(),
            "implies": [i.tag_id for i in self.implies]
        }
        if self.id is not None:
            result["_id"] = self.id
        return result

    def remove_implied_tag(self, tag: TagReference):
        """
        Removes a tag from the list of implied tags

        Attribute
        ---------
            tag
                The implied tag to be removed

        Returns
        -------
            True if the implied tag has been removed
        """
        if tag in self.implies:
            self.implies.remove(tag)
            return True
        else:
            return False

    @staticmethod
    def from_dict(value_dict: Dict) -> 'Tag':
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
        cls = Tag("", [])

        if "name" not in value_dict:
            raise ValueError("the dict must contain 'name'")

        cls.name = value_dict["name"]

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "implies" in value_dict and value_dict["implies"] is not None:
            cls.implies = [TagReference(d) for d in value_dict["implies"]]

        return cls

    def write_to_db(self, mongo: PyMongo):
        """
        Writes the tag to the database if it's `id` doesn't exist, 
        otherwise it will overwrite the tag with the same `id`

        Parameters
        ----------
            mongo
                The mongo database
        """
        if self.id is None:
            self.id = mongo.db.tags.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.tags.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        """
        Updates a tag in the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the tag's id is None
            False if the tag does not exist in the database
        """
        if self.id is None:
            return False

        new_data = mongo.db.tags.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_tag = Tag.from_dict(new_data)

        self.name = new_tag.name
        self.implies = new_tag.implies

    def delete_from_db(self, mongo: PyMongo) -> bool:
        """
        Removes a tag from the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the tag does not exist, or has not been deleted
            True if the the tag has been deleted
        """
        if self.id is None:
            return False

        return mongo.db.tags.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, name: str) -> Optional['Tag']:
        """
        Finds a tag in the database with the specified name

        Parameters
        ----------
            mongo
                The mongo database
            tag_ref
                The tag to be searched by

        Returns
        -------
            None if a tag has not been found
            The tag if it exists in the database
        """
        result = mongo.db.tags.find_one({"name": name.lower()})
        if result is None:
            return None
        return Tag.from_dict(result)
