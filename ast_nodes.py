import ast
from pyparsing import ParseResults
import json
from typing import Union

class ASTNode:
    _counter = 0
    def __init__(self):
        self.children: list[ASTNode] = []
        self.parent: Union[ASTNode | None] = None

        self.uid = ASTNode._counter
        ASTNode._counter += 1

    def to_python(self):
        """Convert the AST node to a Python representation (to be defined later)."""
        raise NotImplementedError

    def to_logstash(self):
        """Convert the AST node back to a Logstash representation (to be defined later)."""
        raise NotImplementedError

    def __repr__(self):
        return self.to_repr()

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"{self.__class__.__name__}"

class LSString(ASTNode):
    def __init__(self, lexeme: str):
        super().__init__()

        # NOTE: When rendering / printing, lexeme will have quotations around it.
        self.lexeme = lexeme # in python, this is like: '"message"'

        try:
            # NOTE: When rendering / printing, self.value won't have the quotation marks around it as its a native python type
            # Characters like \f, \t, \n, etc are treated as python literals. E.g. \n will be parsed and rendered as newline in self.value, which is expected
            # You cannot use raw string while doing literal_eval as of yet. It breaks the later code.
            safe_lexeme = lexeme.replace('\r\n', '\\n').replace('\n', '\\n')
            self.value = ast.literal_eval(f"""{safe_lexeme}""")
        except Exception as e:
            raise ValueError(f"Invalid string literal {lexeme!r}: {e}")

    def to_python(self):
        return self.value

    def to_source(self):
        return self.lexeme

    def to_logstash(self, indent=0):
        return self.to_python()

    def __repr__(self):
        return f"LSString({self.lexeme!r})"
    
    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"LSString({self.lexeme!r})"
    
def build_lsstring( tokens):
    return LSString(tokens[0])

class LSBareWord(ASTNode):
    """
    Represents a logstash key word (e.g., mutate).
    """
    def __init__(self, value: str):
        super().__init__()
        self.lexeme = value
        self.value = value

    def __repr__(self):
        return f"LSBareWord({self.value})"
    
    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"LSBareWord({self.value})"
    
    def to_python(self):
        return self.value

    def to_logstash(self):
        return self.value

    def to_source(self):
        return self.lexeme

def build_lsbw(tokens):
    return LSBareWord(tokens[0])

class Number(ASTNode):
    def __init__(self, value):
        super().__init__()
        self.lexeme = value
        self.value = value

    def __repr__(self):
        return str(self.value)
    
    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Number({self.value})"

    def to_python(self):
        return self.value 
    
    def to_logstash(self, indent=0):
        return self.value
    
    def to_source(self):
        return self.lexeme

def build_number(toks):
    toks = toks[0]
    return Number(toks)

class Array(ASTNode):
    def __init__(self, values):
        super().__init__()
        self.children :list[ASTNode] = values # Generally the elements are either Hash or LSString

        # set parent links
        for child in self.children:
            child.parent = self

    def to_python(self):
        # If the element is LSString, then the .to_python() will remove quotation marks and parse it as a python object
        return [val.to_python() for val in self.children]

    def __repr__(self):
        return f"Array {[val.to_python() for val in self.children]}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Array[\n{children}\n{ind}]"

    def to_source(self):
        inner = ", ".join(c.to_source() for c in self.children)
        return f"[{inner}]" # A string representation only for rendering- so it's fine if we join and concat brackets
    
    def to_logstash(self, indent=0):
        ind = ' ' * indent
        inner_parts = []
        for c in self.children:
            if isinstance(c, Hash) or isinstance(c, HashEntryNode):
                inner_parts.append(f"\n{ind}{c.to_logstash(indent=indent + 2)}\n")
            else:
                inner_parts.append(c.to_source())
        inner = ", ".join(inner_parts)
        return f"{ind}{self.to_source()}" # NOTE: here, we aren't doing to_logstash() because of quotation marks issues

