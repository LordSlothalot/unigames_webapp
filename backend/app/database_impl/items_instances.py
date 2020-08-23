from typing import Dict, List

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo

from app.database_impl.attrib_options import AttributeOption
from app.database_impl.relations import Relation, RelationOption
from app.database_impl.tags import TagParameterImpl, Tag


class TagReference:
    pass


class TagReference:
    tag_id: ObjectId = None
    parameters: List[TagParameterImpl] = []

    def __init__(self, tag_id: ObjectId, parameters: List[TagParameterImpl]):
        self.tag_id = tag_id

        if parameters is not None:
            self.parameters = parameters

    @staticmethod
    def from_dict(value_dict: Dict) -> TagReference:
        cls = TagReference(None, None)

        if "tag_id" not in value_dict:
            raise ValueError("the dict must contain 'tag_id'")

        if "tag_id" in value_dict and value_dict["tag_id"] is not None:
            cls.tag_id = value_dict["tag_id"]

        if "parameters" not in value_dict or "parameters" not in value_dict:
            cls.parameters = [TagParameterImpl.from_dict(d) for d in value_dict["parameters"]]

        return cls

    def to_dict(self) -> Dict:
        return {
            "tag_id": self.tag_id,
            "parameters": [p.to_dict() for p in self.parameters]
        }


class Item:
    id: ObjectId = None
    attributes: Dict = {}
    tags: List[TagReference] = []
    implied_tags: List[TagReference] = []


