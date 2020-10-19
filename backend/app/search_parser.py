import abc
from enum import Enum
from typing import List, Union, Optional, Dict

from bson import ObjectId
from flask_pymongo import PyMongo

from app.database_impl.attrib_options import AttributeOption
from app.database_impl.tags import Tag


class Brackets(Enum):
    """
    An enum class used to enumerate the two types of parthenthsis 
    and to be able to just lookup their character representations
    """

    Parentheses = ["Parentheses", '(', ')']
    Curly = ["Curly", '{', '}']


class SearchStringParseError:
    """
    A base class used to repersent the a general error that might 
    be returned by the parser
    """

    def __str__(self) -> str:
        return "SearchStringParseError: "

    def __repr__(self) -> str:
        return self.__str__()


class UnexpectedCloseBracket(SearchStringParseError):
    """
    A subclass of SearchStringParseError, for the specific instance 
    where a close baracket (either } or )) was encountered in an 
    illegal/unexpected position such as '(a ::and b))'
    """

    def __init__(self, index: int, bracket: Brackets):
        self.index = index
        self.bracket = bracket

    def __str__(self) -> str:
        return super().__str__() + "Unexpected '" + self.bracket.value[2] + "' at index: " + str(self.index)


class MissingCloseBracket(SearchStringParseError):
    """
    A subclass of SearchStringParseError, for the specific instance 
    where a close baracket (either } or )) was missing, where is 
    was required such as '(a :: and b'
    """

    def __init__(self, bracket: Brackets):
        self.bracket = bracket

    def __str__(self) -> str:
        return super().__str__() + "Missing a closing '" + self.bracket.value[2] + "'"


class UnexpectedOperator(SearchStringParseError):
    """
    A subclass of SearchStringParseError, for the specific instance 
    where an operator such as ::and occurs in an unexpected locations 
    such as: 'a ::and ::and b'
    """

    def __init__(self, index: int, operator: 'OperatorTypes', alias=None):
        self.index = index
        if alias is None or not alias:
            self.operator_str = "::" + str(operator.value)
        else:
            self.operator_str = alias

    def __str__(self) -> str:
        return super().__str__() + "Unexpected operator: [" + self.operator_str + "] at index: " + str(self.index)


class UnexpectedTag(SearchStringParseError):
    """
    A subclass of SearchStringParseError, for the specific instance 
    where a tag appears in the wrong spot such as: 'a ::not b'
    """

    def __init__(self, index: int, string: str):
        self.index = index
        self.string = string

    def __str__(self) -> str:
        return super().__str__() + "Unexpected tag: [" + self.string + "] at index: " + str(self.index)


class NonexistentTag(SearchStringParseError):
    """
    A subclass of SearchStringParseError, for the specific instance 
    where a tag does not exisit in the DB
    """

    def __init__(self, string: str):
        self.string = string

    def __str__(self) -> str:
        return super().__str__() + "Nonexistent tag: [" + self.string + "]"


class NonexistentAttribute(SearchStringParseError):
    """
    A subclass of SearchStringParseError, for the specific instance 
    where an attribute does not exisit in the DBA subclass of 
    SearchStringParseError, for the specific instance where an attribute 
    does not exisit in the DB
    """

    def __init__(self, string: str):
        self.string = string

    def __str__(self) -> str:
        return super().__str__() + "Nonexistent attribute: [" + self.string + "]"


