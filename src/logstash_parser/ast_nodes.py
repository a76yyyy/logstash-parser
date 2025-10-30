import ast
from typing import Any, Generic, Literal, TypeVar, overload

from pyparsing import ParserElement, ParseResults

from logstash_parser import grammar
from logstash_parser.schemas import (
    ArraySchema,
    ASTNodeSchema,
    AttributeSchema,
    BooleanExpressionSchema,
    BooleanSchema,
    BranchSchema,
    CompareExpressionSchema,
    ConfigSchema,
    ElseConditionSchema,
    ElseIfConditionSchema,
    ExpressionSchema,
    HashEntryNodeSchema,
    HashSchema,
    IfConditionSchema,
    InExpressionSchema,
    LSBareWordSchema,
    LSStringSchema,
    NegativeExpressionSchema,
    NotInExpressionSchema,
    NumberSchema,
    PluginSchema,
    PluginSectionNodeSchema,
    RegexExpressionSchema,
    RegexpSchema,
    SelectorNodeSchema,
)

T = TypeVar("T", bound="ASTNode")


class ASTNode(Generic[T]):
    _counter = 0

    # 类变量：定义解析器名称和元素（子类可覆盖）
    _parser_name: str | None = None
    _parser_element: ParserElement | None = None

    # Schema 类引用（子类必须覆盖，这里只是占位）
    schema_class: type["ASTNodeSchema"]

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

    @overload
    def to_python(self, as_pydantic: Literal[False] = False) -> Any: ...

    @overload
    def to_python(self, as_pydantic: Literal[True]) -> ASTNodeSchema: ...

    def to_python(self, as_pydantic: bool = False) -> Any:
        """Convert the AST node to a Python representation.

        Args:
            as_pydantic: If True, return Pydantic Schema object; if False, return dict/native types

        Returns:
            Pydantic Schema object if as_pydantic=True, otherwise dict or native Python types
        """
        if as_pydantic:
            return self._to_pydantic_model()
        return self._to_python_dict()

    def _to_python_dict(self) -> Any:
        """Convert to Python dict or native types (subclasses must implement)."""
        raise NotImplementedError(f"{self.__class__.__name__}._to_python_dict() must be implemented")

    def _to_pydantic_model(self) -> ASTNodeSchema:
        """Convert to Pydantic Schema (subclasses must implement)."""
        raise NotImplementedError(f"{self.__class__.__name__}._to_pydantic_model() must be implemented")

    @classmethod
    def from_python(cls, data: dict[str, Any] | ASTNodeSchema) -> "ASTNode":
        """Create AST node from Python representation.

        Args:
            data: Either a dict or a Pydantic Schema object

        Returns:
            AST node instance
        """
        # If it's a dict, convert to Schema first
        if isinstance(data, dict):
            data = cls.schema_class.model_validate(data)

        # Now data is a Schema object, use _from_pydantic
        return cls._from_pydantic(data)  # type: ignore[arg-type]

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "ASTNode":
        """Create AST node from Pydantic Schema (subclasses must implement)."""
        raise NotImplementedError(f"{cls.__name__}._from_pydantic() must be implemented")

    def to_logstash(self):
        """Convert the AST node to a Logstash representation (to be defined later)."""
        raise NotImplementedError

    def __repr__(self):
        return self.to_repr()

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"{self.__class__.__name__}"


