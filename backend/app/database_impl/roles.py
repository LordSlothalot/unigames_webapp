from enum import Enum
from typing import Dict, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo


class Permissions(Enum):
    """
    A class for permissions users hold
    """

    CanEditItems = "can_edit_items"
    """
    Users with this permission can edit items
    """

    CanEditUsers = "can_edit_users"
    """
    Users with this permission can edit other users
    """
    
    CanViewHidden = "can_view_hidden"
    """
    Users with this permission can view hidden items
    """
    

    def __str__(self):
        return self.value


class Role:
    """
    A class to represent roles of users
    """

    id: ObjectId
    """
    Role id
    """

    name: str
    """
    Role name
    """

    priority: int
    """
    Role priority. A high number is high priority
    """

    permissions: Dict[Permissions, bool]
    """
    A dictionary containing role permissions.
    """

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.roles.create_index([("name", pymongo.ASCENDING)], unique=True, sparse=False)

    def __init__(self, name: str, priority: int, permissions: Dict[Permissions, bool]):
        self.id = None
        self.name = name
        self.priority = priority
        self.permissions = permissions

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
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
        """
        Writes the role to the database if it's `id` doesn't exist, 
        otherwise it will overwrite the role with the same `id`

        Attributes
        ----------
            self
                the role to be updated
            mongo
                the database
        """
        if self.id is None:
            self.id = mongo.db.roles.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.roles.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        """
        Updates a role in the database

        Attributes
        ----------
            self
                the role to be updated
            mongo
                the database

        Returns
        -------
            False if the role's id is None
            False if the role does not exist in the database
        """
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
        """
        Removes a role from the database

        Attributes
        ----------
            self
                the role to be deleted
            mongo
                the database

        Returns
        -------
            False if the role does not exist, or has not been deleted
            True if the the role has been deleted
        """
        if self.id is None:
            return False

        return mongo.db.roles.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, name: str) -> Optional['Role']:
        """
        Finds a role in the database with the specified name

        Attributes
        ----------
            mongo
                the database
            tag_ref
                the name to be searched by

        Returns
        -------
            None if a role has not been found
            The role if it exists in the database
        """
        result = mongo.db.roles.find_one({"name": name})
        if result is None:
            return None

        return Role.from_dict(result)
    
    @classmethod
    def create_new(cls, mongo: PyMongo, name: str, priority: int, can_view_hidden: bool, can_edit_users: bool, can_edit_items: bool):
        """
        Create a new role and inserts it into the database

        Attributes
        ----------
            mongo
                the database
            name
                the name of the role
            priority
                the role priority
            can_view_hidden
                Users with this role can view hidden items
            can_edit_users
                Users with this role can edit other users
            can_edit_items
                Users with this role can edit items

        Returns
        -------
            True if the role has been created, else false
        """
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