class Value:
    """
    An general 'atom' of an expression, such as 'a' or 
    '::instance::uuid::equals::10202901'
    """

    string: str
    not_value: bool = False

    @staticmethod
    def parse(value: str) -> Union['Value', SearchStringParseError]:
        """
        Given a string, that is suppose to figure out which kind 
        of atom/value it is and parse that into it's types
        """

        if value.lstrip().startswith("::"):

            if value.lstrip().startswith("::has::"):
                cls = HasItemAttributeValue()
                cls.string = value
                cls.attribute_name = value.lstrip()[len("::has::"):].rstrip().lower()

                return cls
            elif value.lstrip().startswith("::instance::has::"):
                cls = HasInstanceAttributeValue()
                cls.string = value
                cls.attribute_name = value.lstrip()[len("::instance::has::"):].rstrip().lstrip()

                return cls
            elif value.lstrip().startswith("::instance::"):
                remain = value.lstrip()[len("::instance::"):].rstrip()

                if "::equals::" in remain:
                    s = remain.find("::equals::")

                    cls = CheckInstanceAttributeValue()
                    cls.string = value
                    cls.attribute_name = remain[:s].lower()
                    cls.value = remain[s + len("::equals::"):]
                    cls.check_mode = CheckMode.Equals

                    return cls
                elif "::contains::" in remain:
                    s = remain.find("::contains::")

                    cls = CheckInstanceAttributeValue()
                    cls.string = value
                    cls.attribute_name = remain[:s].lower()
                    cls.value = remain[s + len("::contains::"):]
                    cls.check_mode = CheckMode.Contains

                    return cls
                else:
                    cls = InstanceTagValue()
                    cls.string = value
                    cls.stripped_name = remain.strip().lower()

                    return cls

            else:
                remain = value.lstrip()[len("::"):].rstrip()

                if "::equals::" in remain:
                    s = remain.find("::equals::")

                    cls = CheckItemAttributeValue()
                    cls.string = value
                    cls.attribute_name = remain[:s].lower()
                    cls.value = remain[s + len("::equals::"):]
                    cls.check_mode = CheckMode.Equals

                    return cls
                elif "::contains::" in remain:
                    s = remain.find("::contains::")

                    cls = CheckItemAttributeValue()
                    cls.string = value
                    cls.attribute_name = remain[:s].lower()
                    cls.value = remain[s + len("::contains::"):]
                    cls.check_mode = CheckMode.Contains

                    return cls

        else:
            cls = ItemTagValue()
            cls.string = value
            cls.stripped_name = value.strip().lower()

            return cls

    def __str__(self) -> str:
        """
        Convert the atom back into a string, for testing
        """
        if self.not_value:
            return "!"
        return ""

    def to_search_query(self) -> Dict:
        """
        Take the value/atom and convert it into a MongoDB search 
        query for that specific information
        """
        if isinstance(self, ItemTagValue):
            if self.not_value:
                inner = {"$ne": self.tag_id}
                op = "$and"
            else:
                inner = self.tag_id
                op = "$or"

            return {op: [{"tags": inner}, {"implied_tags": inner}]}
        elif isinstance(self, InstanceTagValue):
            if self.not_value:
                inner = {"$ne": self.tag_id}
                op = "$and"
            else:
                inner = self.tag_id
                op = "$or"

            return {op: [{"instances.tags": inner}, {"instances.implied_tags": inner}]}
        elif isinstance(self, HasItemAttributeValue):
            if self.not_value:
                return {"attributes.option_id": {"$ne": self.attribute_option_id}}
            else:
                return {"attributes.option_id": self.attribute_option_id}
        elif isinstance(self, HasInstanceAttributeValue):
            if self.not_value:
                return {"instances.attributes.option_id": {"$ne": self.attribute_option_id}}
            else:
                return {"instances.attributes.option_id": self.attribute_option_id}
        elif isinstance(self, VisibleItemValue):
            return {"hidden": {"$ne": True}}
        elif isinstance(self, CheckItemAttributeValue):
            if self.check_mode == CheckMode.Equals:
                if self.not_value:
                    return {"attributes": {"$elemMatch": {"option_id": self.attribute_option_id, "value": {"$ne": self.value}}}}
                else:
                    return {"attributes": {"$elemMatch": {"option_id": self.attribute_option_id, "value": self.value}}}
            elif self.check_mode == CheckMode.Contains:
                if self.not_value:
                    return {"attributes": {"$elemMatch": {"option_id": self.attribute_option_id, "value": {"not": {"$regex": ".*" + self.value + ".*"}}}}}
                else:
                    return {"attributes": {"$elemMatch": {"option_id": self.attribute_option_id, "value": {"$regex": ".*" + self.value + ".*"}}}}
            else:
                return {"TODO": "Unexpected"}
        elif isinstance(self, CheckInstanceAttributeValue):
            if self.check_mode == CheckMode.Equals:
                if self.not_value:
                    return {"instances.attributes": {"$elemMatch": {"option_id": self.attribute_option_id, "value": {"$ne": self.value}}}}
                else:
                    return {"instances.attributes": {"$elemMatch": {"option_id": self.attribute_option_id, "value": self.value}}}
            elif self.check_mode == CheckMode.Contains:
                if self.not_value:
                    return {"instances.attributes": {"$elemMatch": {"option_id": self.attribute_option_id, "value": {"not": {"$regex": ".*" + self.value + ".*"}}}}}
                else:
                    return {"instances.attributes": {"$elemMatch": {"option_id": self.attribute_option_id, "value": {"$regex": ".*" + self.value + ".*"}}}}
            else:
                return {"TODO": "Unexpected"}


