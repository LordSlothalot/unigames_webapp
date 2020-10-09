from typing import Dict, List, Union, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo

from app.database_impl.attrib_options import AttributeOption, Attribute
from app.database_impl.relations import Relation, RelationOption
from app.database_impl.tags import Tag, TagReference


class Item:
    id: ObjectId = None
    hidden: bool = False
    attributes: List[Attribute]
    tags: List[TagReference] = []
    implied_tags: List[TagReference] = []
    instances: List['Instance'] = []

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
        if tag in self.tags:
            self.tags.remove(tag)
            return True
        else:
            return False

    @staticmethod
    def from_dict(value_dict: Dict) -> 'Item':
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
        if self.id is None:
            self.id = mongo.db.items.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.items.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
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

    # if 'instances' is true, then also recalculate the implied of all the instances
    # if 'inherit' is true, then if a tag is on all instance of an object it will be implied on the item
    # returns true if successful, false otherwise
    def recalculate_implied_tags(self, mongo: PyMongo, instances: bool = False, inherit: bool = True):
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
        if self.id is None:
            return False

        return mongo.db.items.delete_one({"_id": self.id}).deleted_count == 1
    
    def hide(self, mongo: PyMongo) -> bool:
        if self.hidden is True:
            self.hidden = False
        else:
            self.hidden = True
        self.write_to_db(mongo)

    @staticmethod
    def search_for_by_tag(mongo: PyMongo, tag_ref: Union[Tag, TagReference]) -> List['Item']:
        if isinstance(tag_ref, Tag):
            tag_ref = TagReference(tag_ref)

        result = mongo.db.items.find({"$or": [{"tags": {"$elemMatch": {"$eq": tag_ref.tag_id}}},
                                              {"implied_tags": {"$elemMatch": {"$eq": tag_ref.tag_id}}}]})
        if result is None:
            return []

        return [Item.from_dict(i) for i in result]

    @staticmethod
    def search_for_by_attribute(mongo: PyMongo, attrib_option: AttributeOption, value) -> List['Item']:
        result = mongo.db.items.find({"attributes": {"$elemMatch": { "option_id": attrib_option.id, "value": value }}})

        if result is None:
            return []

        return [Item.from_dict(i) for i in result]


class Instance:
    id: ObjectId = None
    hidden: bool = False
    attributes: List[Attribute]
    tags: List[TagReference] = []
    implied_tags: List[TagReference] = []

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