def build_array_node(toks):
    return Array(toks[0])

class HashEntryNode(ASTNode):
    """Corresponds to hash_entry in PEG"""
    def __init__(self, key, value):
        super().__init__()
        self.key: Union[LSString, LSBareWord, Number] = key # Can be either LSString or Number or LSBareWord. LSString can be assumed to not have escapes
        self.value: ASTNode = value

    def __repr__(self):
        return self.to_source()
    
    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        return f"{ind}HashEntry(\n{self.key.to_repr(indent + 2)} => {self.value.to_repr()}\n{ind})"

    def to_logstash(self, indent=0):
        ind = indent * ' '
        out = f"{ind}{self.key.to_source()} => "
        if isinstance(self.value, Hash):
            out += f"\n{self.value.to_logstash(indent + 2)}\n"
        else:
            out += self.value.to_source() if isinstance(self.value.to_source(), str) else str(self.value.to_source())
            out += "\n"
        return out
        
    def to_python(self):
        return super().to_python()

    def to_source(self):
        return f"{self.key.to_source()} => {self.value.to_source()}"

def build_hash_entry_node(toks):
    toks = toks[0]
    return HashEntryNode(toks[0], toks[1][0])

class Hash(ASTNode):
    """Corresponds to hashmap in PEG. Pretty much the same as hash_entries, except that hashmap wraps hash_entries in braces"""
    def __init__(self, entries):
        super().__init__()
        self.children: list[HashEntryNode] = [*entries]

        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"Hash {self.children}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Hash {{\n{children}\n{ind}}}"

    def to_python(self):
        D = { }

        for entry in self.children:
            D[entry.key.to_python()] = entry.value.to_python()

        return D
    
    def to_source(self):
        lines = []
        for e in self.children:
            k, v = e.key.to_source(), e.value.to_source()
            lines.append(f"{k} => {v}")
        body = "\n  " + "\n  ".join(lines) + "\n"
        return "{" + body + "}"

    def to_logstash(self, indent=0):
        ind = " " * indent
        out = f"{ind}{{\n"
        for entry in self.children:
            out += entry.to_logstash(indent + 2)
        out += f'{ind}}}\n'
        return out

def build_hash_node(toks):
    return Hash(toks[0])

class Attribute(ASTNode):
    def __init__(self, name, value):
        super().__init__()
        self.name: Union[LSString, LSBareWord] = name # Either LSString or LSBareWord
        self.value: ASTNode = value

        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"Attribute {repr(self.name)} => {self.value}"
    
    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        return f"{ind}Attribute(\n{self.name.to_repr(indent + 2)} => {self.value.to_repr(indent + 2)}\n{ind})"

    def to_python(self):
        D = {
            self.name.to_python(): self.value.to_python()
        }
        return D
    
    def to_logstash(self, indent=0):
        ind = indent * ' '
        out = f"{ind}{self.name.to_source()} => "
        
        if isinstance(self.value, Hash):
            out += f"\n{self.value.to_logstash(indent + 2)}\n"
        else:
            out += self.value.to_source() if isinstance(self.value.to_source(), str) else str(self.value.to_source())
            out += '\n'
        return out

    def to_source(self):
        return r"{k} => {v}".format(k=self.name.to_source(), v=self.value.to_source())
     
def build_attribute_node(toks):
    return Attribute(toks[0][0], toks[0][1][0])