class TagValue(Value):
    """
    A subclass of Value, for the specific case where the atom is 
    a tag, like 'a'
    """
    stripped_name: str
    tag_id: Optional[ObjectId] = None

    def __str__(self) -> str:
        return super().__str__()


class ItemTagValue(TagValue):
    """
    A subclass of TagValue, for the specific case where the tag is 
    for a tag attached to an item, like 'a'  
    """

    def __str__(self) -> str:
        return super().__str__() + "Tag: '" + self.stripped_name + "'"


class InstanceTagValue(TagValue):
    """
    A subclass of TagValue, for the specific case where the tag is 
    for a tag attached to an instance, like 'instance::a'
    """

    def __str__(self) -> str:
        return super().__str__() + "InstanceTag: '" + self.stripped_name + "'"


class AttributeValue(Value):
    """
    A subclass of Value, for the specific case where we are looking 
    for an attribute
    """

    attribute_name: str
    attribute_option_id: Optional[ObjectId] = None

    def __str__(self) -> str:
        return super().__str__()


class HasItemAttributeValue(AttributeValue):
    """
    A subclass of AttributeValue, for when we are looking for an item 
    to have an attribute, like: 'has::name'
    """

    def __str__(self) -> str:
        return super().__str__() + "HasItemAttribute: '" + self.attribute_name + "'"


class HasInstanceAttributeValue(AttributeValue):
    """
    A subclass of AttributeValue, for when we are looking for an instance 
    to have an attribute, like: 'instance::has::name'
    """

    def __str__(self) -> str:
        return super().__str__() + "HasInstanceAttribute: '" + self.attribute_name + "'"


class CheckMode(Enum):
    """
    For the value checks below, enumerates whether it is 'equals' or 'contains'
    """

    Equals = 0,
    Contains = 1
    # TODO add more options? such as starts with/ends with, or case sensitive/case insensitive


class CheckItemAttributeValue(AttributeValue):
    """
    A subclass of AttributeValue, for when checking for a specific 
    value of an item's attribute, like 'name::equals::Bob' or 'name::contains::Bob'
    """

    check_mode: CheckMode
    value: str

    def __str__(self) -> str:
        return "CheckItemAttribute: '" + self.attribute_name + "'" + " | " + str(
            self.check_mode) + " | '" + self.value + "'"


class CheckInstanceAttributeValue(AttributeValue):
    """
    A subclass of AttributeValue, for when checking for a specific 
    value of an instance's attribute, like 'name::equals::Bob' or 
    'name::contains::Bob'
    """

    check_mode: CheckMode
    value: str

    def __str__(self) -> str:
        return "CheckInstanceAttribute: '" + self.attribute_name + "'" + " | " + str(
            self.check_mode) + " | '" + self.value + "'"


class VisibleItemValue(Value):
    """
    A special subclass of Value, used internally to tell the DB to only 
    provide visible visible items/instances from the DB
    """

    def __str__(self) -> str:
        return "VisibleItem"


class OperatorTypes(Enum):
    """
    An enum to enumerate the different types of operator
    """

    Identity = "identity"
    Not = "not"
    And = "and"
    Or = "or"


class Operator(metaclass=abc.ABCMeta):
    """
    A general base class for the two types of operator (unitary, binary) 
    as a node in a abstact symbol tree of operators and values on the leafs
    """

    op_type: OperatorTypes = None

    def __init__(self, op_type: OperatorTypes):
        self.op_type = op_type

    @abc.abstractmethod
    def get_left_most(self) -> Union['Operator', Value]:
        """
        Get the left most child of this node
        """
        pass

    @abc.abstractmethod
    def get_right_most(self) -> Union['Operator', Value]:
        """
        Get the right most child of this node
        """
        pass

    @abc.abstractmethod
    def set_left_most(self, value: Union['Operator', Value]):
        """
        Set the left most child of this node
        """
        pass

    @abc.abstractmethod
    def set_right_most(self, value: Union['Operator', Value]):
        """
        Set the right most child of this node
        """
        pass

    @abc.abstractmethod
    def __str__(self) -> str:
        """
    	Convert back to string for debugging
        """ 
        pass

    @abc.abstractmethod
    def to_search_query(self) -> Dict:
        """
    	Recursively convert this node and it's children to a MongoDB query
        """
        pass


