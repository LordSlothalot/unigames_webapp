from enum import Enum
from typing import List, Dict, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo

from app.database_impl.tags import TagReference


class RelationOption:
    """
    A class to represent relation options. An example of a relation option is "borrowing".
    """

    id: ObjectId = None
    """
    A relation option id
    """

    name: str = None
    """
    The name of the relation option
    """

    implies: List[TagReference] = []
    """
    A list of tags this relation option implies
    """

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.relation_options.create_index([("name", pymongo.ASCENDING)], unique=True, sparse=False)
        pass

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
            "name": self.name,
            "implies": [i.tag_id for i in self.implies]
        }

        if self.id is not None:
            result["_id"] = self.id

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> 'RelationOption':
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
        cls = RelationOption("", [])

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "name" not in value_dict or value_dict["name"] is None:
            raise ValueError("Relation Option needs a 'name'")

        cls.name = value_dict["name"]

        if "implies" in value_dict and value_dict["implies"] is not None:
            cls.implies = [TagReference(i) for i in value_dict["implies"]]

        return cls

    def write_to_db(self, mongo: PyMongo):
        """
        Writes the relation to the database if it's `id` doesn't exist, 
        otherwise it will overwrite the relation with the same `id`

        Parameters
        ----------
            mongo
                The mongo database
        """
        if self.id is None:
            self.id = mongo.db.relation_options.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.relation_options.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        """
        Updates the relation in the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the relation's id is None
            False if the relation does not exist in the database
            True if the relation was updated
        """
        if self.id is None:
            return False

        new_data = mongo.db.relation_options.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_relation_option = RelationOption.from_dict(new_data)

        self.name = new_relation_option.name
        self.implies = new_relation_option.implies

    def delete_from_db(self, mongo: PyMongo) -> bool:
        """
        Removes the relation from the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the relation does not exist, or has not been deleted
            True if the relation has been deleted
        """
        if self.id is None:
            return False

        return mongo.db.relation_options.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, name: str) -> Optional['RelationOption']:
        """
        Finds a relation in the database with the specified name

        Parameters
        ----------
            mongo
                The mongo database
            name
                The name to be searched by

        Returns
        -------
            None if a relation has not been found
            The relation if it exists in the database
        """
        result = mongo.db.relation_options.find_one({"name": name})
        if result is None:
            return None

        return RelationOption.from_dict(result)


class RelationType(Enum):
    """
    The types of relations
    """

    Invalid = 0
    Item = 1
    Instance = 2


class Relation:
    """
    A class to represent a relation between users and items or instances
    """

    id: ObjectId = None
    """
    The id of the relation
    """

    user_id: ObjectId = None
    """
    The user creating the relation
    """

    option_id: ObjectId = None
    """
    The relation option
    """

    relation_type: RelationType = RelationType.Invalid
    """
    The type of relation
    """

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

    @staticmethod
    def new_item(user_id: ObjectId, option_id: ObjectId, item_id: ObjectId) -> 'Relation':
        """
        Create a new item relation

        Parameters
        ----------
            user_id
                The user creating the relation
            option_id
                The relation option
            item_id
                The item

        Returns
        -------
            The new item relation
        """
        cls = Relation()

        cls.id = None
        cls.user_id = user_id
        cls.option_id = option_id
        cls.relation_type = RelationType.Item
        cls.item_id = item_id

        return cls

    @staticmethod
    def new_instance(user_id: ObjectId, option_id: ObjectId, instance_id: ObjectId) -> 'Relation':
        """
        Create a new instance relation

        Parameters
        ----------
            user_id
                The user creating the relation
            option_id
                The relation option
            item_id
                The instance

        Returns
        -------
            The new instance relation
        """
        cls = Relation()

        cls.id = None
        cls.user_id = user_id
        cls.option_id = option_id
        cls.relation_type = RelationType.Instance
        cls.instance_id = instance_id

        return cls

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        result = {
            "user_id": self.user_id,
            "option_id": self.option_id,
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
    def from_dict(value_dict: Dict) -> 'Relation':
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
        cls = Relation()

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "user_id" not in value_dict or value_dict["user_id"] is None:
            raise ValueError("Relation needs a 'user_id'")

        cls.user_id = value_dict["user_id"]

        if "option_id" not in value_dict or value_dict["option_id"] is None:
            raise ValueError("Relation needs a 'option_id'")

        cls.option_id = value_dict["option_id"]

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
        """
        Writes the relation to the database if it's `id` doesn't exist, 
        otherwise it will overwrite the relation with the same `id`

        Parameters
        ----------
            mongo
                The mongo database
        """
        if self.id is None:
            self.id = mongo.db.relations.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.relations.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        """
        Updates a relation in the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the relation's id is None
            False if the relation does not exist in the database
        """
        if self.id is None:
            return False

        new_data = mongo.db.relations.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_relation = Relation.from_dict(new_data)

        self.user_id = new_relation.user_id
        self.option_id = new_relation.option_id
        self.relation_type = new_relation.relation_type
        if new_relation.relation_type == RelationType.Item:
            self.item_id = new_relation.item_id
        elif new_relation.relation_type == RelationType.Instance:
            self.instance_id = new_relation.instance_id
        else:
            ValueError("Should never get here")

    def delete_from_db(self, mongo: PyMongo) -> bool:
        """
        Removes an relation from the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the relation does not exist, or has not been deleted
            True if the the relation has been deleted
        """
        if self.id is None:
            return False

        return mongo.db.relations.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_user_id(mongo: PyMongo, user_id: ObjectId) -> List['Relation']:
        """
        Finds all the relations containing a specific user id

        Parameters
        ----------
            mongo
                The mongo database
            user_id
                The user id to be searched by

        Returns
        -------
            A list of all relations with the specified user id
        """
        result = mongo.db.relations.find({"user_id": user_id})
        if result is None or not result:
            return []

        return [Relation.from_dict(r) for r in result]

    @staticmethod
    def search_for_by_item_id(mongo: PyMongo, item_id: ObjectId) -> List['Relation']:
        """
        Finds all the relations containing a specific item id

        Parameters
        ----------
            mongo
                The mongo database
            item_id
                The item id to be searched by

        Returns
        -------
            A list of all relations with the specified item id
        """
        result = mongo.db.relations.find({"item_id": item_id})
        if result is None or not result:
            return []

        return [Relation.from_dict(r) for r in result]

    @staticmethod
    def search_for_by_instance_id(mongo: PyMongo, instance_id: ObjectId) -> List['Relation']:
        """
        Finds all the relations containing a specific instance id

        Parameters
        ----------
            mongo
                The mongo database
            instance_id
                The instance id to be searched by

        Returns
        -------
            A list of all relations with the specified instance id
        """
        result = mongo.db.relations.find({"instance_id": instance_id})
        if result is None or not result:
            return []

        return [Relation.from_dict(r) for r in result]
