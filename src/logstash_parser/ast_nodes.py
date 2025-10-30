import ast
from typing import Any, Generic, TypeVar

from pyparsing import ParserElement, ParseResults

from logstash_parser import grammar

T = TypeVar("T", bound="ASTNode")


class ASTNode(Generic[T]):
    _counter = 0

    # 类变量：定义解析器名称和元素（子类可覆盖）
    _parser_name: str | None = None
    _parser_element: ParserElement | None = None

    def __init__(
        self,
        s: str | None = None,
        loc: int | None = None,
    ) -> None:
        self.children: list[T] = []
        self.in_expression_context = False

        # 延迟计算所需的信息
        self._s = s
        self._loc = loc

        # 缓存的 source_text (延迟计算)
        self._source_text_cache: str | None = None

        self.uid = ASTNode._counter
        ASTNode._counter += 1

    def get_source_text(self) -> str | None:
        """延迟获取 source text，只在需要时才提取"""
        # 如果已经缓存，直接返回
        if self._source_text_cache is not None:
            return self._source_text_cache

        # 如果有延迟计算信息，现在计算
        if self._s is not None and self._loc is not None and self._parser_name and self._parser_element:
            # 直接提取，不需要全局缓存函数
            result = self._parser_element.searchString(self._s[self._loc :])
            if result:
                self._source_text_cache = str(result.as_list()[0][0])
            else:
                raise ValueError(f"Failed to extract source text for {self._parser_name} at location {self._loc}")
            return self._source_text_cache

        return None

    def set_expression_context(self, value: bool):
        self.in_expression_context = value
        for child in self.children:
            if isinstance(child, ASTNode):
                child.set_expression_context(value)

    def traverse(self):
        """Recursively traverse and call the `recurse` function on each child."""
        for child in self.children:
            child.traverse()

    def to_source(self) -> str | int | float:
        """Convert the AST node to a string representation for rendering.

        If source text is available, returns it directly.
        Otherwise, reconstructs the source from child nodes.
        """
        # If we have source text, return it
        source_text = self.get_source_text()
        if source_text is not None:
            return source_text

        # Otherwise, subclasses must implement reconstruction logic
        raise NotImplementedError(
            f"{self.__class__.__name__}.to_source() must be implemented or source text must be set"
        )

    def to_python(self):
        """Convert the AST node to a Python representation (to be defined later)."""
        raise NotImplementedError

    def to_logstash(self):
        """Convert the AST node to a Logstash representation (to be defined later)."""
        raise NotImplementedError

    def __repr__(self):
        return self.to_repr()

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"{self.__class__.__name__}"


class LSString(ASTNode):
    def __init__(self, lexeme: str):
        super().__init__()

        # NOTE: When rendering / printing, lexeme will have quotations around it.
        self.lexeme = lexeme  # in python, this is like: '"message"'

        try:
            # NOTE: When rendering / printing, self.value won't have the quotation marks around it
            # as its a native python type
            # Characters like \f, \t, \n, etc are treated as python literals.
            # E.g. \n will be parsed and rendered as newline in self.value, which is expected
            # You cannot use raw string while doing literal_eval as of yet. It breaks the later code.
            safe_lexeme = lexeme.replace("\r\n", "\\n").replace("\n", "\\n")
            self.value = ast.literal_eval(f"""{safe_lexeme}""")
        except Exception as e:
            raise ValueError(f"Invalid string literal {lexeme!r}: {e}") from None

    def to_python(self):
        # 简单节点:直接返回 Python 原生类型
        if self.in_expression_context:
            return repr(self.value)
        return self.value

    def to_source(self):
        return self.lexeme

    def to_logstash(self, indent=0):
        # 保留原始引号类型(单引号或双引号)
        return self.lexeme

    def __repr__(self):
        return f"LSString({self.lexeme!r})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"LSString({self.lexeme!r})"


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
        # 简单节点:直接返回字符串
        return self.value

    def to_logstash(self):
        return self.value

    def to_source(self):
        return self.lexeme