class UnitaryOperator(Operator):
    """
    A subclass of Operator for the specific instance of an operator 
    that takes in one value, such as 'not' or the unity operator '()'
    """
    value: Union[Operator, Value]

    def __init__(self, op_type: OperatorTypes, value: Union[Operator, Value]):
        super().__init__(op_type)

        self.value = value

    def get_left_most(self) -> Union[Operator, Value]:
        """
        Get the left most child of this node
        """
        return self.value

    def get_right_most(self) -> Union[Operator, Value]:
        """
        Get the right most child of this node
        """
        return self.value

    def set_left_most(self, value: Union[Operator, Value]):
        """
        Set the left most child of this node
        """
        self.value = value

    def set_right_most(self, value: Union[Operator, Value]):
        """
        Set the right most child of this node
        """
        self.value = value

    def __str__(self) -> str:
        """
    	Convert back to string for debugging
        """
        if self.op_type == OperatorTypes.Identity:
            return "(" + str(self.value) + ")"
        else:
            return "::not " + str(self.value)

    def to_search_query(self) -> Dict:
        """
    	Recursively convert this node and it's children to a MongoDB query
        """
        if self.op_type == OperatorTypes.Identity:
            return self.value.to_search_query()
        else:
            return {"NOTE": "Should never be reached"}


class BinaryOperator(Operator):
    """
    A subclass of Operator for the specific instance of an operator 
    that takes in two values, such as 'and' or 'or'
    """

    left_value: Union[Operator, Value]
    right_value: Union[Operator, Value]

    def __init__(self, op_type: OperatorTypes, left_value: Union[Operator, Value], right_value: Union[Operator, Value]):
        super().__init__(op_type)

        self.left_value = left_value
        self.right_value = right_value

    def get_left_most(self) -> Union[Operator, Value]:
        """
        Get the left most child of this node
        """
        return self.left_value

    def get_right_most(self) -> Union[Operator, Value]:
        """
        Get the right most child of this node
        """
        return self.right_value

    def set_left_most(self, value: Union[Operator, Value]):
        """
        Set the left most child of this node
        """
        self.left_value = value

    def set_right_most(self, value: Union[Operator, Value]):
        """
        Set the right most child of this node
        """
        self.right_value = value

    def __str__(self) -> str:
        """
        Convert back to string for debugging
        """
        if self.op_type == OperatorTypes.And:
            return "(" + str(self.left_value) + " ::and " + str(self.right_value) + ")"
        else:
            return "(" + str(self.left_value) + " ::or " + str(self.right_value) + ")"

    def to_search_query(self) -> Dict:
        """
    	Recursively convert this node and it's children to a MongoDB query
        """
        if self.op_type == OperatorTypes.And:
            return {"$and": [self.left_value.to_search_query(), self.right_value.to_search_query()]}
        else:
            return {"$or": [self.left_value.to_search_query(), self.right_value.to_search_query()]}

class LexerSymbolTypes(Enum):
    """
    An enum used to represent all the different symbols that the lexer 
    must proccess, along with their character representations, and array
    of string represents an alias
    """

    # Operators
    AND = ["::and", ',']
    OR = "::or"
    NOT = ["::not", '-']
    # Brackets
    PAREN_OPEN = "("
    PAREN_CLOSE = ")"
    ESCAPE_OPEN = "{"
    ESCAPE_CLOSE = "}"
    # Tags
    TAG = None
    IGNORE = ""

    @staticmethod
    def from_str(value: str) -> 'LexerSymbolTypes':
        """
        Convert a string into a lexer symbol type based on theirt string representations
        """

        for option in LexerSymbolTypes:
            if isinstance(option.value, list):
                for o in option.value:
                    if o == value:
                        return option
            else:
                if option.value == value:
                    return option
        return LexerSymbolTypes.TAG