class Plugin(ASTNode):
    def __init__(self, plugin_name, attributes):
        super().__init__()
        self.plugin_name: str = plugin_name if isinstance(plugin_name, str) else plugin_name.to_python() # This is LSBareWord when Logstash is first parsed
        self.children: list[Attribute]= attributes 

        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"Plugin {self.plugin_name}: {self.children}"
    
    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}Plugin({self.plugin_name})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def to_python(self):
        d = [ ]
        for attribute in self.children:
            temp = { }
            temp[attribute.name.to_python()] = attribute.value.to_python()
            d.append(temp)

        D = {self.plugin_name : d } 
        return D

    def to_logstash(self, indent=0, is_dm_branch=False):
        ind = indent * ' '
        out = f"{ind}{self.plugin_name} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2)

        out += f"{ind}}}\n"
        return out

    def to_source(self):
        hdr = self.plugin_name.to_source() # Wrap the quotation marks around the plugin => '"field"' is rendered as "field"
        inner = "\n".join(f"  {attr.to_source()}" for attr in self.children)
        return f"{hdr}  {{\n{inner}\n}}" # A string!!! Not a dictionary 

def build_plugin_node(toks):
    return Plugin(toks[0][0], toks[0][1])


class Boolean(ASTNode):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def to_python(self):
        return self.value

    def to_logstash(self, indent=0):
        return LSBareWord(str(self.value).lower()).to_logstash()
    
    def to_source(self):
        return LSBareWord(str(self.value).lower()).to_logstash()

    def __repr__(self):
        return str(self.to_python())

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Boolean({self.value})"

    
def build_boolean_node(toks):
    return Boolean(toks[0])

class SelectorNode(ASTNode):
    """
    Represents a Log-Stash field reference like [foo][bar][baz]
    We keep the raw selector string around for fidelity.
    """
    def __init__(self, raw):
        super().__init__()
        self.raw = raw
        self.children = [raw] if isinstance(raw, ASTNode) else []

        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"SelectorNode( {str(self.raw)})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"SelectorNode({self.raw})"

    def to_python(self):
        return str(self.raw)

    def to_logstash(self, indent=0):
        return str(self.raw)
    
def build_selector_node(toks):
    return SelectorNode(toks[0])

class CompareExpression(ASTNode):
    def __init__(self, left, operator, right):
        super().__init__()
        self.left = left
        self.operator = operator
        self.right = right
        self.children = [left, right]

        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"{self.left} {self.operator} {self.right}"
    
    def to_python(self):
        left = self.left.to_python() if isinstance(self.left, ASTNode) else self.left
        right = self.right.to_python() if isinstance(self.right, ASTNode) else self.right
        return f"{left} {self.operator} {right}"

    def to_logstash(self, indent=0):
        return f"{self.left.to_logstash()} {self.operator} {self.right.to_logstash()}"

class InExpression(ASTNode):
    def __init__(self, value, operator, collection):
        super().__init__()
        self.value = value
        self.operator = operator
        self.collection = collection
        self.children = [value, collection]

        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"InExpression({self.value} {self.operator} {self.collection})"
    
    def to_python(self):
        return f"{self.value.to_python()} {self.operator} {self.collection.to_python()}"
    
    def to_logstash(self, indent=0):
        return f"{self.value.to_logstash()} {self.operator} {self.collection.to_logstash()}"

class NotInExpression(ASTNode):
    def __init__(self, value, operator, collection):
        super().__init__()
        self.value = value
        self.operator = operator
        self.collection = collection
        self.children = [value, collection]

        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"{self.value} {self.operator} {self.collection.to_python()} "

    def to_logstash(self, indent=0):
        return f"{self.value.to_logstash()} {self.operator} {self.collection.to_logstash()})"

    def to_python(self):
        return f"{self.value.to_python()} {self.operator} {self.collection.to_python()}"
    
class NegativeExpression(ASTNode):
    def __init__(self, operator, expression):
        super().__init__()
        self.operator = operator
        self.expression = expression
        self.children = [self.expression] if isinstance(self.expression, ASTNode) else []
        
        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"not {self.expression}".replace('not not', '') # Replace double negatives with empty string. Not required but makes life easier

    def to_repr(self, indent = 0):
        return f"not {self.expression}".replace('not not', '')

    def to_python(self):
        return f"not {self.expression.to_python()}".replace("not not ", '')
    
    def to_logstash(self, indent=0):
        return f"!({self.expression.to_logstash()})"

