from __future__ import annotations

import abc
from enum import Enum
from typing import List, Union


class Brackets(Enum):
    Parentheses = ["Parentheses", '(', ')']
    Curly = ["Curly", '{', '}']


class SearchStringParseError:
    def __str__(self) -> str:
        return "SearchStringParseError: "


class UnexpectedCloseBracket(SearchStringParseError):
    def __init__(self, index: int, bracket: Brackets):
        self.index = index
        self.bracket = bracket

    def __str__(self) -> str:
        return super().__str__() + "Unexpected '" + self.bracket.value[2] + "' at index: " + str(self.index)


class MissingCloseBracket(SearchStringParseError):

    def __init__(self, bracket: Brackets):
        self.bracket = bracket

    def __str__(self) -> str:
        return super().__str__() + "Missing a closing '" + self.bracket.value[2] + "'"


class UnexpectedOperator(SearchStringParseError):

    def __init__(self, index: int, operator: OperatorTypes, alias=None):
        self.index = index
        if alias is None or not alias:
            self.operator_str = "::" + str(operator.value)
        else:
            self.operator_str = alias

    def __str__(self) -> str:
        return super().__str__() + "Unexpected operator: [" + self.operator_str + "] at index: " + str(self.index)


class UnexpectedTag(SearchStringParseError):

    def __init__(self, index: int, string: str):
        self.index = index
        self.string = string

    def __str__(self) -> str:
        return super().__str__() + "Unexpected tag: [" + self.string + "] at index: " + str(self.index)


class Value:
    string: str

    def __init__(self, value: str):
        self.string = value

    def __str__(self) -> str:
        return self.string


class OperatorTypes(Enum):
    Identity = "identity"
    Not = "not"
    And = "and"
    Or = "or"


class Operator(metaclass=abc.ABCMeta):
    op_type: OperatorTypes = None

    def __init__(self, op_type: OperatorTypes):
        self.op_type = op_type

    @abc.abstractmethod
    def get_left_most(self) -> Union[Operator, Value]:
        pass

    @abc.abstractmethod
    def get_right_most(self) -> Union[Operator, Value]:
        pass

    @abc.abstractmethod
    def set_left_most(self, value: Union[Operator, Value]):
        pass

    @abc.abstractmethod
    def set_right_most(self, value: Union[Operator, Value]):
        pass

    @abc.abstractmethod
    def __str__(self) -> str:
        pass


class UnitaryOperator(Operator):
    value: Union[Operator, Value]

    def __init__(self, op_type: OperatorTypes, value: Union[Operator, Value]):
        super().__init__(op_type)

        self.value = value

    def get_left_most(self) -> Union[Operator, Value]:
        return self.value

    def get_right_most(self) -> Union[Operator, Value]:
        return self.value

    def set_left_most(self, value: Union[Operator, Value]):
        self.value = value

    def set_right_most(self, value: Union[Operator, Value]):
        self.value = value

    def __str__(self) -> str:
        if self.op_type == OperatorTypes.Identity:
            return "(" + str(self.value) + ")"
        else:
            return "::not " + str(self.value)


class BinaryOperator(Operator):
    left_value: Union[Operator, Value]
    right_value: Union[Operator, Value]

    def __init__(self, op_type: OperatorTypes, left_value: Union[Operator, Value], right_value: Union[Operator, Value]):
        super().__init__(op_type)

        self.left_value = left_value
        self.right_value = right_value

    def get_left_most(self) -> Union[Operator, Value]:
        return self.left_value

    def get_right_most(self) -> Union[Operator, Value]:
        return self.right_value

    def set_left_most(self, value: Union[Operator, Value]):
        self.left_value = value

    def set_right_most(self, value: Union[Operator, Value]):
        self.right_value = value

    def __str__(self) -> str:
        if self.op_type == OperatorTypes.And:
            return "(" + str(self.left_value) + " ::and " + str(self.right_value) + ")"
        else:
            return "(" + str(self.left_value) + " ::or " + str(self.right_value) + ")"