class LexerSymbol:
    """
    A class used by the lexer to store the symbols it extracts
    """

    symbol_type: LexerSymbolTypes
    start_index: int
    end_index: int

    def __init__(self, symbol_type: LexerSymbolTypes, start_index: int, end_index: int):
        self.symbol_type = symbol_type
        self.start_index = start_index
        self.end_index = end_index

    def __str__(self) -> str:
        if isinstance(self.symbol_type.value, list):
            symbol_str = self.symbol_type.value[0]
        elif self.symbol_type.value is not None:
            symbol_str = self.symbol_type.value
        else:
            symbol_str = "::TAG"

        return "[" + str(self.start_index) + ", " + str(self.end_index) + "]" + symbol_str


#  a lexer to turn the string into an array of symbols
def search_string_lexer(search_string: str) -> Union[List[LexerSymbol], SearchStringParseError]:
    """
    Takes in a search string and converts it intl an array of lexer symbols
    """

    result = []

    escape_depth = 0
    paren_depth = 0
    symbol_start = 0
    skipped = False

    for i, c in enumerate(search_string):

        if c == '{':
            escape_depth += 1

            if escape_depth == 1:
                if search_string[symbol_start:i].isspace():
                    # result.append(
                    #     LexerSymbol(LexerSymbolTypes.from_str(search_string[symbol_start:i]), symbol_start, i - 1))

                    result.append(LexerSymbol(LexerSymbolTypes.ESCAPE_OPEN, i, i))
                    symbol_start = i + 1

                    skipped = False
                else:
                    skipped = True

        elif c == '}':
            escape_depth -= 1

            if escape_depth == 0 and not skipped:
                result.append(LexerSymbol(LexerSymbolTypes.TAG, symbol_start, i - 1))
                result.append(LexerSymbol(LexerSymbolTypes.ESCAPE_CLOSE, i, i))

                symbol_start = i + 1
            elif escape_depth < 0:
                return UnexpectedCloseBracket(i, Brackets.Curly)
        elif escape_depth == 0:
            if c == '(' or c == ')':
                if c == '(':
                    paren_depth += 1
                else:
                    paren_depth -= 1

                    if paren_depth < 0:
                        return UnexpectedCloseBracket(i, Brackets.Parentheses)

                result.append(
                    LexerSymbol(LexerSymbolTypes.from_str(search_string[symbol_start:i]), symbol_start, i - 1))
                result.append(LexerSymbol(LexerSymbolTypes.from_str(c), i, i))
                symbol_start = i + 1

            if c == ',':
                result.append(
                    LexerSymbol(LexerSymbolTypes.from_str(search_string[symbol_start:i]), symbol_start, i - 1))
                result.append(LexerSymbol(LexerSymbolTypes.AND, i, i))
                symbol_start = i + 1

            if search_string[i:].startswith("::and"):
                result.append(
                    LexerSymbol(LexerSymbolTypes.from_str(search_string[symbol_start:i]), symbol_start, i - 1))
                result.append(LexerSymbol(LexerSymbolTypes.AND, i, i + 4))
                symbol_start = i + 5

            if c == '-':
                result.append(
                    LexerSymbol(LexerSymbolTypes.from_str(search_string[symbol_start:i]), symbol_start, i - 1))
                result.append(LexerSymbol(LexerSymbolTypes.NOT, i, i))
                symbol_start = i + 1

            if search_string[i:].startswith("::not"):
                result.append(
                    LexerSymbol(LexerSymbolTypes.from_str(search_string[symbol_start:i]), symbol_start, i - 1))
                result.append(LexerSymbol(LexerSymbolTypes.NOT, i, i + 4))
                symbol_start = i + 5

            if search_string[i:].startswith("::or"):
                result.append(
                    LexerSymbol(LexerSymbolTypes.from_str(search_string[symbol_start:i]), symbol_start, i - 1))
                result.append(LexerSymbol(LexerSymbolTypes.OR, i, i + 3))
                symbol_start = i + 4

    if not search_string[symbol_start:].isspace():
        result.append(LexerSymbol(LexerSymbolTypes.from_str(search_string[symbol_start:]), symbol_start,
                                  len(search_string) - 1))

    for r in result:
        r.start_index += (r.end_index - r.start_index + 1) - len(search_string[r.start_index:r.end_index + 1].lstrip())
        r.end_index -= (r.end_index - r.start_index + 1) - len(search_string[r.start_index:r.end_index + 1].rstrip())

    result = [r for r in result if r.start_index <= r.end_index]

    if escape_depth != 0:
        return MissingCloseBracket(Brackets.Curly)
    if paren_depth != 0:
        return MissingCloseBracket(Brackets.Parentheses)

    return result


