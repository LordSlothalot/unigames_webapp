from __future__ import annotations

from enum import IntEnum
from typing import List, Dict, Optional

import pymongo
from bson import ObjectId
from flask_pymongo import PyMongo


class TagParameterTypes(IntEnum):
    # The value needs to be set at another level
    NeedOverride = -1
    # An error has occurred
    Invalid = 0
    # Supports single integers being stored in the argument
    Integer = 1
    # Supports single reals being stored in the argument
    Real = 2
    # Supports a range of integers being stored in the argument (max can equal min, eqv to Integer)
    IntegerRange = 3
    # Supports a range of reals being stored in the argument (max can equal min, eqv to Integer)
    RealRange = 4
    # Supports a string from a set of valid options being stored in the argument
    Enumerated = 5
    # Supports a string being stored in the argument
    String = 6
    # TODO Consider a range option that support conditions like: i % 2 == 0 (is even)
    #      or possibly where it supports either ranges or sets, so [1,5] and {1,2,4,5} can both fit


class TagParameter:
    index: int = None
    type: TagParameterTypes = TagParameterTypes.Invalid

    def __new_numeric(self, min_value, max_value) -> TagParameter:
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError("min must be <= max")

        self.min_value = min_value
        self.max_value = max_value

        return self

    @staticmethod
    def new_integer(index: int, min_value: int = None, max_value: int = None) -> TagParameter:
        cls = TagParameter()

        cls.index = index
        cls.type = TagParameterTypes.Integer

        return cls.__new_numeric(min_value, max_value)

    @staticmethod
    def new_real(index: int, min_value: float = None, max_value: float = None) -> TagParameter:
        cls = TagParameter()

        cls.index = index
        cls.type = TagParameterTypes.Real

        return cls.__new_numeric(min_value, max_value)

    @staticmethod
    def new_integer_range(index: int, min_value: int = None, max_value: int = None) -> TagParameter:
        cls = TagParameter()

        cls.index = index
        cls.type = TagParameterTypes.IntegerRange

        return cls.__new_numeric(min_value, max_value)

    @staticmethod
    def new_real_range(index: int, min_value: float = None, max_value: float = None) -> TagParameter:
        cls = TagParameter()

        cls.index = index
        cls.type = TagParameterTypes.RealRange

        return cls.__new_numeric(min_value, max_value)

    @staticmethod
    def new_enum(index: int, options: List[str]) -> TagParameter:
        cls = TagParameter()

        cls.index = index
        cls.type = TagParameterTypes.Enumerated

        cls.options = options

        return cls

    @staticmethod
    def new_string(index: int) -> TagParameter:
        cls = TagParameter()

        cls.index = index
        cls.type = TagParameterTypes.String

        return cls

    @staticmethod
    def from_dict(value_dict: Dict) -> TagParameter:
        cls = TagParameter()

        if "type" not in value_dict or "index" not in value_dict:
            raise ValueError("dict must have 'type' and 'index' keys")

        cls.type = TagParameterTypes(value_dict["type"])
        cls.index = value_dict["index"]

        if cls.type == TagParameterTypes.Invalid:
            raise ValueError("can not construct with invalid type")
        elif cls.type == TagParameterTypes.Integer \
                or cls.type == TagParameterTypes.Real \
                or cls.type == TagParameterTypes.IntegerRange \
                or cls.type == TagParameterTypes.RealRange:

            if "min_value" in value_dict and value_dict["min_value"] is not None:
                cls.min_value = value_dict["min_value"]
            else:
                cls.min_value = None

            if "max_value" in value_dict and value_dict["max_value"] is not None:
                cls.max_value = value_dict["max_value"]
            else:
                cls.max_value = None

        elif cls.type == TagParameterTypes.Enumerated:
            cls.options = value_dict["enum"]
        elif cls.type == TagParameterTypes.String:
            pass
        else:
            raise ValueError("can not construct with unknown type")

        return cls

    def to_dict(self) -> Optional[Dict]:
        result = {"index": self.index, "type": int(self.type)}

        if self.type == TagParameterTypes.Invalid:
            raise ValueError("can not construct with invalid type")
        elif self.type == TagParameterTypes.Integer \
                or self.type == TagParameterTypes.Real \
                or self.type == TagParameterTypes.IntegerRange \
                or self.type == TagParameterTypes.RealRange:

            if self.min_value is not None:
                result["min_value"] = self.min_value
            if self.max_value is not None:
                result["max_value"] = self.max_value

        elif self.type == TagParameterTypes.Enumerated:
            result["enum"] = self.options
        elif self.type == TagParameterTypes.String:
            pass
        else:
            raise ValueError("can not construct with unknown type")

        return result