def build_negative_expression(toks):
    return NegativeExpression(toks[0], toks[1])

class RValue(ASTNode):
    def __init__(self, value):
        super().__init__()
        self.value = value
        self.children = [value] if isinstance(value, ASTNode) else []
        
        # set parent links
        for child in self.children:
            child.parent = self

    def __repr__(self):
        return f"{self.value}"
    
    def to_python(self):
        return self.value.to_python()
    
    def to_logstash(self):
        return self.value.to_logstash()

class Expression(ASTNode):
    def __init__(self, condition):
        super().__init__()
        self.condition = condition[0]
        self.children = [condition[0]] if isinstance(condition[0], ASTNode) else []

        # set parent links
        for child in self.children:
            child.parent = self

    def to_logstash(self, indent=0):
        return self.condition.to_logstash()

    def to_python(self):
        return f"{self.condition.to_python()}"

    def to_source(self):
        return self.to_logstash()

    def __repr__(self):
        return f"{self.condition}".replace('not not', '') # Replace double negatives with empty string. Not required but makes life easier

class BooleanExpression(ASTNode):
    def __init__(self, left, operator, right):
        super().__init__()
        self.left = left
        self.operator = operator
        self.right = right
        self.children = [left, right]

        # set parent links
        for child in self.children:
            child.parent = self

    def to_logstash(self, indent=0):
        if self.operator == 'or':
            return f"{self.left.to_logstash()} {self.operator} {self.right.to_logstash()}" 
        return f"({self.left.to_logstash()} {self.operator} {self.right.to_logstash()})"

    def __repr__(self):
        return f"({self.left} {self.operator} {self.right})"
    
    def to_python(self):
        left = f"{self.left.to_python()}" if isinstance(self.left, ASTNode) else self.left
        right = f"{self.right.to_python()}" if isinstance(self.right, ASTNode) else self.right
        return f"({left} {self.operator} {right})"
    

    def to_source(self):
        return self.to_logstash()

def build_condition_node(toks):
    # t[0] is the first expression
    condition_expr = toks[0]
    
    # Starting from the second item, alternating between boolean operators and expressions
    for i in range(1, len(toks), 2):
        boolean_operator = toks[i]  # the operator (and, or, xor, nand)
        next_expression = toks[i + 1]  # the next expression
        
        # Create a new compound expression based on the boolean operator and the next expression
        condition_expr = BooleanExpression(condition_expr, boolean_operator, next_expression)
    
    return condition_expr

class IfCondition(ASTNode):
    def __init__(self, expr, body):
        super().__init__()
        self.expr = expr
        self.children = body.as_list() if isinstance(body, ParseResults) else body

        # set parent links
        for child in self.children:
            child.parent = self

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}IfCondition(expr={self.expr.to_python()})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def to_python(self):
        D = { }

        D['IfCondition'] = { 
            "expr": self.expr.to_python(),
            'children': [ child.to_python() for child in self.children ]
        }
        return D

    def to_logstash(self, indent=0, is_dm_branch=False):
        if not is_dm_branch:
            return f"if {self.expr.to_logstash(indent=0)}"
        ind = indent * " "
        out = f"{ind} if {self.expr.to_logstash(indent=0)} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2, is_dm_branch=is_dm_branch)
        out += f"{ind}}}\n"
        return out
    
def build_if_condition_node(toks):
    return IfCondition(toks[0][1][0], toks[0][1][1][0])


class ElseIfCondition(ASTNode):
    def __init__(self, expr, body):
        super().__init__()
        self.expr = expr
        self.children = body.as_list()
        self.combined_expr = None
        # set parent links
        for child in self.children:
            child.parent = self

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}ElseIfCondition(expr={self.expr.to_python()})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"


    def to_python(self):
        return self.expr.to_python()

    def to_logstash(self, indent=0, is_dm_branch=False):
        if not is_dm_branch:
            return f"else if ({self.expr.to_python()} )"
        
        ind = indent * " "
        out = f"{ind} else if {self.expr.to_python()} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2, is_dm_branch=is_dm_branch)
        out += f"{ind}}}\n"
        return out