class AST:
    """
    Used to store the abstract symbol tree
    """

    base_operator: Operator
    tag_values: List[TagValue] = []
    attribute_values: List[AttributeValue] = []

    def __init__(self, base_operator: Operator):
        self.base_operator = base_operator
        self.tag_values = []
        self.attribute_values = []

    def __str__(self) -> str:
        return str(self.base_operator)


#  a parser to turn the symbols from the lexer into an AST, or in this case a tree of operators
def search_string_parser(search_string: Union[str, List[LexerSymbol]]) -> Union[AST, SearchStringParseError]:
    """
    Takes in a search string, or array of lexer symbols, converts 
    the string into an array of lexer symbols if needed, then converts 
    that into the abstract symbol tree
    """

    if isinstance(search_string, str):
        lex_symbols = search_string_lexer(search_string)
        if isinstance(lex_symbols, SearchStringParseError):
            return lex_symbols
    else:
        lex_symbols = search_string

    # one pass to absorb (, ) or - that are a part of tags

    paren_depth = 0
    embedded_paren = 0

    for i, s in enumerate(lex_symbols):
        if s.symbol_type == LexerSymbolTypes.PAREN_OPEN:
            paren_depth += 1

        if s.symbol_type == LexerSymbolTypes.PAREN_OPEN or search_string[s.start_index] == '-':
            if i != 0 and lex_symbols[i - 1].symbol_type == LexerSymbolTypes.TAG:
                # 'a' '(' -> 'a (' or 'a' '-' -> 'a -'
                lex_symbols[i - 1].end_index = s.end_index
                s.symbol_type = LexerSymbolTypes.IGNORE
                embedded_paren += 1

        if s.symbol_type == LexerSymbolTypes.PAREN_CLOSE:
            if i != len(lex_symbols) - 1 and lex_symbols[i + 1].symbol_type == LexerSymbolTypes.TAG:
                # ')' 'a' -> ') a'
                s.end_index = lex_symbols[i + 1].end_index
                s.symbol_type = LexerSymbolTypes.TAG
                lex_symbols[i + 1].symbol_type = LexerSymbolTypes.IGNORE
            elif embedded_paren > 0:
                # '( a' ')' -> '( a )'
                lex_symbols[i-1].end_index = s.end_index
                s.symbol_type = LexerSymbolTypes.IGNORE
                embedded_paren -= 1

            paren_depth -= 1
            if paren_depth < 0:
                return UnexpectedCloseBracket(s.start_index, Brackets.Parentheses)

    # one pass to remove ignore

    lex_symbols = [ls for ls in lex_symbols if ls.symbol_type != LexerSymbolTypes.IGNORE]

    # one pass to combine adj tags

    for i, s in enumerate(lex_symbols):
        if i == 0:
            continue

        if s.symbol_type == LexerSymbolTypes.TAG and lex_symbols[i - 1].symbol_type == LexerSymbolTypes.TAG:
            lex_symbols[i - 1].symbol_type = LexerSymbolTypes.IGNORE
            s.start_index = lex_symbols[i - 1].start_index

    # form ast

    ast = AST(UnitaryOperator(OperatorTypes.Identity, None))
    operator_stack: List[Union[Operator, Value]] = [ast.base_operator]

    escape_depth = 0

    for symbol in lex_symbols:
        if symbol.symbol_type == LexerSymbolTypes.ESCAPE_OPEN:
            escape_depth += 1
        elif symbol.symbol_type == LexerSymbolTypes.ESCAPE_CLOSE:
            escape_depth -= 1

            if escape_depth < 0:
                return UnexpectedCloseBracket(symbol.start_index, Brackets.Curly)
        elif symbol.symbol_type == LexerSymbolTypes.PAREN_OPEN and escape_depth == 0:
            new_operator = UnitaryOperator(OperatorTypes.Identity, None)

            operator_stack[-1].set_right_most(new_operator)
            operator_stack.append(new_operator)
        elif symbol.symbol_type == LexerSymbolTypes.PAREN_CLOSE and escape_depth == 0:
            operator_stack.pop()
            if not operator_stack:
                return UnexpectedCloseBracket(symbol.start_index, Brackets.Parentheses)
        elif symbol.symbol_type == LexerSymbolTypes.NOT:
            new_operator = UnitaryOperator(OperatorTypes.Not, None)

            operator_stack[-1].set_right_most(new_operator)
            operator_stack.append(new_operator)
        elif symbol.symbol_type == LexerSymbolTypes.AND or symbol.symbol_type == LexerSymbolTypes.OR:
            left = operator_stack[-1].get_right_most()
            op_type = OperatorTypes.And if symbol.symbol_type == LexerSymbolTypes.AND else OperatorTypes.Or
            if left is None:
                return UnexpectedOperator(symbol.start_index, op_type)

            if isinstance(left, Operator) and left.op_type == OperatorTypes.Identity:
                left = left.get_left_most()

            new_operator = BinaryOperator(op_type, left, None)
            operator_stack[-1].set_right_most(new_operator)
            operator_stack.append(new_operator)
        elif symbol.symbol_type != LexerSymbolTypes.IGNORE:
            value = Value.parse(search_string[symbol.start_index:symbol.end_index + 1])

            if isinstance(value, TagValue):
                ast.tag_values.append(value)
            elif isinstance(value, AttributeValue):
                ast.attribute_values.append(value)

            operator_stack[-1].set_right_most(value)
            # if len(operator_stack) > 1:
            #     operator_stack.pop()
            #     if len(operator_stack) > 1:
            #         operator_stack.pop()

    return ast