class TagParameterImpl:
    index: int = None
    type: TagParameterTypes = TagParameterTypes.Invalid

    def __new_numeric_range(self, param: TagParameter, min_value, max_value):
        if (min_value is not None and max_value is not None and min_value > max_value) \
                or (min_value is not None and param.min_value is not None and min_value < param.min_value) \
                or (max_value is not None and param.max_value is not None and max_value > param.max_value):
            raise ValueError("min must be <= max, and [min,max] must lie in range defined by the param")

        self.min_value = min_value
        self.max_value = max_value

        return self

    def __new_numeric(self, param: TagParameter, value):
        if (value is not None and param.max_value is not None and value > param.max_value) \
                or (value is not None and param.min_value is not None and value < param.min_value):
            raise ValueError("value must be in [min,max]")

        self.value = value

        return self

    @staticmethod
    def new_needs_override(param: TagParameter) -> TagParameterImpl:
        cls = TagParameterImpl()
        cls.index = param.index
        cls.type = TagParameterTypes.NeedOverride

        return cls

    @staticmethod
    # None means any
    def new_integer(param: TagParameter, value: int = None) -> TagParameterImpl:
        cls = TagParameterImpl()

        if param.type != TagParameterTypes.Integer:
            raise ValueError("Type of parm must match method")

        cls.index = param.index
        cls.type = param.type

        return cls.__new_numeric(param, value)

    @staticmethod
    # None means any
    def new_real(param: TagParameter, value: float = None) -> TagParameterImpl:
        cls = TagParameterImpl()

        if param.type != TagParameterTypes.Real:
            raise ValueError("Type of parm must match method")

        cls.index = param.index
        cls.type = param.type

        return cls.__new_numeric(param, value)

    @staticmethod
    # none means, either (-inf, max], [min, inf), or (-inf, inf)
    def new_integer_range(param: TagParameter, min_value: int = None, max_value: int = None) -> TagParameterImpl:
        cls = TagParameterImpl()

        if param.type != TagParameterTypes.IntegerRange:
            raise ValueError("Type of parm must match method")

        cls.index = param.index
        cls.type = param.type

        return cls.__new_numeric_range(param, min_value, max_value)

    @staticmethod
    # none means, either (-inf, max], [min, inf), or (-inf, inf)
    def new_real_range(param: TagParameter, min_value: float = None, max_value: float = None) -> TagParameterImpl:
        cls = TagParameterImpl()

        if param.type != TagParameterTypes.RealRange:
            raise ValueError("Type of parm must match method")

        cls.index = param.index
        cls.type = param.type

        return cls.__new_numeric_range(param, min_value, max_value)

    @staticmethod
    # None means any
    def new_enum(param: TagParameter, value: Optional[str]) -> TagParameterImpl:
        cls = TagParameterImpl()

        if param.type != TagParameterTypes.Enumerated:
            raise ValueError("Type of parm must match method")

        if value is not None and value not in param.options:
            raise ValueError("Enum value must either be None or in the defined set by the param")

        cls.index = param.index
        cls.type = param.type

        cls.value = value
        return cls

    @staticmethod
    # None means any
    def new_string(param: TagParameter, value: Optional[str]) -> TagParameterImpl:
        cls = TagParameterImpl()

        if param.type != TagParameterTypes.String:
            raise ValueError("Type of parm must match method")

        cls.index = param.index
        cls.type = param.type

        cls.value = value
        return cls

    @staticmethod
    def from_dict(value_dict: Dict) -> TagParameterImpl:
        cls = TagParameterImpl()

        if "type" not in value_dict or "index" not in value_dict:
            raise ValueError("dict must have 'type' and 'index' keys")

        cls.index = value_dict["index"]
        cls.type = TagParameterTypes(value_dict["type"])

        if cls.type == TagParameterTypes.Invalid:
            raise ValueError("The param type must not be invalid")
        elif cls.type == TagParameterTypes.Integer \
                or cls.type == TagParameterTypes.Real \
                or cls.type == TagParameterTypes.Enumerated \
                or cls.type == TagParameterTypes.String:
            cls.value = value_dict["value"]
        elif cls.type == TagParameterTypes.IntegerRange \
                or cls.type == TagParameterTypes.RealRange:
            cls.min_value = value_dict["min-value"]
            cls.max_value = value_dict["max-value"]
        else:
            raise ValueError("The param type must not be unknown")

        return cls

    def to_dict(self) -> Optional[Dict]:
        result = {"index": self.index, "type": int(self.type)}

        if self.type == TagParameterTypes.Invalid:
            raise ValueError("can not make dict from invalid type")
        elif self.type == TagParameterTypes.Integer \
                or self.type == TagParameterTypes.Real \
                or self.type == TagParameterTypes.Enumerated \
                or self.type == TagParameterTypes.String:

            if self.value is not None:
                result["value"] = self.value

        elif self.type == TagParameterTypes.IntegerRange \
                or self.type == TagParameterTypes.RealRange:

            if self.min_value is not None:
                result["min_value"] = self.min_value
            if self.max_value is not None:
                result["max_value"] = self.max_value

        else:
            return None

        return result