class LSString(ASTNode):
    schema_class = LSStringSchema

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

    def _to_python_dict(self):
        # 简单节点:直接返回 Python 原生类型
        if self.in_expression_context:
            return repr(self.value)
        return self.value

    def _to_pydantic_model(self) -> LSStringSchema:
        return LSStringSchema(
            source_text=self.get_source_text(),
            lexeme=self.lexeme,
            value=self.value,
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "LSString":
        assert isinstance(schema, LSStringSchema)
        node = cls(schema.lexeme)
        node._source_text_cache = schema.source_text
        return node

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

    schema_class = LSBareWordSchema

    def __init__(self, value: str):
        super().__init__()
        self.lexeme = value
        self.value = value

    def __repr__(self):
        return f"LSBareWord({self.value})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"LSBareWord({self.value})"

    def _to_python_dict(self):
        # 简单节点:直接返回字符串
        return self.value

    def _to_pydantic_model(self) -> LSBareWordSchema:
        return LSBareWordSchema(
            source_text=self.get_source_text(),
            value=self.value,
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "LSBareWord":
        assert isinstance(schema, LSBareWordSchema)
        node = cls(schema.value)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self):
        return self.value

    def to_source(self):
        return self.lexeme


class Regexp(ASTNode):
    schema_class = RegexpSchema

    def __init__(self, lexeme: str):
        super().__init__()

        # NOTE: When rendering / printing, lexeme will have quotations around it.
        self.lexeme = lexeme  # in python, this is like: '"message"'

        try:
            self.value = rf"{lexeme}"

        except Exception as e:
            raise ValueError(f"Invalid string literal {lexeme!r}: {e}") from None

    def _to_python_dict(self):
        # 简单节点:直接返回正则表达式字符串
        if self.in_expression_context:
            return repr(self.value)
        return self.value

    def _to_pydantic_model(self) -> RegexpSchema:
        return RegexpSchema(
            source_text=self.get_source_text(),
            lexeme=self.lexeme,
            value=self.value,
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Regexp":
        assert isinstance(schema, RegexpSchema)
        node = cls(schema.lexeme)
        node._source_text_cache = schema.source_text
        return node

    def to_source(self):
        return self.lexeme

    def to_logstash(self, indent=0):
        return f"/{self.lexeme}/"

    def __repr__(self):
        return f"LSString({self.lexeme!r})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Regexp({self.lexeme!r})"


class Number(ASTNode):
    schema_class = NumberSchema

    def __init__(self, value: int | float):
        super().__init__()
        self.lexeme: int | float = value
        self.value: int | float = value

    def __repr__(self):
        return str(self.value)

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Number({self.value})"

    def _to_python_dict(self) -> int | float:
        # 简单节点:直接返回数字
        return self.value

    def _to_pydantic_model(self) -> NumberSchema:
        return NumberSchema(
            source_text=self.get_source_text(),
            value=self.value,
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Number":
        assert isinstance(schema, NumberSchema)
        node = cls(schema.value)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent: int = 0) -> int | float:
        return self.value

    def to_source(self) -> int | float:
        return self.lexeme


class Array(ASTNode[ASTNode]):
    schema_class = ArraySchema
    _parser_name = "array"
    _parser_element = grammar.array_with_source

    def __init__(self, values: list[ASTNode], s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.children: list[ASTNode] = values  # Generally the elements are either Hash or LSString

    def _to_python_dict(self) -> list[Any]:
        # 数据结构节点:直接返回 Python list
        return [val._to_python_dict() for val in self.children]

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return ArraySchema(
            source_text=self.get_source_text(),
            children=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Array":
        assert isinstance(schema, ArraySchema)
        children = [_schema_to_node(child) for child in schema.children]
        node = cls(children)
        node._source_text_cache = schema.source_text
        return node

    def __repr__(self):
        return f"Array {[val._to_python_dict() for val in self.children]}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Array[\n{children}\n{ind}]"

    def to_source(self) -> str:
        """Reconstruct array source from children."""
        # Try to get cached source text first
        source_text = self.get_source_text()
        if source_text is not None:
            return source_text

        # Reconstruct from children
        inner_parts: list[str] = []
        for c in self.children:
            source = c.to_source()
            inner_parts.append(str(source) if not isinstance(source, str) else source)
        return "[" + ", ".join(inner_parts) + "]"

    def to_logstash(self, indent: int = 0) -> str:
        ind = " " * indent
        # Reconstruct from children for logstash output
        inner_parts: list[str] = []
        for c in self.children:
            if isinstance(c, Hash):
                # Hash needs special formatting - strip indent
                inner_parts.append(c.to_logstash().strip())
            else:
                # For other types, use to_logstash
                child_output = c.to_logstash()
                inner_parts.append(str(child_output) if not isinstance(child_output, str) else child_output)
        return f"{ind}[" + ", ".join(inner_parts) + "]"


class HashEntryNode(ASTNode):
    """Corresponds to hash_entry in PEG"""

    schema_class = HashEntryNodeSchema
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
        # Use to_logstash for key
        key_output = self.key.to_logstash()
        out = f"{ind}{key_output if isinstance(key_output, str) else str(key_output)} => "
        if isinstance(self.value, Hash):
            out += f"\n{self.value.to_logstash(indent + 2)}\n"
        else:
            # Use to_logstash for value
            value_output = self.value.to_logstash()
            out += value_output if isinstance(value_output, str) else str(value_output)
            out += "\n"
        return out

    def _to_python_dict(self) -> tuple[str | int | float, Any]:
        # HashEntry 返回键值对元组，由 Hash 节点组装成 dict
        return (self.key._to_python_dict(), self.value._to_python_dict())

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return HashEntryNodeSchema(
            source_text=self.get_source_text(),
            key=self.key._to_pydantic_model(),  # type: ignore[arg-type]
            value=self.value._to_pydantic_model(),  # type: ignore[arg-type]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "HashEntryNode":
        assert isinstance(schema, HashEntryNodeSchema)
        key = _schema_to_node(schema.key)
        value = _schema_to_node(schema.value)
        node = cls(key, value)
        node._source_text_cache = schema.source_text
        return node


class Hash(ASTNode[HashEntryNode]):
    """
    Corresponds to hashmap in PEG.
    Pretty much the same as hash_entries, except that hashmap wraps hash_entries in braces
    """

    schema_class = HashSchema
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

    def _to_python_dict(self) -> dict[str | int | float, Any]:
        # 数据结构节点:直接返回 Python dict
        hash_object: dict[str | int | float, Any] = {}

        for entry in self.children:
            key, value = entry._to_python_dict()
            hash_object[key] = value

        return hash_object

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return HashSchema(
            source_text=self.get_source_text(),
            children=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Hash":
        assert isinstance(schema, HashSchema)
        children = [HashEntryNode._from_pydantic(child) for child in schema.children]
        node = cls(children)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent: int = 0) -> str:
        ind = " " * indent
        out = f"{ind}{{\n"
        for entry in self.children:
            out += entry.to_logstash(indent + 2)
        out += f"{ind}}}\n"
        return out


class Attribute(ASTNode):
    schema_class = AttributeSchema
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

    def _to_python_dict(self) -> dict[str, Any]:
        name_key = self.name._to_python_dict()
        value_val = (
            self.value._to_python_dict()
            if hasattr(self.value, "_to_python_dict")
            else (self.value._to_python_dict() if isinstance(self.value, ASTNode) else self.value)
        )
        return {name_key: value_val}

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return AttributeSchema(
            source_text=self.get_source_text(),
            name=self.name._to_pydantic_model(),  # type: ignore[arg-type]
            value=self.value._to_pydantic_model(),  # type: ignore[arg-type]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Attribute":
        assert isinstance(schema, AttributeSchema)
        name = _schema_to_node(schema.name)
        value = _schema_to_node(schema.value)
        node = cls(name, value)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent: int = 0) -> str:
        ind = indent * " "
        name_logstash = self.name.to_logstash() if isinstance(self.name, ASTNode) else self.name
        out = f"{ind}{name_logstash if isinstance(name_logstash, str) else str(name_logstash)} => "

        if isinstance(self.value, Hash):
            out += f"\n{self.value.to_logstash(indent + 2)}\n"
        else:
            value_output = self.value.to_logstash()
            out += value_output if isinstance(value_output, str) else str(value_output)
            out += "\n"
        return out


class Plugin(ASTNode[Attribute]):
    schema_class = PluginSchema
    _parser_name = "plugin"
    _parser_element = grammar.plugin_with_source

    def __init__(
        self, plugin_name: str | LSBareWord, attributes: list[Attribute], s: str | None = None, loc: int | None = None
    ):
        super().__init__(s=s, loc=loc)
        self.plugin_name: str = (
            plugin_name if isinstance(plugin_name, str) else plugin_name._to_python_dict()
        )  # This is LSBareWord when Logstash is first parsed
        self.children: list[Attribute] = attributes

    def __repr__(self):
        return f"Plugin {self.plugin_name}: {self.children}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}Plugin({self.plugin_name})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_python_dict(self) -> dict[str, list[dict[str, Any]]]:
        d: list[dict[str, Any]] = []
        for attribute in self.children:
            d.append(attribute._to_python_dict())

        plugin_object: dict[str, list[dict[str, Any]]] = {self.plugin_name: d}
        return plugin_object

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return PluginSchema(
            source_text=self.get_source_text(),
            plugin_name=self.plugin_name,
            attributes=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Plugin":
        assert isinstance(schema, PluginSchema)
        attributes = [Attribute._from_pydantic(attr) for attr in schema.attributes]
        node = cls(schema.plugin_name, attributes)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent: int = 0, is_dm_branch: bool = False) -> str:
        ind = indent * " "
        out = f"{ind}{self.plugin_name} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2)

        out += f"{ind}}}\n"
        return out


class Boolean(ASTNode):
    schema_class = BooleanSchema

    def __init__(self, value: bool):
        super().__init__()
        self.value: bool = value

    def _to_python_dict(self) -> bool:
        # 简单节点:直接返回布尔值
        return self.value

    def _to_pydantic_model(self) -> BooleanSchema:
        return BooleanSchema(
            source_text=self.get_source_text(),
            value=self.value,
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Boolean":
        assert isinstance(schema, BooleanSchema)
        node = cls(schema.value)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent: int = 0) -> str:
        return str(self.value).lower()

    def to_source(self) -> str:
        return str(self.value).lower()

    def __repr__(self):
        return str(self._to_python_dict())

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Boolean({self.value})"


class SelectorNode(ASTNode):
    """
    Represents a Log-Stash field reference like [foo][bar][baz]
    We keep the raw selector string around for fidelity.
    """

    schema_class = SelectorNodeSchema

    def __init__(self, raw: str | ASTNode):
        super().__init__()
        self.raw: str | ASTNode = raw
        self.children: list[ASTNode] = [raw] if isinstance(raw, ASTNode) else []

    def __repr__(self):
        return f"SelectorNode( {str(self.raw)})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"SelectorNode({self.raw})"

    def _to_python_dict(self) -> str:
        # 简单节点:直接返回选择器字符串
        return str(self.raw)

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return SelectorNodeSchema(
            source_text=self.get_source_text(),
            raw=str(self.raw),
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "SelectorNode":
        assert isinstance(schema, SelectorNodeSchema)
        node = cls(schema.raw)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent: int = 0) -> str:
        return str(self.raw)

    def to_source(self) -> str:
        return str(self.raw)


class RegexExpression(ASTNode):
    schema_class = RegexExpressionSchema
    _parser_name = "regexp_expression"
    _parser_element = grammar.regexp_expression_with_source

    def __init__(self, left: ASTNode, operator: str, pattern: ASTNode, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)

        self.left: ASTNode = left
        self.operator: str = operator
        self.pattern: ASTNode = pattern

        self.children: list[ASTNode] = [left, pattern]

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def _to_python_dict(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "left": self.left._to_python_dict(),
            "operator": self.operator,
            "pattern": self.pattern._to_python_dict(),
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return RegexExpressionSchema(
            source_text=self.get_source_text(),
            left=self.left._to_pydantic_model(),  # type: ignore[arg-type]
            operator=self.operator,
            pattern=self.pattern._to_pydantic_model(),  # type: ignore[arg-type]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "RegexExpression":
        assert isinstance(schema, RegexExpressionSchema)
        left = _schema_to_node(schema.left)
        pattern = _schema_to_node(schema.pattern)
        node = cls(left, schema.operator, pattern)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent: int = 0) -> str:
        return f"{self.left.to_logstash()} {self.operator} {self.pattern.to_logstash()}"


class CompareExpression(ASTNode):
    schema_class = CompareExpressionSchema
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

    def _to_python_dict(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "left": self.left._to_python_dict(),
            "operator": self.operator,
            "right": self.right._to_python_dict(),
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return CompareExpressionSchema(
            source_text=self.get_source_text(),
            left=self.left._to_pydantic_model(),  # type: ignore[arg-type]
            operator=self.operator,
            right=self.right._to_pydantic_model(),  # type: ignore[arg-type]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "CompareExpression":
        assert isinstance(schema, CompareExpressionSchema)
        left = _schema_to_node(schema.left)
        right = _schema_to_node(schema.right)
        node = cls(left, schema.operator, right)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent=0):
        return f"{self.left.to_logstash()} {self.operator} {self.right.to_logstash()}"


class InExpression(ASTNode):
    schema_class = InExpressionSchema
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

    def _to_python_dict(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "in_expression",
            "value": self.value._to_python_dict(),
            "operator": self.operator,
            "collection": self.collection._to_python_dict(),
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return InExpressionSchema(
            source_text=self.get_source_text(),
            value=self.value._to_pydantic_model(),  # type: ignore[arg-type]
            operator=self.operator,
            collection=self.collection._to_pydantic_model(),  # type: ignore[arg-type]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "InExpression":
        assert isinstance(schema, InExpressionSchema)
        value = _schema_to_node(schema.value)
        collection = _schema_to_node(schema.collection)
        node = cls(value, schema.operator, collection)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent=0):
        return f"{self.value.to_logstash()} {self.operator} {self.collection.to_logstash()}"


class NotInExpression(ASTNode):
    schema_class = NotInExpressionSchema
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
        return f"{self.value} {self.operator} {self.collection._to_python_dict()} "

    def to_logstash(self, indent=0):
        return f"{self.value.to_logstash()} {self.operator} {self.collection.to_logstash()})"

    def _to_python_dict(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "not_in_expression",
            "value": self.value._to_python_dict(),
            "operator": self.operator,
            "collection": self.collection._to_python_dict(),
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return NotInExpressionSchema(
            source_text=self.get_source_text(),
            value=self.value._to_pydantic_model(),  # type: ignore[arg-type]
            operator=self.operator,
            collection=self.collection._to_pydantic_model(),  # type: ignore[arg-type]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "NotInExpression":
        assert isinstance(schema, NotInExpressionSchema)
        value = _schema_to_node(schema.value)
        collection = _schema_to_node(schema.collection)
        node = cls(value, schema.operator, collection)
        node._source_text_cache = schema.source_text
        return node


class NegativeExpression(ASTNode):
    schema_class = NegativeExpressionSchema
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

    def _to_python_dict(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "negative_expression",
            "operator": self.operator,
            "expression": self.expression._to_python_dict(),
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return NegativeExpressionSchema(
            source_text=self.get_source_text(),
            operator=self.operator,
            expression=self.expression._to_pydantic_model(),  # type: ignore[arg-type]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "NegativeExpression":
        assert isinstance(schema, NegativeExpressionSchema)
        expression = _schema_to_node(schema.expression)
        node = cls(schema.operator, expression)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent=0):
        return f"!({self.expression.to_logstash()})"


class RValue(ASTNode):
    def __init__(self, value: LSString | Number | SelectorNode | Array | Regexp):
        super().__init__()
        self.value = value
        self.children = [value] if isinstance(value, ASTNode) else []

    def __repr__(self):
        return f"{self.value}"

    def _to_python_dict(self):
        return self.value._to_python_dict()

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return self.value._to_pydantic_model()

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "RValue":
        # RValue 直接包装内部 value，从 schema 重建
        value = _schema_to_node(schema)
        return cls(value)  # type: ignore[arg-type]

    def to_logstash(self):
        return self.value.to_logstash()


class Expression(ASTNode):
    schema_class = ExpressionSchema
    _parser_name = "expression"
    _parser_element = grammar.expression_with_source

    def __init__(self, condition, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.condition = condition[0]
        self.children = [condition[0]] if isinstance(condition[0], ASTNode) else []

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def to_logstash(self, indent=0):
        return self.condition.to_logstash()

    def _to_python_dict(self):
        return self.condition._to_python_dict()

    def _to_pydantic_model(self) -> ASTNodeSchema:
        # Expression 是包装器，直接返回内部 condition 的 schema
        return self.condition._to_pydantic_model()

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Expression":
        # Expression 是包装器，从 schema 重建内部 condition
        # schema 本身就是 condition 的 schema
        condition = _schema_to_node(schema)
        node = cls([condition])
        node._source_text_cache = schema.source_text
        return node

    def __repr__(self):
        return f"{self.condition}".replace(
            "not not", ""
        )  # Replace double negatives with empty string. Not required but makes life easier


class BooleanExpression(ASTNode[ASTNode]):
    schema_class = BooleanExpressionSchema
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

    def _to_python_dict(self) -> dict[str, Any]:
        # Expression 节点:返回结构化对象
        return {
            "type": "boolean_expression",
            "left": self.left._to_python_dict(),
            "operator": self.operator,
            "right": self.right._to_python_dict(),
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return BooleanExpressionSchema(
            source_text=self.get_source_text(),
            left=self.left._to_pydantic_model(),  # type: ignore[arg-type]
            operator=self.operator,
            right=self.right._to_pydantic_model(),  # type: ignore[arg-type]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "BooleanExpression":
        assert isinstance(schema, BooleanExpressionSchema)
        left = _schema_to_node(schema.left)
        right = _schema_to_node(schema.right)
        node = cls(left, schema.operator, right)
        node._source_text_cache = schema.source_text
        return node

    def to_source(self):
        # 从子节点重构 source text
        left_source = self.left.to_source() if isinstance(self.left, ASTNode) else str(self.left)
        right_source = self.right.to_source() if isinstance(self.right, ASTNode) else str(self.right)
        return f"{left_source} {self.operator} {right_source}"


class IfCondition(ASTNode["Plugin | Branch"]):
    schema_class = IfConditionSchema
    _parser_name = "if_condition"
    _parser_element = grammar.if_condition_with_source

    def __init__(self, expr: Expression | BooleanExpression, body, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.expr = expr
        self.children = body.as_list() if isinstance(body, ParseResults) else body

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}IfCondition(expr={self.expr._to_python_dict()})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_python_dict(self) -> dict[str, Any]:
        # Branch condition 节点:返回结构化对象
        return {
            "type": "if",
            "expr": self.expr._to_python_dict(),
            "body": [child._to_python_dict() for child in self.children],
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return IfConditionSchema(
            source_text=self.get_source_text(),
            expr=self.expr._to_pydantic_model(),  # type: ignore[arg-type]
            body=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "IfCondition":
        assert isinstance(schema, IfConditionSchema)
        expr = _schema_to_node(schema.expr)
        body = [_schema_to_node(child) for child in schema.body]
        node = cls(expr, body)  # type: ignore[arg-type]
        node._source_text_cache = schema.source_text
        return node

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
    schema_class = ElseIfConditionSchema
    _parser_name = "else_if_condition"
    _parser_element = grammar.else_if_condition_with_source

    def __init__(self, expr: Expression | BooleanExpression, body, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.expr = expr
        self.children = body.as_list() if isinstance(body, ParseResults) else body
        self.combined_expr = None

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}ElseIfCondition(expr={self.expr._to_python_dict()})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_python_dict(self) -> dict[str, Any]:
        # Branch condition 节点:返回结构化对象
        return {
            "type": "else_if",
            "expr": self.expr._to_python_dict(),
            "body": [child._to_python_dict() for child in self.children],
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return ElseIfConditionSchema(
            source_text=self.get_source_text(),
            expr=self.expr._to_pydantic_model(),  # type: ignore[arg-type]
            body=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "ElseIfCondition":
        assert isinstance(schema, ElseIfConditionSchema)
        expr = _schema_to_node(schema.expr)
        body = [_schema_to_node(child) for child in schema.body]
        node = cls(expr, body)  # type: ignore[arg-type]
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent=0, is_dm_branch=False):
        if not is_dm_branch:
            return f"else if ({self.expr.to_logstash()} )"

        ind = indent * " "
        out = f"{ind} else if {self.expr.to_logstash()} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2, is_dm_branch=is_dm_branch)
        out += f"{ind}}}\n"
        return out


class ElseCondition(ASTNode["Plugin | Branch"]):
    schema_class = ElseConditionSchema
    _parser_name = "else_condition"
    _parser_element = grammar.else_condition_with_source

    def __init__(self, body, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.expr: Expression | BooleanExpression | None = None
        self.children = body.as_list() if isinstance(body, ParseResults) else body
        self.combined_expr = None

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}ElseCondition"
        header += f"(expr={self.expr._to_python_dict()})" if self.expr else ""
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_python_dict(self) -> dict[str, Any]:
        # Branch condition 节点:返回结构化对象
        # else 没有 expr
        return {
            "type": "else",
            "body": [child._to_python_dict() for child in self.children],
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return ElseConditionSchema(
            source_text=self.get_source_text(),
            body=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "ElseCondition":
        assert isinstance(schema, ElseConditionSchema)
        body = [_schema_to_node(child) for child in schema.body]
        node = cls(body)  # type: ignore[arg-type]
        node._source_text_cache = schema.source_text
        return node

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
    schema_class = BranchSchema
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

    def _to_python_dict(self) -> dict[str, Any]:
        # Branch 节点:返回结构化对象
        return {
            "type": "branch",
            "conditions": [child._to_python_dict() for child in self.children],
        }

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return BranchSchema(
            source_text=self.get_source_text(),
            children=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Branch":
        assert isinstance(schema, BranchSchema)
        # 从 schema.children 重建 if/elseif/else 条件
        if_rule = None
        else_if_rules = []
        else_rule = None

        for child in schema.children:
            if isinstance(child, IfConditionSchema):
                if_rule = IfCondition._from_pydantic(child)
            elif isinstance(child, ElseIfConditionSchema):
                else_if_rules.append(ElseIfCondition._from_pydantic(child))
            elif isinstance(child, ElseConditionSchema):
                else_rule = ElseCondition._from_pydantic(child)

        if if_rule is None:
            raise ValueError("Branch must have an if condition")

        node = cls(if_rule, else_if_rules if else_if_rules else None, else_rule)
        node._source_text_cache = schema.source_text
        return node

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
    schema_class = PluginSectionNodeSchema
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

    def _to_python_dict(self):
        # Return a dictionary with plugin_type as key and list of children as value
        children_data = []
        for child in self.children:
            children_data.append(child._to_python_dict())
        return {self.plugin_type: children_data}

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return PluginSectionNodeSchema(
            source_text=self.get_source_text(),
            plugin_type=self.plugin_type,
            children=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "PluginSectionNode":
        assert isinstance(schema, PluginSectionNodeSchema)
        # 从 schema.children 重建 Plugin 或 Branch
        children = [_schema_to_node(child) for child in schema.children]
        node = cls(schema.plugin_type, children)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent=0, is_dm_branch=False) -> str:
        ind = " " * indent
        out = f"{ind}{self.plugin_type} {{\n"
        children = "\n".join(c.to_logstash(indent + 2, is_dm_branch) for c in self.children)
        out += children
        out += f"{ind}}}"

        return out


class Config(ASTNode[PluginSectionNode]):
    schema_class = ConfigSchema
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

    def _to_python_dict(self):
        """Convert the Config AST to a Python dictionary representation.

        Returns a dictionary where keys are plugin types (input/filter/output)
        and values are lists of all sections of that type.
        """
        config_dict = {}

        for child in self.children:
            if isinstance(child, PluginSectionNode):
                child_data = child._to_python_dict()
                # child_data is like {"filter": [...]}
                for plugin_type, content in child_data.items():
                    if plugin_type not in config_dict:
                        config_dict[plugin_type] = []
                    config_dict[plugin_type].extend(content)

        return config_dict

    def _to_pydantic_model(self) -> ASTNodeSchema:
        return ConfigSchema(
            source_text=self.get_source_text(),
            children=[child._to_pydantic_model() for child in self.children],  # type: ignore[misc]
        )

    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> "Config":
        assert isinstance(schema, ConfigSchema)
        # 从 schema.children 重建 PluginSectionNode
        children = [PluginSectionNode._from_pydantic(child) for child in schema.children]
        node = cls(children)
        node._source_text_cache = schema.source_text
        return node

    def to_logstash(self, indent=0, is_dm_branch=False) -> str:
        """Convert the Config AST back to Logstash configuration format."""
        out = ""
        for child in self.children:
            if isinstance(child, PluginSectionNode):
                out += child.to_logstash(indent, is_dm_branch)
                out += "\n"
        return out.rstrip() + "\n"


# ============================================================================
# Schema to Node mapping
# ============================================================================

# Mapping from Schema class to AST Node class for efficient conversion
SCHEMA_TO_NODE: dict[type[ASTNodeSchema], type[ASTNode]] = {
    # Simple types
    LSStringSchema: LSString,
    LSBareWordSchema: LSBareWord,
    NumberSchema: Number,
    BooleanSchema: Boolean,
    RegexpSchema: Regexp,
    SelectorNodeSchema: SelectorNode,
    # Data structures
    ArraySchema: Array,
    HashEntryNodeSchema: HashEntryNode,
    HashSchema: Hash,
    AttributeSchema: Attribute,
    # Plugin
    PluginSchema: Plugin,
    # Expressions
    CompareExpressionSchema: CompareExpression,
    RegexExpressionSchema: RegexExpression,
    InExpressionSchema: InExpression,
    NotInExpressionSchema: NotInExpression,
    NegativeExpressionSchema: NegativeExpression,
    BooleanExpressionSchema: BooleanExpression,
    ExpressionSchema: Expression,
    # Conditions
    IfConditionSchema: IfCondition,
    ElseIfConditionSchema: ElseIfCondition,
    ElseConditionSchema: ElseCondition,
    BranchSchema: Branch,
    # Configuration
    PluginSectionNodeSchema: PluginSectionNode,
    ConfigSchema: Config,
}


# ============================================================================
# Helper function for Schema to Node conversion
# ============================================================================


def _schema_to_node(schema: ASTNodeSchema) -> ASTNode:
    """Convert a Pydantic Schema back to an AST Node.

    Args:
        schema: Pydantic Schema object

    Returns:
        Corresponding AST Node instance

    Raises:
        ValueError: If schema type is not recognized
    """
    schema_type = type(schema)
    node_class = SCHEMA_TO_NODE.get(schema_type)

    if node_class is None:
        raise ValueError(f"Unknown schema type: {schema_type}")

    return node_class._from_pydantic(schema)


# ============================================================================
# Builder functions for pyparsing
# ============================================================================


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