class Item:
    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.items.create_index([("tags.tag_id", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.items.create_index([("implied_tags.tag_id", pymongo.ASCENDING)], unique=False, sparse=True)

    # NOTE: attributes must conform an ItemAttributeOption, however that is not checked here
    def __init__(self, attributes: Dict, tags: List[TagReference]):
        self.id = None
        self.attributes = attributes
        self.tags = tags
        self.implied_tags = []

    def to_dict(self) -> Dict:
        result = {
            "attributes": self.attributes,
            "tags": [t.to_dict() for t in self.tags],
            "implied_tags": [t.to_dict() for t in self.implied_tags]
        }
        if self.id is not None:
            result["_id"] = self.id

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> Item:
        cls = Item(None, None)

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "attributes" in value_dict and value_dict["attributes"] is not None:
            cls.attributes = value_dict["attributes"]

        if "tags" in value_dict and value_dict["tags"] is not None:
            cls.tags = [TagReference.from_dict(t) for t in value_dict["tags"]]

        if "implied_tags" in value_dict and value_dict["implied_tags"] is not None:
            cls.implied_tags = [TagReference.from_dict(t) for t in value_dict["implied_tags"]]

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

        self.attributes = new_item.attributes
        self.tags = new_item.tags
        self.implied_tags = new_item.implied_tags

    def recalculate_implied_tags(self, mongo: PyMongo):
        self.update_from_db(mongo)
        self.implied_tags = []

        # get implied from relations
        relations = mongo.db.relations.find({"item_id": self.id})
        relations = [Relation.from_dict(r) for r in relations]

        relation_options = mongo.db.relation_options.find({"_id": {"$in": [r.option_id for r in relations]}})
        relation_options = [RelationOption.from_dict(r) for r in relation_options]

        relation_implied: Dict[ObjectId, Dict[int, TagParameterImpl]] = {}

        for ro in relation_options:
            for implied in ro.implies:
                if implied.implied_id not in relation_implied:
                    relation_implied[implied.implied_id] = {}

                for para in implied.parameters:
                    relation_implied[implied.implied_id][para.index] = para

        for r in relations:
            for implied in r.implies:
                if implied.implied_id not in relation_implied:
                    relation_implied[implied.implied_id] = {}

                for para in implied.parameters:
                    relation_implied[implied.implied_id][para.index] = para

        self.implied_tags = [TagReference(implied_id, [p for p in parameters.values()]) for implied_id, parameters in
                             relation_implied.items()]

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
                    if implied.implied_id not in searched:
                        searched.add(implied.implied_id)
                        to_search.add(implied.implied_id)
                        self.implied_tags.append(TagReference(implied.implied_id, implied.parameters))

        self.write_to_db(mongo)

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.items.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_tag_id(mongo: PyMongo, tag_id: ObjectId) -> List[Item]:
        result = mongo.db.items.find({"$or": [{"tags": {"$elemMatch": {"tag_id": tag_id}}},
                                              {"implied_tags": {"$elemMatch": {"tag_id": tag_id}}}]})
        if result is None:
            return []

        return [Item.from_dict(i) for i in result]

    @staticmethod
    def search_for_by_tag_id_with_instance(mongo: PyMongo, tag_id: ObjectId) -> List[Item]:
        result = Item.search_for_by_tag_id(mongo, tag_id)

        instances = mongo.db.instances.find({"$or": [{"tags": {"$elemMatch": {"tag_id": tag_id}}},
                                                     {"implied_tags": {"$elemMatch": {"tag_id": tag_id}}}]})
        instances = [Instance.from_dict(i) for i in instances]
        instance_item_ids = [i.item_id for i in instances]

        instance_items = mongo.db.items.find({"_id": {"$in": instance_item_ids}})
        instance_items = [Item.from_dict(i) for i in instance_items]

        item_ids = set(i.id for i in result)

        for i in instance_items:
            if i.id not in item_ids:
                item_ids.add(i.id)
                result.append(i)

        return result

    @staticmethod
    def search_for_by_tag_id_with_common_instance(mongo: PyMongo, tag_id: ObjectId) -> List[Item]:
        result = Item.search_for_by_tag_id(mongo, tag_id)

        instances = mongo.db.instances.find({"$or": [{"tags": {"$elemMatch": {"tag_id": tag_id}}},
                                                     {"implied_tags": {"$elemMatch": {"tag_id": tag_id}}}]})
        instances = [Instance.from_dict(i) for i in instances]
        instance_item_ids = [i.item_id for i in instances]

        instance_items = mongo.db.items.find({"_id": {"$in": instance_item_ids}})
        instance_items = [Item.from_dict(i) for i in instance_items]

        instance_ids = set(i.id for i in instances)
        item_ids = set(i.id for i in result)

        for i in instance_items:
            if i.id not in item_ids:

                all_instances = mongo.db.instances.find({"item_id": i.id})
                all_instance_ids = set(Instance.from_dict(i).id for i in all_instances)

                if all_instance_ids.issubset(instance_ids):
                    item_ids.add(i.id)
                    result.append(i)

        return result

    @staticmethod
    def search_for_by_attribute(mongo: PyMongo, attrib_option: AttributeOption, value) -> List[Item]:
        result = mongo.db.items.find({"attributes." + str(attrib_option.attribute_name): value})

        if result is None:
            return []

        return [Item.from_dict(i) for i in result]
        



class Instance:
    id: ObjectId = None
    item_id: ObjectId = None
    attributes: Dict = {}
    tags: List[TagReference] = []
    implied_tags: List[TagReference] = []


class Instance:
    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.instances.create_index([("item_id", pymongo.ASCENDING)], unique=False, sparse=False)
        mongo.db.instances.create_index([("tags.tag_id", pymongo.ASCENDING)], unique=False, sparse=True)
        mongo.db.instances.create_index([("implied_tags.tag_id", pymongo.ASCENDING)], unique=False, sparse=True)

    def __init__(self, item_id: ObjectId, attributes: Dict, tags: List[TagReference]):
        self.id = None
        self.item_id = item_id
        self.attributes = attributes
        self.tags = tags
        self.implied_tags = []

    def to_dict(self) -> Dict:
        result = {
            "item_id": self.item_id,
            "attributes": self.attributes,
            "tags": [t.to_dict() for t in self.tags],
            "implied_tags": [t.to_dict() for t in self.implied_tags]
        }
        if self.id is not None:
            result["_id"] = self.id

        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> Instance:
        cls = Instance(None, None, None)

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "item_id" not in value_dict or value_dict["item_id"] is None:
            raise ValueError("Instance must have an 'item_id'")

        cls.item_id = value_dict["item_id"]

        if "attributes" in value_dict and value_dict["attributes"] is not None:
            cls.attributes = value_dict["attributes"]

        if "tags" in value_dict and value_dict["tags"] is not None:
            cls.tags = [TagReference.from_dict(t) for t in value_dict["tags"]]

        if "implied_tags" in value_dict and value_dict["implied_tags"] is not None:
            cls.implied_tags = [TagReference.from_dict(t) for t in value_dict["implied_tags"]]

        return cls

    def write_to_db(self, mongo: PyMongo):
        if self.id is None:
            self.id = mongo.db.instances.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.instances.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        new_data = mongo.db.instances.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_instance = Instance.from_dict(new_data)

        self.item_id = new_instance.item_id
        self.attributes = new_instance.attributes
        self.tags = new_instance.tags
        self.implied_tags = new_instance.implied_tags

    def recalculate_implied_tags(self, mongo: PyMongo):
        self.update_from_db(mongo)
        self.implied_tags = []

        # get implied from relations
        relations = mongo.db.relations.find({"instance_id": self.id})
        relations = [Relation.from_dict(r) for r in relations]

        relation_options = mongo.db.relation_options.find({"_id": {"$in": [r.option_id for r in relations]}})
        relation_options = [RelationOption.from_dict(r) for r in relation_options]

        relation_implied: Dict[ObjectId, Dict[int, TagParameterImpl]] = {}

        for ro in relation_options:
            for implied in ro.implies:
                if implied.implied_id not in relation_implied:
                    relation_implied[implied.implied_id] = {}

                for para in implied.parameters:
                    relation_implied[implied.implied_id][para.index] = para

        for r in relations:
            for implied in r.implies:
                if implied.implied_id not in relation_implied:
                    relation_implied[implied.implied_id] = {}

                for para in implied.parameters:
                    relation_implied[implied.implied_id][para.index] = para

        self.implied_tags = [TagReference(implied_id, [p for p in parameters.values()]) for implied_id, parameters in
                             relation_implied.items()]

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
                    if implied.implied_id not in searched:
                        searched.add(implied.implied_id)
                        to_search.add(implied.implied_id)
                        self.implied_tags.append(TagReference(implied.implied_id, implied.parameters))

        self.write_to_db(mongo)

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.instances.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_item(mongo: PyMongo, item_id: ObjectId) -> List[Instance]:
        result = mongo.db.instances.find({"item_id": item_id})
        if result is None:
            return []

        return [Instance.from_dict(i) for i in result]

    @staticmethod
    def search_for_by_tag_id(mongo: PyMongo, tag_id: ObjectId) -> List[Instance]:
        result = mongo.db.instances.find({"$or": [{"tags": {"$elemMatch": {"tag_id": tag_id}}},
                                                  {"implied_tags": {"$elemMatch": {"tag_id": tag_id}}}]})
        if result is None:
            return []

        return [Instance.from_dict(i) for i in result]

    @staticmethod
    def search_for_by_attribute(mongo: PyMongo, attrib_option: AttributeOption, value) -> List[Instance]:
        result = mongo.db.instances.find({"attributes." + str(attrib_option.attribute_name): value})

        if result is None:
            return []

        return [Instance.from_dict(i) for i in result]