class TagImplication:
    implied_id: ObjectId = None
    parameters: List[TagParameterImpl] = []

    def __init__(self, implied_id: ObjectId, parameters: List[TagParameterImpl]):
        self.implied_id = implied_id

        if parameters is not None:
            self.parameters = parameters
        else:
            self.parameters = []

    @staticmethod
    def from_dict(value_dict: Dict) -> TagImplication:
        cls = TagImplication(None, None)

        if "implied_id" not in value_dict:
            raise ValueError("the dict must contain 'implied_id'")

        if "implied_id" in value_dict and value_dict["implied_id"] is not None:
            cls.implied_id = value_dict["implied_id"]

        if "parameters" in value_dict and "parameters" in value_dict:
            cls.parameters = [TagParameterImpl.from_dict(d) for d in value_dict["parameters"] if d is not None]

        return cls

    def to_dict(self) -> Dict:
        return {
            "implied_id": self.implied_id,
            "parameters": [p.to_dict() for p in self.parameters]
        }


class Tag:
    id: ObjectId = None
    name: str = None
    parameters: List[TagParameter] = []
    implies: List[TagImplication] = []

    @staticmethod
    def init_indices(mongo: PyMongo):
        mongo.db.tags.create_index([("name", pymongo.ASCENDING)], unique=True)

    def __init__(self, name: str, parameters: List[TagParameter], implies: List[TagImplication]):
        self.id = None
        self.name = name
        self.parameters = parameters
        self.implies = implies

    def to_dict(self) -> Dict:
        result = {
            "name": self.name,
            "parameters": [p.to_dict() for p in self.parameters],
            "implies": [i.to_dict() for i in self.implies]
        }
        if self.id is not None:
            result["_id"] = self.id
        return result

    @staticmethod
    def from_dict(value_dict: Dict) -> Tag:
        cls = Tag(None, None, None)

        if "name" not in value_dict:
            raise ValueError("the dict must contain 'name'")

        cls.name = value_dict["name"]

        if "_id" in value_dict:
            cls.id = value_dict["_id"]

        if "parameters" in value_dict and value_dict["parameters"] is not None:
            cls.parameters = [TagParameter.from_dict(d) for d in value_dict["parameters"]]

        if "implies" in value_dict and value_dict["implies"] is not None:
            cls.implies = [TagImplication.from_dict(d) for d in value_dict["implies"]]

        return cls

    def write_to_db(self, mongo: PyMongo):
        if self.id is None:
            self.id = mongo.db.tags.insert_one(self.to_dict()).inserted_id
        else:
            mongo.db.tags.find_one_and_replace({"_id": self.id}, self.to_dict())

    # Returns True if the update worked, else False, usually meaning it's no longer there
    def update_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        new_data = mongo.db.tags.find_one({"_id": self.id})

        if new_data is None:
            return False

        new_tag = Tag.from_dict(new_data)

        self.name = new_tag.name
        self.parameters = new_tag.parameters
        self.implies = new_tag.implies

    def delete_from_db(self, mongo: PyMongo) -> bool:
        if self.id is None:
            return False

        return mongo.db.tags.delete_one({"_id": self.id}).deleted_count == 1

    @staticmethod
    def search_for_by_name(mongo: PyMongo, name: str) -> Optional[Tag]:
        result = mongo.db.tags.find_one({"name": name})
        if result is None:
            return None
        return Tag.from_dict(result)