def search_string_to_mongodb_query(mongo: PyMongo, search_string: Union[str, AST], include_hidden: bool = False) -> Union[Dict, List[SearchStringParseError]]:
    """
    Takes in a search string, or AST and converts the search string 
    into an AST if neededed, then does all the processing needed to 
    convert that AST into a query that MongoDB understands
    """

    if isinstance(search_string, str):
        ast: AST = search_string_parser(search_string)
        if isinstance(ast, SearchStringParseError):
            return [ast]
    else:
        ast: AST = search_string

    # if not include_hidden then add that condition

    if not include_hidden:
        ast.base_operator = BinaryOperator(OperatorTypes.And, ast.base_operator, VisibleItemValue())

    # verify existence of tags/attribs and get their ids

    tag_names: Dict[str, TagValue] = {t.stripped_name: t for t in ast.tag_values}
    attribute_names: Dict[str, AttributeValue] = {a.attribute_name: a for a in ast.attribute_values}

    tags = mongo.db.tags.find({"name": {"$in": list(tag_names.keys())}})
    tags = [Tag.from_dict(t) for t in tags]

    for tag in tags:
        tag_names.pop(tag.name).tag_id = tag.id

    if tag_names:
        return [NonexistentTag(t) for t in tag_names.keys()]

    attrib_options = mongo.db.attrib_options.find({"attribute_name": {"$in": list(attribute_names.keys())}})
    attrib_options = [AttributeOption.from_dict(t) for t in attrib_options]

    for attrib_option in attrib_options:
        attribute_names.pop(attrib_option.attribute_name).attribute_option_id = attrib_option.id

    if attribute_names:
        return [NonexistentAttribute(t) for t in attribute_names.keys()]

    # now: selectively apply de-morgans law to move all not's onto atomic values due to limitation in MongoDB search

    to_visit_queue: List[Operator] = [ast.base_operator]

    while to_visit_queue:
        node = to_visit_queue.pop()

        if isinstance(node, UnitaryOperator):
            if node.op_type == OperatorTypes.Identity:
                if isinstance(node.value, Operator):
                    to_visit_queue.append(node.value)
            elif node.op_type == OperatorTypes.Not:
                if isinstance(node.value, UnitaryOperator):
                    if node.value.op_type == OperatorTypes.Identity:
                        # !(a) -> (!a)
                        node.op_type = OperatorTypes.Identity
                        node.value.op_type = OperatorTypes.Not
                    elif node.value.op_type == OperatorTypes.Not:
                        # !!a -> a
                        node.op_type = OperatorTypes.Identity
                        node.value.op_type = OperatorTypes.Identity

                    to_visit_queue.append(node.value)
                elif isinstance(node.value, BinaryOperator):
                    if node.value.op_type == OperatorTypes.And:
                        # !(a && b) -> (!a || !b)
                        node.op_type = OperatorTypes.Identity
                        node.value.op_type = OperatorTypes.Or

                        node.value.left_value = UnitaryOperator(OperatorTypes.Not, node.value.left_value)
                        node.value.right_value = UnitaryOperator(OperatorTypes.Not, node.value.right_value)
                    elif node.value.op_type == OperatorTypes.Or:
                        # !(a || b) -> (!a && !b)
                        node.op_type = OperatorTypes.Identity
                        node.value.op_type = OperatorTypes.And

                        node.value.left_value = UnitaryOperator(OperatorTypes.Not, node.value.left_value)
                        node.value.right_value = UnitaryOperator(OperatorTypes.Not, node.value.right_value)

                    to_visit_queue.append(node.value)
                elif isinstance(node.value, Value):
                    # embed the not so it can be processed correctly
                    # !a -> a(not = true)
                    node.op_type = OperatorTypes.Identity
                    node.value.not_value = not node.value.not_value

        elif isinstance(node, BinaryOperator):
            if isinstance(node.left_value, Operator):
                to_visit_queue.append(node.left_value)
            if isinstance(node.right_value, Operator):
                to_visit_queue.append(node.right_value)

    # now form into a search

    return ast.base_operator.to_search_query()