def build_condition_else_if_node(toks):
    return ElseIfCondition(toks[0][1][0], toks[0][1][1][0])


class ElseCondition(ASTNode):
    def __init__(self, body):
        super().__init__()
        self.expr = None
        self.children = body.as_list()
        self.combined_expr = None

        # set parent links
        for child in self.children:
            child.parent = self

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}ElseCondition"
        header += f"(expr={self.expr.to_python()})" if self.expr else ""
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def to_python(self):
        return None if self.expr is None else self.expr.to_python()

    def to_logstash(self, indent=0, is_dm_branch=False):

        if not is_dm_branch:
            if self.combined_expr:
                out = f"else if {self.expr.to_logstash()} "
            else:
                out = f"else"
            return out
        
        ind = " " * indent
        if self.combined_expr:
            out = f"{ind} else if {self.expr.to_logstash()} {{\n"
        else:
            out = f"{ind} else {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2, is_dm_branch=is_dm_branch)
        out += f"{ind} }}\n"
        return out

def build_condition_else_node(toks):
    return ElseCondition(toks[0][1])

class Branch(ASTNode):
    def __init__(self, if_rule, else_if_rules=None, else_rule=None):
        super().__init__()
        if else_if_rules is None:
            else_if_rules = []
        self.children: list[Union[IfCondition, ElseIfCondition, ElseCondition]] = [if_rule] + else_if_rules
        if else_rule is not None:
            self.children.append(else_rule)

        # set parent links
        for child in self.children:
            child.parent = self

    def to_python(self):
        D = { }
        D['branch'] = { child.expr: child.to_python() for child in self.children }
        return D

    def to_logstash(self, indent=0, is_dm_branch=False) -> str:
        out = ""
        for child in self.children:
            out += child.to_logstash(indent, is_dm_branch)
        return out
    
    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Branch {{\n{children}\n{ind}}}"

def build_branch_node(toks):
    if_rule_node = toks[0]

    else_if_nodes = []
    if len(toks) > 1:
        for else_if_branch in toks[1:]:
            if isinstance(else_if_branch, ElseIfCondition):
                else_if_nodes.append(else_if_branch)
    else_node = None
    for else_branch in toks[1:]:
        if isinstance(else_branch, ElseCondition):
            else_node = else_branch

    return Branch(if_rule_node, else_if_nodes, else_node)


class PluginSectionNode(ASTNode):
    def __init__(self, plugin_type, children):
        super().__init__()
        self.plugin_type = plugin_type
        self.children: list[ASTNode] = children

        # set parent links
        for child in self.children:
            child.parent = self

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}PluginSection(type={self.plugin_type})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"
    
    def to_python(self):
        return self.plugin_type

    def to_logstash(self, indent=0, is_dm_branch=False) -> str:
        ind = " " * indent
        out = f"{ind}filter {{\n"
        children = "\n".join(c.to_logstash(indent + 2, is_dm_branch) for c in self.children)
        out += children
        out += f"{ind}}}"

        return out

def plugin_section_parse_action(t):
    plugin_type = t[0][0]  # Accessing the plugin type (e.g., "filter")
    children = t[0][1].as_list()  # Accessing the list of branch_or_plugin

    return PluginSectionNode(plugin_type, children)

class Config(ASTNode):
    def __init__(self, toks):

        super().__init__()
        self.children: list[ASTNode] = toks

        # set parent links
        for child in self.children:
            child.parent = self

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(child.to_repr(indent + 2) for child in self.children)
        return f"{ind}Config {{\n{children}\n{ind}}}"

def build_config_node(toks):
    return Config(toks)