class Parentheses:
    start: int = -1
    end: int = -1
    inner: List[Parentheses] = []

    def __init__(self, start: int, end: int, inner: List[Parentheses]):
        self.start = start
        self.end = end
        self.inner = inner

    def __str__(self) -> str:
        inner_str = ""

        first = True
        for i in self.inner:
            if first:
                first = False
            else:
                inner_str += ", "
            inner_str += str(i)

        return "Parentheses: start = " + str(self.start) + ", end = " + str(self.end) + ", inner = [" + inner_str + "]"


class LexerSymbolTypes(Enum):
    # Operators
    AND = ["::and", ',']
    OR = "::or"
    NOT = "::not"
    # Brackets
    PAREN_OPEN = "("
    PAREN_CLOSE = ")"
    ESCAPE_OPEN = "{"
    ESCAPE_CLOSE = "}"
    # Tags
    TAG = None

    @staticmethod
    def from_str(value: str) -> LexerSymbolTypes:
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


#  a parser to turn the symbols from the lexer into an AST, or in this case a tree of operators
def search_string_parser(search_string: str) -> Union[Operator, SearchStringParseError]:
    lex_symbols = search_string_lexer(search_string)

    if isinstance(lex_symbols, SearchStringParseError):
        return lex_symbols

    base_operator = UnitaryOperator(OperatorTypes.Identity, None)
    operator_stack: List[Union[Operator, Value]] = [base_operator]

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
        else:
            operator_stack[-1].set_right_most(Value(search_string[symbol.start_index:symbol.end_index + 1]))
            if len(operator_stack) > 1:
                operator_stack.pop()

    return base_operator


# Basic tests that require by inspection testing, to be replaced by unit tests most likely at some point


print("Test: " + str(LexerSymbolTypes.from_str("::and")))
print("Test: " + str(LexerSymbolTypes.from_str("::or")))
print("Test: " + str(LexerSymbolTypes.from_str("::not")))
print("Test: " + str(LexerSymbolTypes.from_str(",")))
print("Test: " + str(LexerSymbolTypes.from_str("(")))
print("Test: " + str(LexerSymbolTypes.from_str(")")))
print("Test: " + str(LexerSymbolTypes.from_str("{")))
print("Test: " + str(LexerSymbolTypes.from_str("}")))
print("Test: " + str(LexerSymbolTypes.from_str("{_")))
print()


def test_lexer(string: str):
    result = search_string_lexer(string)
    result_fmt = ' '.join(string[i.start_index:i.end_index + 1] for i in result)
    print("Testing: '" + string + "'")
    print("\tresult: [" + ', '.join(map(str, result)) + "]")
    print("\tformatted: " + result_fmt)


def test_parser_and_lexer(string: str):
    lexer_result = search_string_lexer(string)
    lexer_result_fmt = ' '.join(string[i.start_index:i.end_index + 1] for i in lexer_result)
    parser_result = search_string_parser(string)

    print("Testing: '" + string + "'")
    print("\tlexer result: [" + ', '.join(map(str, lexer_result)) + "]")
    print("\tlexer formatted: " + lexer_result_fmt)
    print("\tparser result: " + str(parser_result))
    print()


test_parser_and_lexer("ak")
test_parser_and_lexer("ak {bk}")
test_parser_and_lexer("::not ak")
test_parser_and_lexer("ak, bf")
test_parser_and_lexer("ak, bf, cd")
test_parser_and_lexer("ak, (bf, cd)")
test_parser_and_lexer("ak, (bf ::or cd)")
test_parser_and_lexer("ak, (bf ::or cd ::or ::instance::uuid::equals::85781903019)")
test_parser_and_lexer("ak, bf, cd ::and (kt ::or ::not y {1} {2})")
test_parser_and_lexer("ak, bf, cd ::and (kt ::or ::not {y (1)})")
test_parser_and_lexer("ak, bf, cd ::and (kt ::or ::not {y (1) {3}})")

# print("Result: " + str(search_string_search_explicit_paren("a, b, (c {A ) } ::or {d(} )")))
# print("Result: " + str(search_string_search_explicit_paren("a, b, (c {A ) } ::or {d() )")))
# print("Result: " + str(search_string_search_explicit_paren("a, b, (c {A ) } ::or d( )")))
# print("Result: " + str(search_string_search_explicit_paren("a, b, (c {A ) } ::or d) )")))