# TODO Basic tests that require by inspection testing, to be replaced by unit tests most likely at some point

# print("Test ::and -> " + str(LexerSymbolTypes.from_str("::and")))
# print("Test ::or -> " + str(LexerSymbolTypes.from_str("::or")))
# print("Test ::not -> " + str(LexerSymbolTypes.from_str("::not")))
# print("Test , -> " + str(LexerSymbolTypes.from_str(",")))
# print("Test - -> " + str(LexerSymbolTypes.from_str("-")))
# print("Test ( -> " + str(LexerSymbolTypes.from_str("(")))
# print("Test ) -> " + str(LexerSymbolTypes.from_str(")")))
# print("Test { -> " + str(LexerSymbolTypes.from_str("{")))
# print("Test } -> " + str(LexerSymbolTypes.from_str("}")))
# print("Test {_ -> " + str(LexerSymbolTypes.from_str("{_")))
# print()
#
#
# def test_lexer(string: str):
#     result = search_string_lexer(string)
#     result_fmt = ' '.join(string[i.start_index:i.end_index + 1] for i in result)
#     print("Testing: '" + string + "'")
#     print("\tresult: [" + ', '.join(map(str, result)) + "]")
#     print("\tformatted: " + result_fmt)
#
#
# def test_parser_and_lexer(string: str):
#     lexer_result = search_string_lexer(string)
#     lexer_result_fmt = ' '.join(string[i.start_index:i.end_index + 1] for i in lexer_result)
#     parser_result = search_string_parser(string)
#
#     print("Testing: '" + string + "'")
#     print("\tlexer result: [" + ', '.join(map(str, lexer_result)) + "]")
#     print("\tlexer formatted: " + lexer_result_fmt)
#     print("\tparser result: " + str(parser_result))
#     print()
#
#
# test_parser_and_lexer("ak")
# test_parser_and_lexer("ak {bk}")
# test_parser_and_lexer("ThIs iS A TEst")
# test_parser_and_lexer("::not ak")
# test_parser_and_lexer("-ak")
# test_parser_and_lexer("- ak")
# test_parser_and_lexer("ak, bf")
# test_parser_and_lexer("ak, bf, cd")
# test_parser_and_lexer("ak, (bf, cd)")
# test_parser_and_lexer("ak, (bf ::or cd)")
# test_parser_and_lexer("ak, (bf ::or cd ::or ::instance::uuid::equals::85781903019)")
# test_parser_and_lexer("ak, (bf ::or cd ::or ::instance::UUID::equals::85781903019)")
# test_parser_and_lexer("ak, (bf ::or cd ::or ::name::equals::Book's Book)")
# test_parser_and_lexer("ak, (bf ::or cd ::or ::name::Equals::book's book)")
# test_parser_and_lexer("ak, bf, cd ::and (kt ::or ::not y {1} {2})")
# test_parser_and_lexer("ak, bf, cd ::and (kt ::or -y {1} {2})")
# test_parser_and_lexer("ak, bf, cd ::and (kt ::or ::not {y (1)})")
# test_parser_and_lexer("ak, bf, cd ::and (kt ::or -{y (1)})")
# test_parser_and_lexer("ak, bf, cd ::and (kt ::or ::not {y (1) {3}})")
# test_parser_and_lexer("ak, bf, cd ::and (kt ::or -{y (1) {3}})")
