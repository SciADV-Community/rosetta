import enum
import itertools
from collections import deque


# Expression token type enum
class TokenType(enum.Enum):
    SYMBOL = 0
    LOGIC_AND = 1
    LOGIC_OR = 2
    LOGIC_NOT = 3
    L_PARANTHESIS = 4
    R_PARANTHESIS = 5


# Expression token dictionary to simplify code a bit
TokenDic = {'&': TokenType.LOGIC_AND, '|': TokenType.LOGIC_OR,
            '!': TokenType.LOGIC_NOT, '(': TokenType.L_PARANTHESIS}


# Precedence value dictionary for postfix conversion
Precedence = {TokenType.LOGIC_NOT: 20, TokenType.LOGIC_AND: 11,
              TokenType.LOGIC_OR: 10, TokenType.SYMBOL: 0,
              TokenType.L_PARANTHESIS: 0, TokenType.R_PARANTHESIS: 0}


# Expression token representation
class ExpressionToken:
    type = -1
    value = ""

    def __init__(self, type, value):
        self.type = type
        self.value = value


# Tokenize the input string
def tokenize(in_str):
    tokens = []
    # Remove whitespace
    in_str = "".join(in_str.split())
    # If the first character is not a symbol name start or '!' or
    # '(' we have an invalid expression
    if not (in_str[0].isdigit() or in_str[0] == '!' or in_str[0] == '('):
        raise Exception('Invalid syntax at 0')
    i = 0
    while i < len(in_str):
        # Symbol name must start with a digit (Discord role ID)
        if in_str[i].isdigit():
            symbol = "".join(itertools.takewhile(
                lambda x: x.isdigit(), in_str[i:]))
            i += len(symbol) - 1
            tokens.append(ExpressionToken(TokenType.SYMBOL, symbol))
        elif (in_str[i] == '&' and in_str[i + 1] == '&')\
                or (in_str[i] == '|' and in_str[i + 1] == '|'):
            i += 1
            # If no next char or next char is r_paranthesis - invalid syntax
            if i + 1 >= len(in_str) or in_str[i+1] == ')':
                raise Exception('Invalid syntax at {}'.format(i))
            tokens.append(ExpressionToken(TokenDic[in_str[i]], 0))
        elif in_str[i] == '!' or in_str[i] == '(':
            # For unary operations and left paranthesis
            # if previous token is a symbol or r_paranthesis - invalid syntax
            if tokens and (tokens[-1].type == TokenType.SYMBOL
                           or tokens[-1].type == TokenType.R_PARANTHESIS):
                raise Exception('Invalid syntax at {}'.format(i))
            tokens.append(ExpressionToken(TokenDic[in_str[i]], 0))
        elif in_str[i] == ')':
            # Empty paranthesis
            if tokens and tokens[-1].type == TokenType.L_PARANTHESIS:
                raise Exception('Invalid syntax at {}'.format(i))
            tokens.append(ExpressionToken(TokenType.R_PARANTHESIS, 0))
        else:
            raise Exception('Illegal token {} at {}'.format(in_str[i], i))
        i += 1
    return tokens


# Convert tokenized expression to postfix form
def convert_to_postfix(tokens):
    stack = deque()
    output = []
    for token in tokens:
        if token.type == TokenType.LOGIC_AND or token.type == TokenType.LOGIC_OR:
            if stack:
                minPrecedence = Precedence[token.type]
                while Precedence[stack[-1].type] >= minPrecedence:
                    output.append(stack.pop())
                    if not stack:
                        break
            stack.append(token)
        elif token.type == TokenType.SYMBOL:
            output.append(token)
        elif token.type == TokenType.LOGIC_NOT:
            stack.append(token)
        elif token.type == TokenType.L_PARANTHESIS:
            stack.append(token)
        elif token.type == TokenType.R_PARANTHESIS:
            if not stack:
                raise Exception("Missing parenthesis")
            while stack[-1].type != TokenType.L_PARANTHESIS:
                output.append(stack.pop())
                if not stack:
                    raise Exception("Missing parenthesis")
            stack.pop()
    if not stack:
        return output
    if stack[-1].type == TokenType.L_PARANTHESIS:
        raise Exception("Missing parenthesis")
    while stack:
        output.append(stack.pop())
    return output


# Dictionary for symbol evaluation
dictionary = {}


# Evaluate the symbol
def evaluate_symbol(symbol):
    if symbol not in dictionary:
        raise Exception('Symbol {} doesn\'t exist.'.format(symbol))
    return dictionary[symbol]


# Evaluate string expression
def evaluate(in_str):
    if not in_str:
        raise Exception('Empty expression string')
    tokens = convert_to_postfix(tokenize(in_str))
    stack = deque()
    result = False
    for token in tokens:
        if token.type == TokenType.LOGIC_NOT:
            rightOperand = stack.pop()
            result = not rightOperand
            stack.append(result)
        elif token.type == TokenType.LOGIC_AND:
            rightOperand = stack.pop()
            leftOperand = stack.pop()
            result = leftOperand and rightOperand
            stack.append(result)
        elif token.type == TokenType.LOGIC_OR:
            rightOperand = stack.pop()
            leftOperand = stack.pop()
            result = leftOperand or rightOperand
            stack.append(result)
        elif token.type == TokenType.SYMBOL:
            stack.append(evaluate_symbol(token.value))
    return stack.pop()
