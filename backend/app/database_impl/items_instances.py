from typing import Dict, List, Union, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo

from app.database_impl.attrib_options import AttributeOption, Attribute
from app.database_impl.relations import Relation, RelationOption
from app.database_impl.tags import Tag, TagReference


class Item:
    """
    A class to represent an item in the library
    """

    id: ObjectId = None
    """
    The item's unique id
    """

    hidden: bool = False
    """
    Determines if the item is hidden from the user library page
    """

    attributes: List[Attribute]
    """
    A list of the item's attributes
    """

    tags: List[TagReference] = []
    """
    A list of the item's tags
    """

    implied_tags: List[TagReference] = []
    """
    A list of the item's implied tags
    """

    instances: List['Instance'] = []
    """
    A list of all instances of the item
    """

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.items.create_index([("hidden", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.items.create_index([("tags.tag_id", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.items.create_index([("implied_tags.tag_id", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.items.create_index([("attributes.option_id", pymongo.ASCENDING)], unique=False, sparse=True)

    # NOTE: attributes must conform an ItemAttributeOption, however that is not checked here
    def __init__(self, attributes: List[Attribute], tags: List[TagReference], instances: List['Instance'], hidden: bool = False):
        self.id = None
        self.hidden = hidden
        self.attributes = attributes
        self.tags = tags
        self.implied_tags = []
        self.instances = instances

    def get_attributes_by_option(self, option: Union[AttributeOption, ObjectId]) -> List[Attribute]:
        if isinstance(option, AttributeOption):
            option = option.id

        return [a for a in self.attributes if a.option_id == option]

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        result = {
            "attributes": [a.to_dict() for a in self.attributes],
            "tags": [t.tag_id for t in self.tags],
            "implied_tags": [i.tag_id for i in self.implied_tags],
            "instances": [inst.to_dict() for inst in self.instances]
        }
        if self.hidden:
            result["hidden"] = True

        if self.id is not None:
            result["_id"] = self.id

        return result

    def remove_tag(self, tag: TagReference):
        """
        Removes a tag from an item

        Parameters
        ----------
            tag
                The tag to be removed

        Returns
        -------
            True if the tag has been removed from the item
        """
        if tag in self.tags:
            self.tags.remove(tag)
            return True
        else:
            return False

    @staticmethod
    def from_dict(value_dict: Dict) -> 'Item':
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
        cls = Item([], [], [], False)

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        cls.hidden = ("hidden" in value_dict and value_dict["hidden"])

        if "attributes" in value_dict and value_dict["attributes"] is not None:
            cls.attributes = [Attribute.from_dict(d) for d in value_dict["attributes"]]

        if "tags" in value_dict and value_dict["tags"] is not None:
            cls.tags = [TagReference(t) for t in value_dict["tags"]]

        if "implied_tags" in value_dict and value_dict["implied_tags"] is not None:
            cls.implied_tags = [TagReference(t) for t in value_dict["implied_tags"]]

        if "instances" in value_dict and value_dict["instances"] is not None:
            cls.instances = [Instance.from_dict(inst) for inst in value_dict["instances"]]

        return cls

    def write_to_db(self, mongo: PyMongo):
        """
        Writes the item to the database if it's `id` doesn't exist, 
        otherwise it will overwrite the item with the same `id`

        Parameters
        ----------
            mongo
                The mongo database
        """
        if self.id is None:
            self.id = mongo.db.items.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.items.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        """
        Updates an item in the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the item's id is None
            False if the item does not exist in the database
            True if the item was updated
        """
        if self.id is None:
            return False

        new_data = mongo.db.items.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_item = Item.from_dict(new_data)

        self.hidden = new_item.hidden
        self.attributes = new_item.attributes
        self.tags = new_item.tags
        self.implied_tags = new_item.implied_tags
        self.instances = new_item.instances

        return True

    def recalculate_implied_tags(self, mongo: PyMongo, instances: bool = False, inherit: bool = True):
        """
        Recalculates the implied tags

        Parameters
        ----------
            mongo
                The mongo database
            instances
                If true, then also recalculate the implied of all the instances
            inherit
                If true and a tag is on all instances of an object it will be implied on the item

        Returns
        -------
            True if successfull, False otherwise
        """
        if instances:
            self.recalculate_instance_implied_tags(mongo, None)
        else:
            if not self.update_from_db(mongo):
                return False
        self.implied_tags = []

        # get implied from relations
        relations = mongo.db.relations.find({"item_id": self.id})
        relations = [Relation.from_dict(r) for r in relations]

        relation_options = mongo.db.relation_options.find({"_id": {"$in": [r.option_id for r in relations]}})
        relation_options = [RelationOption.from_dict(r) for r in relation_options]

        self.implied_tags = [implied for option in relation_options for implied in option.implies]

        # traverse implication DAG
        to_search = set(t.tag_id for t in self.tags).union(t.tag_id for t in self.implied_tags)
        searched = set(to_search)

        while to_search:
            top_level = mongo.db.tags.find({"_id": {"$in": list(to_search)}})
            to_search = set()
            if top_level is None:
                break

            tags = [Tag.from_dict(tag) for tag in top_level]

            for tag in tags:
                for implied in tag.implies:
                    if implied.tag_id not in searched:
                        searched.add(implied.tag_id)
                        to_search.add(implied.tag_id)
                        self.implied_tags.append(implied)

        if inherit:
            possibilities = set()

            for inst in self.instances:
                possibilities.intersection_update(set(inst.tags).union(inst.implied_tags))

            self.implied_tags.extend(possibilities)

        self.write_to_db(mongo)
        return True

    # returns true if successful, false otherwise
    def recalculate_instance_implied_tags(self, mongo: PyMongo, index: Optional[Union[int, List[int]]] = None):
        """
        Recalculates the implied tags for instances

        Parameters
        ----------
            mongo
                The mongo database
            index

        Returns
        -------
            True if successfull, False otherwise
        """
        if not self.update_from_db(mongo):
            return False

        if index is None:
            to_visit = range(0, len(self.instances))
        elif isinstance(index, int):
            to_visit = [index]
        else:
            to_visit = index

        for i in to_visit:
            inst = self.instances[i]

            # get implied from relations
            relations = mongo.db.relations.find({"instance_id": inst.id})
            relations = [Relation.from_dict(r) for r in relations]

            relation_options = mongo.db.relation_options.find({"_id": {"$in": [r.option_id for r in relations]}})
            relation_options = [RelationOption.from_dict(r) for r in relation_options]

            inst.implied_tags = [implied for option in relation_options for implied in option.implies]

            # traverse implication DAG
            to_search = set(t.tag_id for t in inst.tags).union(t.tag_id for t in inst.implied_tags)
            searched = set(to_search)

            while to_search:
                top_level = mongo.db.tags.find({"_id": {"$in": list(to_search)}})
                to_search = set()
                if top_level is None:
                    break

                tags = [Tag.from_dict(tag) for tag in top_level]

                for tag in tags:
                    for implied in tag.implies:
                        if implied.tag_id not in searched:
                            searched.add(implied.tag_id)
                            to_search.add(implied.tag_id)
                            inst.implied_tags.append(implied)

            self.write_to_db(mongo)
            return True

    def delete_from_db(self, mongo: PyMongo) -> bool:
        """
        Removes an item from the database

        Parameters
        ----------
            mongo
                The mongo database

        Returns
        -------
            False if the item does not exist, or has not been deleted
            True if the the item has been deleted
        """
        if self.id is None:
            return False

        return mongo.db.items.delete_one({"_id": self.id}).deleted_count == 1
    
    def hide(self, mongo: PyMongo) -> bool:
        """
        A function to toggle between an item being hidden and visible in the user library

        Attributes
        ----------
            mongo
                The mongo database
        """
        if self.hidden is True:
            self.hidden = False
        else:
            self.hidden = True
        self.write_to_db(mongo)

    @staticmethod
    def search_for_by_tag(mongo: PyMongo, tag_ref: Union[Tag, TagReference]) -> List['Item']:
        """
        Finds all items with a specific tag

        Parameters
        ----------
            mongo
                The mongo database
            tag_ref
                The tag to be searched by

        Returns
        -------
            A list of all items with the specified tag
        """
        if isinstance(tag_ref, Tag):
            tag_ref = TagReference(tag_ref)

        result = mongo.db.items.find({"$or": [{"tags": {"$elemMatch": {"$eq": tag_ref.tag_id}}},
                                              {"implied_tags": {"$elemMatch": {"$eq": tag_ref.tag_id}}}]})
        if result is None:
            return []

        return [Item.from_dict(i) for i in result]

    @staticmethod
    def search_for_by_attribute(mongo: PyMongo, attrib_option: AttributeOption, value) -> List['Item']:
        """
        Finds all items with a specific attribute

        Parameters
        ----------
            mongo
                The mongo database
            attrib_option
                The attribute to be searched by

        Returns
        -------
            A list of all items with the specified attibute
        """
        result = mongo.db.items.find({"attributes": {"$elemMatch": { "option_id": attrib_option.id, "value": value }}})

        if result is None:
            return []

        return [Item.from_dict(i) for i in result]


class Instance:
    """
    An item can have instances, such as a book having an instance per physical copy, or it could have none, 
    in the case of a digital resource.
    """

    id: ObjectId = None
    """
    Unique instance id
    """

    hidden: bool = False
    """
    The instance may be hidden from users
    """

    attributes: List[Attribute]
    """
    A list of attributes associated with the instance
    """

    tags: List[TagReference] = []
    """
    A list of tags associated with the instance
    """

    implied_tags: List[TagReference] = []
    """
    A list of all the instance's implied tags
    """

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.items.create_index([("instances.hidden", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.items.create_index([("instances.tags.tag_id", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.items.create_index([("instances.implied_tags.tag_id", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.items.create_index([("instances.attributes.option_id", pymongo.ASCENDING)], unique=False, sparse=True)

    def __init__(self, attributes: List[Attribute], tags: List[TagReference], hidden: bool = False):
        self.id = ObjectId()
        self.hidden = hidden
        self.attributes = attributes
        self.tags = tags
        self.implied_tags = []

    def to_dict(self) -> Dict:
        """
	    Serialising the data structure into a MongoDB compliant dictionary for use in PyMongo functions

        Returns
        -------
            The MongoDB compliant data structure
        """
        result = {
            "attributes": [a.to_dict() for a in self.attributes],
            "tags": [t.tag_id for t in self.tags],
            "implied_tags": [t.tag_id for t in self.implied_tags]
        }

        if self.hidden:
            result["hidden"] = True

        if self.id is None:
            self.id = ObjectId()

        result["_id"] = self.id

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> 'Instance':
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
        cls = Instance([], [], False)

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        cls.hidden = ("hidden" in value_dict and value_dict["hidden"])

        if "attributes" in value_dict and value_dict["attributes"] is not None:
            cls.attributes = [Attribute.from_dict(a) for a in value_dict["attributes"]]

        if "tags" in value_dict and value_dict["tags"] is not None:
            cls.tags = [TagReference(t) for t in value_dict["tags"]]

        if "implied_tags" in value_dict and value_dict["implied_tags"] is not None:
            cls.implied_tags = [TagReference(t) for t in value_dict["implied_tags"]]

        return cls