class Regexp(ASTNode):
    def __init__(self, lexeme: str):
        super().__init__()

        # NOTE: When rendering / printing, lexeme will have quotations around it.
        self.lexeme = lexeme  # in python, this is like: '"message"'

        try:
            self.value = rf"{lexeme}"

        except Exception as e:
            raise ValueError(f"Invalid string literal {lexeme!r}: {e}") from None

    def to_python(self):
        # 简单节点:直接返回正则表达式字符串
        if self.in_expression_context:
            return repr(self.value)
        return self.value

    def to_source(self):
        return self.lexeme

    def to_logstash(self, indent=0):
        return f"/{self.lexeme}/"

    def __repr__(self):
        return f"LSString({self.lexeme!r})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Regexp({self.lexeme!r})"


class Number(ASTNode):
    def __init__(self, value: int | float):
        super().__init__()
        self.lexeme: int | float = value
        self.value: int | float = value

    def __repr__(self):
        return str(self.value)

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Number({self.value})"

    def to_python(self) -> int | float:
        # 简单节点:直接返回数字
        return self.value

    def to_logstash(self, indent: int = 0) -> int | float:
        return self.value

    def to_source(self) -> int | float:
        return self.lexeme


class Array(ASTNode[ASTNode]):
    _parser_name = "array"
    _parser_element = grammar.array_with_source

    def __init__(self, values: list[ASTNode], s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.children: list[ASTNode] = values  # Generally the elements are either Hash or LSString

    def to_python(self) -> list[Any]:
        # 数据结构节点:直接返回 Python list
        return [val.to_python() for val in self.children]

    def __repr__(self):
        return f"Array {[val.to_python() for val in self.children]}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Array[\n{children}\n{ind}]"

    def to_logstash(self, indent: int = 0) -> str:
        ind = " " * indent
        inner_parts: list[str] = []
        for c in self.children:
            if isinstance(c, Hash) or isinstance(c, HashEntryNode):
                inner_parts.append(f"\n{ind}{c.to_logstash(indent=indent + 2)}\n")
            else:
                source = c.to_source()
                inner_parts.append(str(source) if not isinstance(source, str) else source)
        _ = ", ".join(inner_parts)
        return f"{ind}{self.to_source()}"  # NOTE: here, we aren't doing to_logstash() because of quotation marks issues


class HashEntryNode(ASTNode):
    """Corresponds to hash_entry in PEG"""

    _parser_name = "hash_entry"
    _parser_element = grammar.hash_entry_with_source

    def __init__(self, key, value, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.key: LSString | LSBareWord | Number = (
            key  # Can be either LSString or Number or LSBareWord. LSString can be assumed to not have escapes
        )
        self.value: ASTNode = value

    def __repr__(self):
        return self.to_repr()

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        return f"{ind}HashEntry(\n{self.key.to_repr(indent + 2)} => {self.value.to_repr()}\n{ind})"

    def to_logstash(self, indent: int = 0) -> str:
        ind = indent * " "
        key_source = self.key.to_source()
        out = f"{ind}{key_source if isinstance(key_source, str) else str(key_source)} => "
        if isinstance(self.value, Hash):
            out += f"\n{self.value.to_logstash(indent + 2)}\n"
        else:
            value_source = self.value.to_source()
            out += value_source if isinstance(value_source, str) else str(value_source)
            out += "\n"
        return out

    def to_python(self) -> tuple[str | int | float, Any]:
        # HashEntry 返回键值对元组，由 Hash 节点组装成 dict
        return (self.key.to_python(), self.value.to_python())


class Hash(ASTNode[HashEntryNode]):
    """
    Corresponds to hashmap in PEG.
    Pretty much the same as hash_entries, except that hashmap wraps hash_entries in braces
    """

    _parser_name = "hashmap"
    _parser_element = grammar.hashmap_with_source

    def __init__(self, entries: list[HashEntryNode], s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.children: list[HashEntryNode] = [*entries]

    def __repr__(self):
        return self.to_repr()

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Hash {{\n{children}\n{ind}}}"

    def to_python(self) -> dict[str | int | float, Any]:
        # 数据结构节点:直接返回 Python dict
        hash_object: dict[str | int | float, Any] = {}

        for entry in self.children:
            key, value = entry.to_python()
            hash_object[key] = value

        return hash_object

    def to_logstash(self, indent: int = 0) -> str:
        ind = " " * indent
        out = f"{ind}{{\n"
        for entry in self.children:
            out += entry.to_logstash(indent + 2)
        out += f"{ind}}}\n"
        return out


class Attribute(ASTNode):
    _parser_name = "attribute"
    _parser_element = grammar.attribute_with_source

    def __init__(self, name, value, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.name: LSString | LSBareWord = name  # Either LSString or LSBareWord
        self.value: ASTNode = value

    def __repr__(self):
        return f"Attribute {repr(self.name)} => {self.value}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        return f"{ind}Attribute(\n{self.name.to_repr(indent + 2)} => {self.value.to_repr(indent + 2)}\n{ind})"

    def to_python(self) -> dict[str, Any]:
        # Attribute 节点:返回键值对 dict
        name_key = self.name.to_python() if isinstance(self.name, ASTNode) else self.name
        value_val = self.value.to_python() if isinstance(self.value, ASTNode) else self.value
        return {name_key: value_val}

    def to_logstash(self, indent: int = 0) -> str:
        ind = indent * " "
        name_logstash = self.name.to_logstash() if isinstance(self.name, ASTNode) else self.name
        out = f"{ind}{name_logstash if isinstance(name_logstash, str) else str(name_logstash)} => "

        if isinstance(self.value, Hash):
            out += f"\n{self.value.to_logstash(indent + 2)}\n"
        else:
            value_source = self.value.to_logstash()
            out += value_source if isinstance(value_source, str) else str(value_source)
            out += "\n"
        return out


class Plugin(ASTNode[Attribute]):
    _parser_name = "plugin"
    _parser_element = grammar.plugin_with_source

    def __init__(
        self, plugin_name: str | LSBareWord, attributes: list[Attribute], s: str | None = None, loc: int | None = None
    ):
        super().__init__(s=s, loc=loc)
        self.plugin_name: str = (
            plugin_name if isinstance(plugin_name, str) else plugin_name.to_python()
        )  # This is LSBareWord when Logstash is first parsed
        self.children: list[Attribute] = attributes

    def __repr__(self):
        return f"Plugin {self.plugin_name}: {self.children}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}Plugin({self.plugin_name})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def to_python(self) -> dict[str, list[dict[str, Any]]]:
        d: list[dict[str, Any]] = []
        for attribute in self.children:
            d.append(attribute.to_python())

        plugin_object: dict[str, list[dict[str, Any]]] = {self.plugin_name: d}
        return plugin_object

    def to_logstash(self, indent: int = 0, is_dm_branch: bool = False) -> str:
        ind = indent * " "
        out = f"{ind}{self.plugin_name} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2)

        out += f"{ind}}}\n"
        return out


class Boolean(ASTNode):
    def __init__(self, value: bool):
        super().__init__()
        self.value: bool = value

    def to_python(self) -> bool:
        # 简单节点:直接返回布尔值
        return self.value

    def to_logstash(self, indent: int = 0) -> str:
        return str(self.value).lower()

    def to_source(self) -> str:
        return str(self.value).lower()

    def __repr__(self):
        return str(self.to_python())

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Boolean({self.value})"


class SelectorNode(ASTNode):
    """
    Represents a Log-Stash field reference like [foo][bar][baz]
    We keep the raw selector string around for fidelity.
    """

    def __init__(self, raw: str | ASTNode):
        super().__init__()
        self.raw: str | ASTNode = raw
        self.children: list[ASTNode] = [raw] if isinstance(raw, ASTNode) else []

    def __repr__(self):
        return f"SelectorNode( {str(self.raw)})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"SelectorNode({self.raw})"

    def to_python(self) -> str:
        # 简单节点:直接返回选择器字符串
        return str(self.raw)

    def to_logstash(self, indent: int = 0) -> str:
        return str(self.raw)

    def to_source(self) -> str:
        return str(self.raw)


class RegexExpression(ASTNode):
    _parser_name = "regexp_expression"
    _parser_element = grammar.regexp_expression_with_source

    def __init__(self, left: ASTNode, operator: str, pattern: ASTNode, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)

        self.left: ASTNode = left
        self.operator: str = operator
        self.pattern: ASTNode = pattern

        self.children: list[ASTNode] = [left, pattern]

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def to_python(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "regex_expression",
            "left": self.left.to_python(),
            "operator": self.operator,
            "pattern": self.pattern.to_python(),
        }

    def to_logstash(self, indent: int = 0) -> str:
        return f"{self.left.to_logstash()} {self.operator} {self.pattern.to_logstash()}"


class CompareExpression(ASTNode):
    _parser_name = "compare_expression"
    _parser_element = grammar.compare_expression_with_source

    def __init__(self, left: ASTNode, operator: str, right: ASTNode, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.left: ASTNode = left
        self.operator: str = operator
        self.right: ASTNode = right
        self.children: list[ASTNode] = [left, right]

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def __repr__(self):
        return f"{self.left} {self.operator} {self.right}"

    def to_python(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "compare_expression",
            "left": self.left.to_python(),
            "operator": self.operator,
            "right": self.right.to_python(),
        }

    def to_logstash(self, indent=0):
        return f"{self.left.to_logstash()} {self.operator} {self.right.to_logstash()}"


class InExpression(ASTNode):
    _parser_name = "in_expression"
    _parser_element = grammar.in_expression_with_source

    def __init__(self, value, operator, collection, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.value = value
        self.operator = operator
        self.collection = collection
        self.children = [value, collection]

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def __repr__(self):
        return f"InExpression({self.value} {self.operator} {self.collection})"

    def to_python(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "in_expression",
            "value": self.value.to_python(),
            "operator": self.operator,
            "collection": self.collection.to_python(),
        }

    def to_logstash(self, indent=0):
        return f"{self.value.to_logstash()} {self.operator} {self.collection.to_logstash()}"


class NotInExpression(ASTNode):
    _parser_name = "not_in_expression"
    _parser_element = grammar.not_in_expression_with_source

    def __init__(self, value, operator, collection, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.value = value
        self.operator = operator
        self.collection = collection
        self.children = [value, collection]

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def __repr__(self):
        return f"{self.value} {self.operator} {self.collection.to_python()} "

    def to_logstash(self, indent=0):
        return f"{self.value.to_logstash()} {self.operator} {self.collection.to_logstash()})"

    def to_python(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "not_in_expression",
            "value": self.value.to_python(),
            "operator": self.operator,
            "collection": self.collection.to_python(),
        }


class NegativeExpression(ASTNode):
    _parser_name = "negative_expression"
    _parser_element = grammar.negative_expression_with_source

    def __init__(self, operator, expression, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.operator = operator
        self.expression = expression
        self.children = [self.expression] if isinstance(self.expression, ASTNode) else []
        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def __repr__(self):
        return f"not {self.expression}".replace(
            "not not", ""
        )  # Replace double negatives with empty string. Not required but makes life easier

    def to_repr(self, indent=0):
        return f"not {self.expression}".replace("not not", "")

    def to_python(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "negative_expression",
            "operator": self.operator,
            "expression": self.expression.to_python(),
        }

    def to_logstash(self, indent=0):
        return f"!({self.expression.to_logstash()})"


class RValue(ASTNode):
    def __init__(self, value: LSString | Number | SelectorNode | Array | Regexp):
        super().__init__()
        self.value = value
        self.children = [value] if isinstance(value, ASTNode) else []

    def __repr__(self):
        return f"{self.value}"

    def to_python(self):
        return self.value.to_python()

    def to_logstash(self):
        return self.value.to_logstash()


class Expression(ASTNode):
    _parser_name = "expression"
    _parser_element = grammar.expression_with_source

    def __init__(self, condition, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.condition = condition[0]
        self.children = [condition[0]] if isinstance(condition[0], ASTNode) else []

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def to_logstash(self, indent=0):
        return self.condition.to_logstash()

    def to_python(self):
        # Expression 是包装器，直接返回内部 condition 的结果
        return self.condition.to_python()

    def __repr__(self):
        return f"{self.condition}".replace(
            "not not", ""
        )  # Replace double negatives with empty string. Not required but makes life easier


class BooleanExpression(ASTNode[ASTNode]):
    # BooleanExpression 不需要 parser_element，因为它可以从子节点重构

    def __init__(self, left, operator, right):
        super().__init__()

        self.left = left
        self.operator = operator
        self.right = right
        self.children = [left, right]

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def to_logstash(self, indent=0):
        if self.operator == "or":
            return f"{self.left.to_logstash()} {self.operator} {self.right.to_logstash()}"
        return f"({self.left.to_logstash()} {self.operator} {self.right.to_logstash()})"

    def __repr__(self):
        return f"({self.left} {self.operator} {self.right})"

    def to_python(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "boolean_expression",
            "left": self.left.to_python(),
            "operator": self.operator,
            "right": self.right.to_python(),
        }

    def to_source(self):
        # 从子节点重构 source text
        left_source = self.left.to_source() if isinstance(self.left, ASTNode) else str(self.left)
        right_source = self.right.to_source() if isinstance(self.right, ASTNode) else str(self.right)
        return f"{left_source} {self.operator} {right_source}"


class IfCondition(ASTNode["Plugin | Branch"]):
    _parser_name = "if_condition"
    _parser_element = grammar.if_rule_with_source

    def __init__(self, expr: Expression | BooleanExpression, body, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.expr = expr
        self.children = body.as_list() if isinstance(body, ParseResults) else body

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}IfCondition(expr={self.expr.to_python()})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def to_python(self) -> dict[str, Any]:
        # Branch condition 节点:返回结构化对象
        return {
            "type": "if",
            "expr": self.expr.to_python(),
            "body": [child.to_python() for child in self.children],
        }

    def to_logstash(self, indent=0, is_dm_branch=False):
        if not is_dm_branch:
            return f"if {self.expr.to_logstash(indent=0)}"
        ind = indent * " "
        out = f"{ind} if {self.expr.to_logstash(indent=0)} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2, is_dm_branch=is_dm_branch)
        out += f"{ind}}}\n"
        return out


class ElseIfCondition(ASTNode["Plugin | Branch"]):
    _parser_name = "else_if_condition"
    _parser_element = grammar.else_if_rule_with_source

    def __init__(self, expr: Expression | BooleanExpression, body, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.expr = expr
        self.children = body.as_list()
        self.combined_expr = None

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}ElseIfCondition(expr={self.expr.to_python()})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def to_python(self) -> dict[str, Any]:
        # Branch condition 节点:返回结构化对象
        return {
            "type": "else_if",
            "expr": self.expr.to_python(),
            "body": [child.to_python() for child in self.children],
        }

    def to_logstash(self, indent=0, is_dm_branch=False):
        if not is_dm_branch:
            return f"else if ({self.expr.to_python()} )"

        ind = indent * " "
        out = f"{ind} else if {self.expr.to_python()} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2, is_dm_branch=is_dm_branch)
        out += f"{ind}}}\n"
        return out


class ElseCondition(ASTNode["Plugin | Branch"]):
    _parser_name = "else_condition"
    _parser_element = grammar.else_rule_with_source

    def __init__(self, body, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.expr: Expression | BooleanExpression | None = None
        self.children = body.as_list()
        self.combined_expr = None

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}ElseCondition"
        header += f"(expr={self.expr.to_python()})" if self.expr else ""
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def to_python(self) -> dict[str, Any]:
        # Branch condition 节点:返回结构化对象
        # else 没有 expr
        return {
            "type": "else",
            "body": [child.to_python() for child in self.children],
        }

    def to_logstash(self, indent=0, is_dm_branch=False):
        if not is_dm_branch:
            if self.combined_expr and self.expr:
                out = f"else if {self.expr.to_logstash()} "
            else:
                out = "else"
            return out

        ind = " " * indent
        if self.combined_expr and self.expr:
            out = f"{ind} else if {self.expr.to_logstash()} {{\n"
        else:
            out = f"{ind} else {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2, is_dm_branch=is_dm_branch)
        out += f"{ind} }}\n"
        return out


class Branch(ASTNode[IfCondition | ElseIfCondition | ElseCondition]):
    _parser_name = "branch"
    _parser_element = grammar.branch_with_source

    def __init__(
        self,
        if_rule: IfCondition,
        else_if_rules: list[ElseIfCondition] | None = None,
        else_rule: ElseCondition | None = None,
        s: str | None = None,
        loc: int | None = None,
    ):
        super().__init__(s=s, loc=loc)
        if else_if_rules is None:
            else_if_rules = []
        else_rules: list[ElseCondition] = []
        if else_rule:
            else_rules = [else_rule]

        # Build children list with explicit type
        children: list[IfCondition | ElseIfCondition | ElseCondition] = [if_rule]
        children.extend(else_if_rules)
        children.extend(else_rules)
        self.children = children

    def to_python(self) -> dict[str, Any]:
        # Branch 节点:返回结构化对象
        return {
            "type": "branch",
            "conditions": [child.to_python() for child in self.children],
        }

    def to_logstash(self, indent=0, is_dm_branch=False) -> str:
        out = ""
        for child in self.children:
            out += child.to_logstash(indent, is_dm_branch=True)
        return out

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Branch {{\n{children}\n{ind}}}"


class PluginSectionNode(ASTNode[Plugin]):
    _parser_name = "plugin_section"
    _parser_element = grammar.plugin_section_with_source

    def __init__(self, plugin_type, children, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.plugin_type = plugin_type
        self.children = children

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}PluginSection(type={self.plugin_type})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def to_python(self):
        # Return a dictionary with plugin_type as key and list of children as value
        children_data = []
        for child in self.children:
            children_data.append(child.to_python())
        return {self.plugin_type: children_data}

    def to_logstash(self, indent=0, is_dm_branch=False) -> str:
        ind = " " * indent
        out = f"{ind}{self.plugin_type} {{\n"
        children = "\n".join(c.to_logstash(indent + 2, is_dm_branch) for c in self.children)
        out += children
        out += f"{ind}}}"

        return out


class Config(ASTNode[PluginSectionNode]):
    _parser_name = "config"
    _parser_element = grammar.config_with_source

    def __init__(
        self,
        toks,
        s: str | None = None,
        loc: int | None = None,
    ):
        super().__init__(s=s, loc=loc)
        self.children = toks

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(child.to_repr(indent + 2) for child in self.children)
        return f"{ind}Config {{\n{children}\n{ind}}}"

    def to_python(self):
        """Convert the Config AST to a Python dictionary representation.

        Returns a dictionary where keys are plugin types (input/filter/output)
        and values are lists of all sections of that type.
        """
        config_dict = {}

        for child in self.children:
            if isinstance(child, PluginSectionNode):
                child_data = child.to_python()
                # child_data is like {"filter": [...]}
                for plugin_type, content in child_data.items():
                    if plugin_type not in config_dict:
                        config_dict[plugin_type] = []
                    config_dict[plugin_type].extend(content)

        return config_dict

    def to_logstash(self, indent=0, is_dm_branch=False) -> str:
        """Convert the Config AST back to Logstash configuration format."""
        out = ""
        for child in self.children:
            if isinstance(child, PluginSectionNode):
                out += child.to_logstash(indent, is_dm_branch)
                out += "\n"
        return out.rstrip() + "\n"


def build_lsstring(toks: ParseResults):
    value = toks.as_list()[0]
    return LSString(value)


def build_lsbw(toks: ParseResults):
    value = toks.as_list()[0]
    return LSBareWord(value)


def build_name(toks: ParseResults):
    value = toks.as_list()[0]
    return value if isinstance(value, LSString) else LSBareWord(value)


def build_regexp(toks: ParseResults):
    value = toks.as_list()[0]
    return Regexp(value)


def build_number(toks: ParseResults) -> Number:
    value = toks[0]
    return Number(value)  # type: ignore[arg-type]


def build_array_node(s, loc, toks: ParseResults) -> Array:
    values = list(toks)[0]
    return Array(values, s=s, loc=loc)


def build_hash_entry_node(s, loc, toks: ParseResults) -> HashEntryNode:
    toks_list = list(toks)[0]
    return HashEntryNode(toks_list[0], toks_list[1][0], s=s, loc=loc)


def build_hash_node(s, loc, toks: ParseResults) -> Hash:
    return Hash(list(toks)[0], s=s, loc=loc)


def build_attribute_node(s, loc, toks: ParseResults) -> Attribute:
    return Attribute(toks[0][0], toks[0][1][0], s=s, loc=loc)


def build_plugin_node(s, loc, toks: ParseResults) -> Plugin:
    return Plugin(list(toks)[0][0], list(toks)[0][1], s=s, loc=loc)


def build_boolean_node(toks: ParseResults) -> Boolean:
    return Boolean(list(toks)[0])


def build_selector_node(toks: ParseResults) -> SelectorNode:
    value = list(toks)[0]
    return SelectorNode(value)


def build_regexp_node(s, loc, toks: ParseResults) -> RegexExpression:
    return RegexExpression(list(toks)[0], list(toks)[1], list(toks)[2], s=s, loc=loc)


def build_compare_expression(s, loc, toks: ParseResults):
    return CompareExpression(list(toks)[0], list(toks)[1], list(toks)[2], s=s, loc=loc)


def build_in_expression(s, loc, toks: ParseResults):
    return InExpression(list(toks)[0], list(toks)[1], list(toks)[2], s=s, loc=loc)


def build_not_in_expression(s, loc, toks: ParseResults):
    return NotInExpression(list(toks)[0], list(toks)[1], list(toks)[2], s=s, loc=loc)


def build_negative_expression(s, loc, toks):
    return NegativeExpression(toks[0], toks[1], s=s, loc=loc)


def build_rvalue(toks: ParseResults):
    # RValue 通常不需要保存原始文本，因为它只是包装
    rvalue = toks.as_list()[0]
    return RValue(rvalue)


def build_expression(s, loc, toks: ParseResults):
    return Expression(list(toks)[0], s=s, loc=loc)


def build_condition_node(toks):
    # t[0] is the first expression
    condition_expr = toks[0]

    # Starting from the second item, alternating between boolean operators and expressions
    for i in range(1, len(toks), 2):
        boolean_operator = toks[i]  # the operator (and, or, xor, nand)
        next_expression = toks[i + 1]  # the next expression

        # Create a new compound expression based on the boolean operator and the next expression
        # BooleanExpression 会在 to_source() 中从子节点重构 source text
        condition_expr = BooleanExpression(condition_expr, boolean_operator, next_expression)

    return condition_expr


def build_if_condition_node(s, loc, toks):
    return IfCondition(toks[0][1][0], toks[0][1][1][0], s=s, loc=loc)


def build_condition_else_if_node(s, loc, toks):
    return ElseIfCondition(toks[0][1][0], toks[0][1][1][0], s=s, loc=loc)


def build_condition_else_node(s, loc, toks):
    return ElseCondition(toks[0][1], s=s, loc=loc)


def build_branch_node(s, loc, toks):
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

    return Branch(if_rule_node, else_if_nodes, else_node, s=s, loc=loc)


def build_plugin_section_node(s, loc, toks):
    plugin_type = toks[0][0]
    children = toks[0][1].as_list()

    return PluginSectionNode(plugin_type, children, s=s, loc=loc)


def build_config_node(s, loc, toks):
    """Build config node with original source text.

    Args:
        s: The original parse string
        loc: Current location in the string (unused but required by pyparsing)
        toks: Parse results
    """
    # Config node represents the entire document
    config = Config(toks, s=s, loc=loc)
    return config
