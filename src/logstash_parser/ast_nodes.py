import ast
from typing import Any, Generic, Literal, TypeVar, cast, overload

from pydantic import BaseModel
from pyparsing import ParserElement, ParseResults
from typing_extensions import Self

from logstash_parser import grammar
from logstash_parser.grammar import (
    array,
    attribute,
    bare_word,
    boolean,
    branch,
    compare_expression,
    config,
    else_if_rule,
    else_rule,
    hashmap,
    if_rule,
    in_expression,
    negative_expression,
    not_in_expression,
    number,
    plugin,
    plugin_section,
    regexp,
    regexp_expression,
    selector,
    string,
)
from logstash_parser.schemas import (
    ArraySchema,
    ASTNodeSchema,
    AttributeSchema,
    BooleanExpressionData,
    BooleanExpressionSchema,
    BooleanSchema,
    BranchSchema,
    CompareExpressionData,
    CompareExpressionSchema,
    ConfigSchema,
    ElseConditionSchema,
    ElseIfConditionData,
    ElseIfConditionSchema,
    HashSchema,
    IfConditionData,
    IfConditionSchema,
    InExpressionData,
    InExpressionSchema,
    LSBareWordSchema,
    LSStringSchema,
    NegativeExpressionData,
    NegativeExpressionSchema,
    NotInExpressionData,
    NotInExpressionSchema,
    NumberSchema,
    PluginData,
    PluginSchema,
    PluginSectionSchema,
    RegexExpressionData,
    RegexExpressionSchema,
    RegexpSchema,
    SelectorNodeSchema,
)

T = TypeVar("T", bound="ASTNode")
S = TypeVar("S", bound="BaseModel")  # 放宽为 BaseModel,因为 AttributeSchema 使用 RootModel


class ASTNode(Generic[T, S]):
    _counter = 0

    # 类变量：定义解析器名称和元素（子类必须覆盖）
    _parser_name: str | None = None
    _parser_element_for_get_source: ParserElement  # 用于 get_source_text()，通常是 xxx_with_source
    _parser_element_for_parsing: ParserElement  # 用于 from_logstash()，已设置 parse_action

    # Schema 类引用（子类必须覆盖，这里只是占位）
    schema_class: type[S]

    def __init__(
        self,
        s: str | None = None,
        loc: int | None = None,
    ) -> None:
        self.children: tuple[T, ...] = tuple[T, ...]()
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
        if self._s is not None and self._loc is not None and self._parser_name and self._parser_element_for_get_source:
            # 直接提取，不需要全局缓存函数
            result = self._parser_element_for_get_source.searchString(self._s[self._loc :])
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
        Otherwise, falls back to to_logstash() for reconstruction.
        """
        # If we have source text, return it
        source_text = self.get_source_text()
        if source_text is not None:
            return source_text

        # Fallback: use to_logstash() for reconstruction
        try:
            return self.to_logstash()
        except (NotImplementedError, TypeError) as e:
            raise NotImplementedError(
                f"{self.__class__.__name__}.to_source() must be implemented or source text must be set"
            ) from e

    @overload
    def to_python(self, as_pydantic: Literal[False] = False) -> Any: ...

    @overload
    def to_python(self, as_pydantic: Literal[True]) -> S: ...

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
        """Convert to Python dict via Pydantic model.

        Default implementation uses _to_pydantic_model() and dumps to dict.
        Subclasses can override for custom behavior.
        """
        return self._to_pydantic_model().model_dump(mode="json", exclude_none=True)

    def _to_pydantic_model(self) -> S:
        """Convert to Pydantic Schema (subclasses must implement)."""
        raise NotImplementedError(f"{self.__class__.__name__}._to_pydantic_model() must be implemented")

    def _get_snake_case_key(self) -> str:
        """Get the snake_case key for this node type."""
        # Convert class name to snake_case
        # e.g., LSString -> ls_string, CompareExpression -> compare_expression
        name = self.__class__.__name__
        import re

        # Insert underscore before uppercase letters (except at start)
        snake = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
        return snake.lower()

    @classmethod
    def from_python(cls, data: dict[str, Any] | S) -> Self:
        """Create AST node from Python representation.

        Args:
            data: Either a dict or a Pydantic Schema object

        Returns:
            AST node instance
        """
        # If it's a dict, convert to Schema first
        if isinstance(data, dict):
            schema = cls.schema_class.model_validate(data)
        else:
            schema = data

        # Now schema is a Schema object, use _from_pydantic
        return cls._from_pydantic(schema)

    @classmethod
    def _from_pydantic(cls, schema: S) -> Self:
        """Create AST node from Pydantic Schema (subclasses must implement)."""
        raise NotImplementedError(f"{cls.__name__}._from_pydantic() must be implemented")

    # Simple types
    @overload
    @classmethod
    def from_schema(cls, schema: LSStringSchema) -> "LSString": ...

    @overload
    @classmethod
    def from_schema(cls, schema: LSBareWordSchema) -> "LSBareWord": ...

    @overload
    @classmethod
    def from_schema(cls, schema: NumberSchema) -> "Number": ...

    @overload
    @classmethod
    def from_schema(cls, schema: BooleanSchema) -> "Boolean": ...

    @overload
    @classmethod
    def from_schema(cls, schema: RegexpSchema) -> "Regexp": ...

    @overload
    @classmethod
    def from_schema(cls, schema: SelectorNodeSchema) -> "SelectorNode": ...

    # Data structures
    @overload
    @classmethod
    def from_schema(cls, schema: ArraySchema) -> "Array": ...

    @overload
    @classmethod
    def from_schema(cls, schema: HashSchema) -> "Hash": ...

    @overload
    @classmethod
    def from_schema(cls, schema: AttributeSchema) -> "Attribute": ...

    # Plugin
    @overload
    @classmethod
    def from_schema(cls, schema: PluginSchema) -> "Plugin": ...

    # Expressions
    @overload
    @classmethod
    def from_schema(cls, schema: CompareExpressionSchema) -> "CompareExpression": ...

    @overload
    @classmethod
    def from_schema(cls, schema: RegexExpressionSchema) -> "RegexExpression": ...

    @overload
    @classmethod
    def from_schema(cls, schema: InExpressionSchema) -> "InExpression": ...

    @overload
    @classmethod
    def from_schema(cls, schema: NotInExpressionSchema) -> "NotInExpression": ...

    @overload
    @classmethod
    def from_schema(cls, schema: NegativeExpressionSchema) -> "NegativeExpression": ...

    @overload
    @classmethod
    def from_schema(cls, schema: BooleanExpressionSchema) -> "BooleanExpression": ...

    # Conditions
    @overload
    @classmethod
    def from_schema(cls, schema: IfConditionSchema) -> "IfCondition": ...

    @overload
    @classmethod
    def from_schema(cls, schema: ElseIfConditionSchema) -> "ElseIfCondition": ...

    @overload
    @classmethod
    def from_schema(cls, schema: ElseConditionSchema) -> "ElseCondition": ...

    @overload
    @classmethod
    def from_schema(cls, schema: BranchSchema) -> "Branch": ...

    # Configuration
    @overload
    @classmethod
    def from_schema(cls, schema: PluginSectionSchema) -> "PluginSectionNode": ...

    @overload
    @classmethod
    def from_schema(cls, schema: ConfigSchema) -> "Config": ...

    # # Fallback for unknown schema types
    # @overload
    # @classmethod
    # def from_schema(cls, schema: ASTNodeSchema) -> "ASTNode": ...

    @classmethod
    def from_schema(cls, schema: BaseModel) -> "ASTNode":
        """Convert a Pydantic Schema back to an AST Node.

        Args:
            schema: Pydantic Schema object (BaseModel or RootModel)

        Returns:
            Corresponding AST Node instance

        Raises:
            ValueError: If schema type is not recognized

        Example:
            >>> schema = LSStringSchema(ls_string='"hello"')
            >>> node = ASTNode.from_schema(schema)
            >>> isinstance(node, LSString)
            True
        """
        schema_type = type(schema)
        if schema_type not in SCHEMA_TO_NODE:
            raise ValueError(f"Unknown schema type: {schema_type}")
        node_class = SCHEMA_TO_NODE[schema_type]

        return node_class._from_pydantic(schema)

    @classmethod
    def from_logstash(cls, text: str, *, parse_all: bool = True) -> Self:
        """Parse Logstash configuration text to create this node type.

        Args:
            text: Logstash configuration text fragment
            parse_all: If True, require the entire text to match (default: True)

        Returns:
            AST node instance

        Raises:
            ParseException: If parsing fails

        Example:
            >>> plugin = Plugin.from_logstash('grok { match => { "message" => "%{PATTERN}" } }')
            >>> array = Array.from_logstash('[1, 2, 3]')
        """
        result = cls._parser_element_for_parsing.parse_string(text, parse_all=parse_all)
        if not result or len(result) == 0:
            raise ValueError(f"Failed to parse {cls.__name__} from text: {text!r}")

        return cast(Self, result[0])

    def to_logstash(self, **kwargs):
        """Convert the AST node to a Logstash representation (to be defined later)."""
        raise NotImplementedError

    def __repr__(self):
        return self.to_repr()

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"{self.__class__.__name__}"


class LSString(ASTNode[ASTNode, LSStringSchema]):
    schema_class = LSStringSchema
    _parser_name = "string"
    _parser_element_for_parsing = string
    _parser_element_for_get_source = grammar.string_with_source

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

    def _to_pydantic_model(self) -> LSStringSchema:
        return LSStringSchema(ls_string=self.lexeme)

    @classmethod
    def _from_pydantic(cls, schema) -> "LSString":
        assert isinstance(schema, cls.schema_class)
        node = cls(schema.ls_string)
        return node

    def to_source(self):
        return self.lexeme

    def to_logstash(self, indent=0, **kwargs):
        # 保留原始引号类型(单引号或双引号)
        return self.lexeme

    def __repr__(self):
        return f"LSString({self.lexeme!r})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"LSString({self.lexeme!r})"


class LSBareWord(ASTNode[ASTNode, LSBareWordSchema]):
    """
    Represents a logstash key word (e.g., mutate).
    """

    schema_class = LSBareWordSchema
    _parser_name = "bare_word"
    _parser_element_for_parsing = bare_word
    _parser_element_for_get_source = grammar.bare_word_with_source

    def __init__(self, value: str):
        super().__init__()
        self.lexeme = value
        self.value = value

    def __repr__(self):
        return f"LSBareWord({self.value})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"LSBareWord({self.value})"

    def _to_pydantic_model(self):
        return LSBareWordSchema(ls_bare_word=self.value)

    @classmethod
    def _from_pydantic(cls, schema) -> "LSBareWord":
        assert isinstance(schema, LSBareWordSchema)
        node = cls(schema.ls_bare_word)
        return node

    def to_logstash(self, **kwargs):
        return self.value

    def to_source(self):
        return self.lexeme


class Regexp(ASTNode[ASTNode, RegexpSchema]):
    schema_class = RegexpSchema
    _parser_name = "regexp"
    _parser_element_for_parsing = regexp
    _parser_element_for_get_source = grammar.regexp_with_source

    def __init__(self, lexeme: str):
        super().__init__()

        # NOTE: When rendering / printing, lexeme will have quotations around it.
        self.lexeme = lexeme  # in python, this is like: '"message"'

        try:
            self.value = rf"{lexeme}"

        except Exception as e:
            raise ValueError(f"Invalid string literal {lexeme!r}: {e}") from None

    def _to_pydantic_model(self):
        return RegexpSchema(regexp=self.lexeme)

    @classmethod
    def _from_pydantic(cls, schema) -> "Regexp":
        assert isinstance(schema, RegexpSchema)
        node = cls(schema.regexp)
        return node

    def to_source(self):
        return self.lexeme

    def to_logstash(self, indent=0, **kwargs):
        # lexeme already includes the slashes (e.g., "/error/")
        return self.lexeme

    def __repr__(self):
        return f"LSString({self.lexeme!r})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Regexp({self.lexeme!r})"


class Number(ASTNode[ASTNode, NumberSchema]):
    schema_class = NumberSchema
    _parser_name = "number"
    _parser_element_for_parsing = number
    _parser_element_for_get_source = grammar.number_with_source

    def __init__(self, value: int | float):
        super().__init__()
        self.lexeme: int | float = value
        self.value: int | float = value

    def __repr__(self):
        return str(self.value)

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Number({self.value})"

    def _to_pydantic_model(self):
        return NumberSchema(number=self.value)

    @classmethod
    def _from_pydantic(cls, schema) -> "Number":
        assert isinstance(schema, NumberSchema)
        node = cls(schema.number)
        return node

    def to_logstash(self, indent: int = 0, **kwargs) -> int | float:
        return self.value

    def to_source(self) -> int | float:
        return self.lexeme


class Array(ASTNode["Plugin | Boolean | LSBareWord | LSString | Number | Array | Hash", ArraySchema]):
    schema_class = ArraySchema
    _parser_name = "array"
    _parser_element_for_get_source = grammar.array_with_source
    _parser_element_for_parsing = array

    def __init__(
        self,
        values: tuple["Plugin | Boolean | LSBareWord | LSString | Number | Array | Hash", ...],
        s: str | None = None,
        loc: int | None = None,
    ):
        super().__init__(s=s, loc=loc)
        self.children = values  # Generally the elements are either Hash or LSString

    def _to_pydantic_model(self):
        return ArraySchema(
            array=[child._to_pydantic_model() for child in self.children],
        )

    @classmethod
    def _from_pydantic(cls, schema):
        assert isinstance(schema, ArraySchema)
        children = tuple(ASTNode.from_schema(child) for child in schema.array)
        node = cls(children)
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

    def to_logstash(self, indent: int = 0, **kwargs) -> str:
        ind = " " * indent
        # Reconstruct from children for logstash output
        inner_parts: list[str] = []
        for c in self.children:
            if isinstance(c, Hash):
                # Hash needs special formatting - strip indent
                inner_parts.append(c.to_logstash(**kwargs).strip())
            else:
                # For other types, use to_logstash
                child_output = c.to_logstash(**kwargs)
                inner_parts.append(str(child_output) if not isinstance(child_output, str) else child_output)
        return f"{ind}[" + ", ".join(inner_parts) + "]"


class HashEntryNode(ASTNode[ASTNode, ASTNodeSchema]):
    """Corresponds to hash_entry in PEG

    Note: HashEntryNode is not directly serialized to Schema.
    It's only used internally by Hash, which serializes to a dict.
    """

    _parser_name = "hash_entry"
    _parser_element_for_get_source = grammar.hash_entry_with_source
    _parser_element_for_parsing = grammar.hash_entry

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

    def to_logstash(self, indent: int = 0, **kwargs) -> str:
        ind = indent * " "
        # Use to_logstash for key
        key_output = self.key.to_logstash(**kwargs)
        out = f"{ind}{key_output if isinstance(key_output, str) else str(key_output)} => "
        if isinstance(self.value, Hash):
            # Hash should have opening brace on same line
            hash_str = self.value.to_logstash(indent, **kwargs)
            # Remove leading indent from first line
            hash_lines = hash_str.split("\n")
            out += hash_lines[0].lstrip()
            if len(hash_lines) > 1:
                out += "\n" + "\n".join(hash_lines[1:])
            out += "\n"
        elif isinstance(self.value, Plugin):
            # Plugin should have opening brace on same line
            plugin_str = self.value.to_logstash(indent + 2, **kwargs)
            # Remove leading indent from first line
            plugin_lines = plugin_str.split("\n")
            out += plugin_lines[0].lstrip()
            if len(plugin_lines) > 1:
                out += "\n" + "\n".join(plugin_lines[1:])
            out += "\n"
        else:
            # Use to_logstash for value
            value_output = self.value.to_logstash(**kwargs)
            out += value_output if isinstance(value_output, str) else str(value_output)
            out += "\n"
        return out


class Hash(ASTNode[HashEntryNode, HashSchema]):
    """
    Corresponds to hashmap in PEG.
    Pretty much the same as hash_entries, except that hashmap wraps hash_entries in braces
    """

    schema_class = HashSchema
    _parser_name = "hashmap"
    _parser_element_for_get_source = grammar.hashmap_with_source
    _parser_element_for_parsing = hashmap

    def __init__(self, entries: tuple[HashEntryNode, ...], s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.children: tuple[HashEntryNode, ...] = entries

    def __repr__(self):
        return self.to_repr()

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Hash {{\n{children}\n{ind}}}"

    def _to_pydantic_model(self):
        # Convert list of HashEntryNode to dict
        hash_dict = {}
        for entry in self.children:
            # Serialize the key to string
            key_schema = entry.key._to_pydantic_model()
            # Extract the actual key value from the schema based on type
            if isinstance(key_schema, LSStringSchema):
                key_str = key_schema.ls_string
            elif isinstance(key_schema, LSBareWordSchema):
                key_str = key_schema.ls_bare_word
            elif isinstance(key_schema, NumberSchema):
                key_str = str(key_schema.number)
            else:
                # Fallback: use model_dump_json
                key_str = key_schema.model_dump_json()

            hash_dict[key_str] = entry.value._to_pydantic_model()

        return HashSchema(hash=hash_dict)

    @classmethod
    def _from_pydantic(cls, schema) -> Self:
        assert isinstance(schema, HashSchema)
        # Convert dict back to list of HashEntryNode
        children: list[HashEntryNode] = []
        for key_str, value_schema in schema.hash.items():
            # Reconstruct key node from string using grammar parser
            # Use grammar.hash_key to parse the key string
            # It returns AST nodes directly (LSString, LSBareWord, or Number)
            parsed = grammar.hash_key.parse_string(key_str, parse_all=True)
            key_node = cast(LSString | LSBareWord | Number, parsed[0])

            value_node = ASTNode.from_schema(value_schema)
            children.append(HashEntryNode(key_node, value_node))

        node = cls(tuple(children))
        return node

    def to_logstash(self, indent: int = 0, **kwargs) -> str:
        ind = " " * indent
        out = f"{ind}{{\n"
        for entry in self.children:
            out += entry.to_logstash(indent + 2, **kwargs)
        out += f"{ind}}}"
        return out


class Attribute(ASTNode[ASTNode, AttributeSchema]):
    schema_class = AttributeSchema
    _parser_name = "attribute"
    _parser_element_for_get_source = grammar.attribute_with_source
    _parser_element_for_parsing = attribute

    def __init__(self, name, value, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.name: LSString | LSBareWord = name  # Either LSString or LSBareWord
        self.value: ASTNode = value

    def __repr__(self):
        return f"Attribute {repr(self.name)} => {self.value}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        return f"{ind}Attribute(\n{self.name.to_repr(indent + 2)} => {self.value.to_repr(indent + 2)}\n{ind})"

    def _to_pydantic_model(self):
        # Convert Attribute to dict with single key-value pair
        name_schema = self.name._to_pydantic_model()
        # Extract the actual name value from the schema based on type
        if isinstance(name_schema, LSStringSchema):
            name_str = name_schema.ls_string
        elif isinstance(name_schema, LSBareWordSchema):
            name_str = name_schema.ls_bare_word
        else:
            # Fallback: use model_dump_json
            name_str = name_schema.model_dump_json()

        return AttributeSchema({name_str: self.value._to_pydantic_model()})

    @classmethod
    def _from_pydantic(cls, schema) -> "Attribute":
        assert isinstance(schema, AttributeSchema)
        # Attribute dict should have exactly one key-value pair
        if len(schema.root) != 1:
            raise ValueError(f"Attribute must have exactly one name-value pair, got {len(schema.root)}")

        name_str, value_schema = next(iter(schema.root.items()))

        # Reconstruct name node from string using grammar parser
        # Use grammar.name to parse the name string
        # It returns AST nodes directly (LSString or LSBareWord)
        parsed = grammar.name.parse_string(name_str, parse_all=True)
        name_node = cast(LSString | LSBareWord, parsed[0])

        value_node = ASTNode.from_schema(value_schema)
        node = cls(name_node, value_node)
        return node

    def to_logstash(self, indent: int = 0, **kwargs) -> str:
        ind = indent * " "
        name_logstash = self.name.to_logstash(**kwargs) if isinstance(self.name, ASTNode) else self.name
        out = f"{ind}{name_logstash if isinstance(name_logstash, str) else str(name_logstash)} => "

        if isinstance(self.value, Hash):
            # Hash should have opening brace on same line
            hash_str = self.value.to_logstash(indent, **kwargs)
            # Remove leading indent from first line
            hash_lines = hash_str.split("\n")
            out += hash_lines[0].lstrip()
            if len(hash_lines) > 1:
                out += "\n" + "\n".join(hash_lines[1:])
            out += "\n"
        elif isinstance(self.value, Plugin):
            # Plugin should have opening brace on same line
            plugin_str = self.value.to_logstash(indent + 2, **kwargs)
            # Remove leading indent from first line
            plugin_lines = plugin_str.split("\n")
            out += plugin_lines[0].lstrip()
            if len(plugin_lines) > 1:
                out += "\n" + "\n".join(plugin_lines[1:])
            out += "\n"
        else:
            value_output = self.value.to_logstash(**kwargs)
            out += value_output if isinstance(value_output, str) else str(value_output)
            out += "\n"
        return out


class Plugin(ASTNode[Attribute, PluginSchema]):
    schema_class = PluginSchema
    _parser_name = "plugin"
    _parser_element_for_get_source = grammar.plugin_with_source
    _parser_element_for_parsing = plugin

    def __init__(
        self,
        plugin_name: str | LSBareWord,
        attributes: tuple[Attribute, ...],
        s: str | None = None,
        loc: int | None = None,
    ):
        super().__init__(s=s, loc=loc)
        self.plugin_name: str = (
            plugin_name if isinstance(plugin_name, str) else plugin_name.value
        )  # This is LSBareWord when Logstash is first parsed
        self.children = attributes

    def __repr__(self):
        return f"Plugin {self.plugin_name}: {self.children}"

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}Plugin({self.plugin_name})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_pydantic_model(self):
        return PluginSchema(
            plugin=PluginData(
                plugin_name=self.plugin_name,
                attributes=[child._to_pydantic_model() for child in self.children],
            )
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "Plugin":
        assert isinstance(schema, PluginSchema)
        attributes = tuple(Attribute._from_pydantic(attr) for attr in schema.plugin.attributes)
        node = cls(schema.plugin.plugin_name, attributes)
        return node

    def to_logstash(self, indent: int = 0, is_dm_branch: bool = False, **kwargs) -> str:
        ind = indent * " "
        out = f"{ind}{self.plugin_name} {{\n"
        for child in self.children:
            out += child.to_logstash(indent + 2, **kwargs)

        out += f"{ind}}}"
        return out


class Boolean(ASTNode[ASTNode, BooleanSchema]):
    schema_class = BooleanSchema
    _parser_name = "boolean"
    _parser_element_for_parsing = boolean
    _parser_element_for_get_source = grammar.boolean_with_source

    def __init__(self, value: bool):
        super().__init__()
        self.value: bool = value

    def _to_pydantic_model(self):
        return BooleanSchema(boolean=self.value)

    @classmethod
    def _from_pydantic(cls, schema) -> "Boolean":
        assert isinstance(schema, BooleanSchema)
        node = cls(schema.boolean)
        return node

    def to_logstash(self, indent: int = 0, **kwargs) -> str:
        return str(self.value).lower()

    def to_source(self) -> str:
        return str(self.value).lower()

    def __repr__(self):
        return str(self._to_python_dict())

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"Boolean({self.value})"


class SelectorNode(ASTNode[ASTNode, SelectorNodeSchema]):
    """
    Represents a Log-Stash field reference like [foo][bar][baz]
    We keep the raw selector string around for fidelity.
    """

    schema_class = SelectorNodeSchema
    _parser_name = "selector"
    _parser_element_for_parsing = selector
    _parser_element_for_get_source = grammar.selector_with_source

    def __init__(self, raw: str | ASTNode):
        super().__init__()
        self.raw: str | ASTNode = raw

    def __repr__(self):
        return f"SelectorNode( {str(self.raw)})"

    def to_repr(self, indent: int = 0) -> str:
        return " " * indent + f"SelectorNode({self.raw})"

    def _to_pydantic_model(self):
        return SelectorNodeSchema(selector_node=str(self.raw))

    @classmethod
    def _from_pydantic(cls, schema) -> "SelectorNode":
        assert isinstance(schema, SelectorNodeSchema)
        node = cls(schema.selector_node)
        return node

    def to_logstash(self, indent: int = 0, **kwargs) -> str:
        return str(self.raw)

    def to_source(self) -> str:
        return str(self.raw)


class RegexExpression(ASTNode[ASTNode, RegexExpressionSchema]):
    schema_class = RegexExpressionSchema
    _parser_name = "regexp_expression"
    _parser_element_for_get_source = grammar.regexp_expression_with_source
    _parser_element_for_parsing = regexp_expression

    def __init__(self, left: ASTNode, operator: str, pattern: ASTNode, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)

        self.left: ASTNode = left
        self.operator: str = operator
        self.pattern: ASTNode = pattern

        self.children = (left, pattern)

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def _to_pydantic_model(self):
        return RegexExpressionSchema(
            regex_expression=RegexExpressionData(
                left=self.left._to_pydantic_model(),
                operator=self.operator,
                pattern=self.pattern._to_pydantic_model(),
            )
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "RegexExpression":
        assert isinstance(schema, RegexExpressionSchema)
        left = ASTNode.from_schema(schema.regex_expression.left)
        pattern = ASTNode.from_schema(schema.regex_expression.pattern)
        node = cls(left, schema.regex_expression.operator, pattern)
        return node

    def to_logstash(self, indent: int = 0, **kwargs) -> str:
        return f"{self.left.to_logstash(**kwargs)} {self.operator} {self.pattern.to_logstash(**kwargs)}"


class CompareExpression(ASTNode[ASTNode, CompareExpressionSchema]):
    schema_class = CompareExpressionSchema
    _parser_name = "compare_expression"
    _parser_element_for_get_source = grammar.compare_expression_with_source
    _parser_element_for_parsing = compare_expression

    def __init__(self, left: ASTNode, operator: str, right: ASTNode, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.left: ASTNode = left
        self.operator: str = operator
        self.right: ASTNode = right
        self.children = (left, right)

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def __repr__(self):
        return f"{self.left} {self.operator} {self.right}"

    def _to_pydantic_model(self):
        return CompareExpressionSchema(
            compare_expression=CompareExpressionData(
                left=self.left._to_pydantic_model(),
                operator=self.operator,
                right=self.right._to_pydantic_model(),
            )
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "CompareExpression":
        assert isinstance(schema, CompareExpressionSchema)
        left = ASTNode.from_schema(schema.compare_expression.left)
        right = ASTNode.from_schema(schema.compare_expression.right)
        node = cls(left, schema.compare_expression.operator, right)
        return node

    def to_logstash(self, indent=0, **kwargs):
        return f"{self.left.to_logstash(**kwargs)} {self.operator} {self.right.to_logstash(**kwargs)}"


class InExpression(ASTNode[ASTNode, InExpressionSchema]):
    schema_class = InExpressionSchema
    _parser_name = "in_expression"
    _parser_element_for_get_source = grammar.in_expression_with_source
    _parser_element_for_parsing = in_expression

    def __init__(self, value, operator, collection, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.value = value
        self.operator = operator
        self.collection = collection
        self.children = (value, collection)

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def __repr__(self):
        return f"InExpression({self.value} {self.operator} {self.collection})"

    def _to_pydantic_model(self):
        return InExpressionSchema(
            in_expression=InExpressionData(
                value=self.value._to_pydantic_model(),
                operator=self.operator,
                collection=self.collection._to_pydantic_model(),
            )
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "InExpression":
        assert isinstance(schema, InExpressionSchema)
        value = ASTNode.from_schema(schema.in_expression.value)
        collection = ASTNode.from_schema(schema.in_expression.collection)
        node = cls(value, schema.in_expression.operator, collection)
        return node

    def to_logstash(self, indent=0, **kwargs):
        return f"{self.value.to_logstash(**kwargs)} {self.operator} {self.collection.to_logstash(**kwargs)}"


class NotInExpression(ASTNode[ASTNode, NotInExpressionSchema]):
    schema_class = NotInExpressionSchema
    _parser_name = "not_in_expression"
    _parser_element_for_get_source = grammar.not_in_expression_with_source
    _parser_element_for_parsing = not_in_expression

    def __init__(self, value, operator, collection, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.value = value
        self.operator = operator
        self.collection = collection
        self.children = (value, collection)

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def __repr__(self):
        return f"{self.value} {self.operator} {self.collection._to_python_dict()} "

    def to_logstash(self, indent=0, **kwargs):
        return f"{self.value.to_logstash(**kwargs)} {self.operator} {self.collection.to_logstash(**kwargs)}"

    def _to_pydantic_model(self):
        return NotInExpressionSchema(
            not_in_expression=NotInExpressionData(
                value=self.value._to_pydantic_model(),
                operator=self.operator,
                collection=self.collection._to_pydantic_model(),
            )
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "NotInExpression":
        assert isinstance(schema, NotInExpressionSchema)
        value = ASTNode.from_schema(schema.not_in_expression.value)
        collection = ASTNode.from_schema(schema.not_in_expression.collection)
        node = cls(value, schema.not_in_expression.operator, collection)
        return node


class NegativeExpression(ASTNode[ASTNode, NegativeExpressionSchema]):
    schema_class = NegativeExpressionSchema
    _parser_name = "negative_expression"
    _parser_element_for_get_source = grammar.negative_expression_with_source
    _parser_element_for_parsing = negative_expression

    def __init__(self, operator, expression, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.operator = operator
        self.expression = expression
        self.children = (self.expression,) if isinstance(self.expression, ASTNode) else ()
        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def __repr__(self):
        return f"not {self.expression}".replace(
            "not not", ""
        )  # Replace double negatives with empty string. Not required but makes life easier

    def to_repr(self, indent=0):
        return f"not {self.expression}".replace("not not", "")

    def _to_pydantic_model(self):
        return NegativeExpressionSchema(
            negative_expression=NegativeExpressionData(
                operator=self.operator,
                expression=self.expression._to_pydantic_model(),
            )
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "NegativeExpression":
        assert isinstance(schema, NegativeExpressionSchema)
        expression = ASTNode.from_schema(schema.negative_expression.expression)
        node = cls(schema.negative_expression.operator, expression)
        return node

    def to_logstash(self, indent=0, **kwargs):
        # According to grammar: "!" cs "(" cs condition cs ")" / "!" cs selector
        # Only add parentheses if expression is a condition (BooleanExpression or complex expression)
        # For simple selectors, no parentheses needed
        expr_str = self.expression.to_logstash(**kwargs)

        # If expression is a BooleanExpression or contains operators, add parentheses
        if isinstance(
            self.expression, (BooleanExpression, CompareExpression, RegexExpression, InExpression, NotInExpression)
        ):
            return f"!({expr_str})"

        # For selectors and simple values, no parentheses
        return f"!{expr_str}"


class RValue(
    ASTNode[
        LSString | Number | SelectorNode | Array | Regexp,
        LSStringSchema | NumberSchema | SelectorNodeSchema | ArraySchema | RegexpSchema,
    ]
):
    _parser_name = "rvalue"
    _parser_element_for_get_source = grammar.rvalue_with_source
    _parser_element_for_parsing = grammar.rvalue

    def __init__(self, value: LSString | Number | SelectorNode | Array | Regexp):
        super().__init__()
        self.value = value
        self.children = (value,) if isinstance(value, ASTNode) else ()

    def __repr__(self):
        return f"{self.value}"

    def _to_python_dict(self):
        return self.value._to_python_dict()

    def _to_pydantic_model(self):
        return self.value._to_pydantic_model()

    @classmethod
    def _from_pydantic(cls, schema):
        # RValue 直接包装内部 value，从 schema 重建
        value = ASTNode.from_schema(schema)
        return cls(value)

    def to_logstash(self, indent=0, **kwargs):
        return self.value.to_logstash(indent=indent)


PRECEDENCE = {
    "or": 1,
    "xor": 2,
    "and": 3,
    "nand": 3,
}


class BooleanExpression(ASTNode[ASTNode, BooleanExpressionSchema]):
    schema_class = BooleanExpressionSchema
    _parser_name = "condition"
    _parser_element_for_get_source = grammar.condition_with_source
    _parser_element_for_parsing = grammar.condition

    def __init__(self, left, operator, right, has_explicit_parens=False):
        super().__init__()

        self.left = left
        self.operator = operator
        self.right = right
        self.has_explicit_parens = has_explicit_parens  # Track if user added parentheses
        self.children = (left, right)

        self.set_expression_context(True)  # Mark sub-nodes as expression context

    def to_logstash(self, indent=0, **kwargs):
        # Operator precedence: and/nand > xor > or
        # We need to add parentheses when a lower-precedence operator is used as operand
        # of a higher-precedence operator

        left_str = self._format_operand(self.left, is_left=True)
        right_str = self._format_operand(self.right, is_left=False)

        result = f"{left_str} {self.operator} {right_str}"

        # If user explicitly added parentheses, preserve them by default
        if self.has_explicit_parens:
            return f"({result})"

        return result

    def _format_operand(self, operand, is_left: bool) -> str:
        """Format an operand, adding parentheses if needed based on operator precedence."""
        operand_str = operand.to_logstash() if isinstance(operand, ASTNode) else str(operand)

        # If operand is not a BooleanExpression, no parentheses needed
        if not isinstance(operand, BooleanExpression):
            return operand_str

        # If operand has explicit parentheses, they're already added in its to_logstash()
        if operand.has_explicit_parens:
            return operand_str

        # Operator precedence levels (higher number = higher precedence)

        parent_prec = PRECEDENCE.get(self.operator, 0)
        child_prec = PRECEDENCE.get(operand.operator, 0)

        # Add parentheses if child has lower precedence than parent
        if child_prec < parent_prec:
            return f"({operand_str})"

        return operand_str

    def __repr__(self):
        return f"({self.left} {self.operator} {self.right})"

    def _to_pydantic_model(self):
        return BooleanExpressionSchema(
            boolean_expression=BooleanExpressionData(
                left=self.left._to_pydantic_model(),
                operator=self.operator,
                right=self.right._to_pydantic_model(),
            )
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "BooleanExpression":
        assert isinstance(schema, BooleanExpressionSchema)
        left = ASTNode.from_schema(schema.boolean_expression.left)
        right = ASTNode.from_schema(schema.boolean_expression.right)
        node = cls(left, schema.boolean_expression.operator, right)
        return node

    def to_source(self):
        # 从子节点重构 source text
        left_source = self.left.to_source() if isinstance(self.left, ASTNode) else str(self.left)
        right_source = self.right.to_source() if isinstance(self.right, ASTNode) else str(self.right)
        return f"{left_source} {self.operator} {right_source}"


class IfCondition(ASTNode["Plugin | Branch", IfConditionSchema]):
    schema_class = IfConditionSchema
    _parser_name = "if_condition"
    _parser_element_for_get_source = grammar.if_condition_with_source
    _parser_element_for_parsing = if_rule

    def __init__(
        self,
        expr: CompareExpression
        | RegexExpression
        | InExpression
        | NotInExpression
        | NegativeExpression
        | BooleanExpression
        | LSString
        | Number
        | SelectorNode
        | Array
        | Regexp,
        body: tuple["Plugin | Branch", ...],
        s: str | None = None,
        loc: int | None = None,
    ):
        super().__init__(s=s, loc=loc)
        self.expr = expr
        self.children = body

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}IfCondition(expr={self.expr._to_python_dict()})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_pydantic_model(self):
        return IfConditionSchema(
            if_condition=IfConditionData(
                expr=self.expr._to_pydantic_model(),
                body=[child._to_pydantic_model() for child in self.children],
            )
        )

    @classmethod
    def _from_pydantic(cls, schema):
        assert isinstance(schema, IfConditionSchema)
        expr = ASTNode.from_schema(schema.if_condition.expr)
        body = tuple(ASTNode.from_schema(child) for child in schema.if_condition.body)
        node = cls(expr, body)
        return node

    def to_logstash(self, indent=0, is_dm_branch=False, **kwargs):
        if not is_dm_branch:
            return f"if {self.expr.to_logstash(indent=0, **kwargs)}"
        ind = indent * " "
        out = f"{ind}if {self.expr.to_logstash(indent=0, **kwargs)} {{\n"
        for child in self.children:
            child_out = child.to_logstash(indent + 2, is_dm_branch=is_dm_branch, **kwargs)
            out += child_out
            # Only add newline if child doesn't already end with one
            if not child_out.endswith("\n"):
                out += "\n"
        out += f"{ind}}}\n"
        return out


class ElseIfCondition(ASTNode["Plugin | Branch", ElseIfConditionSchema]):
    schema_class = ElseIfConditionSchema
    _parser_name = "else_if_condition"
    _parser_element_for_get_source = grammar.else_if_condition_with_source
    _parser_element_for_parsing = else_if_rule

    def __init__(
        self,
        expr: CompareExpression
        | RegexExpression
        | InExpression
        | NotInExpression
        | NegativeExpression
        | BooleanExpression
        | LSString
        | Number
        | SelectorNode
        | Array
        | Regexp,
        body: tuple["Plugin | Branch", ...],
        s: str | None = None,
        loc: int | None = None,
    ):
        super().__init__(s=s, loc=loc)
        self.expr = expr
        self.children = body
        self.combined_expr = None

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}ElseIfCondition(expr={self.expr._to_python_dict()})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_pydantic_model(self):
        return ElseIfConditionSchema(
            else_if_condition=ElseIfConditionData(
                expr=self.expr._to_pydantic_model(),
                body=[child._to_pydantic_model() for child in self.children],
            )
        )

    @classmethod
    def _from_pydantic(cls, schema):
        assert isinstance(schema, ElseIfConditionSchema)
        expr = ASTNode.from_schema(schema.else_if_condition.expr)
        body = tuple(ASTNode.from_schema(child) for child in schema.else_if_condition.body)
        node = cls(expr, body)
        return node

    def to_logstash(self, indent=0, is_dm_branch=False, **kwargs):
        if not is_dm_branch:
            return f"else if ({self.expr.to_logstash(**kwargs)} )"

        ind = indent * " "
        out = f" else if {self.expr.to_logstash(**kwargs)} {{\n"
        for child in self.children:
            child_out = child.to_logstash(indent + 2, is_dm_branch=is_dm_branch, **kwargs)
            out += child_out
            # Only add newline if child doesn't already end with one
            if not child_out.endswith("\n"):
                out += "\n"
        out += f"{ind}}}\n"
        return out


class ElseCondition(ASTNode["Plugin | Branch", ElseConditionSchema]):
    schema_class = ElseConditionSchema
    _parser_name = "else_condition"
    _parser_element_for_get_source = grammar.else_condition_with_source
    _parser_element_for_parsing = else_rule

    def __init__(self, body: tuple["Plugin | Branch", ...], s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.expr: (
            CompareExpression
            | RegexExpression
            | InExpression
            | NotInExpression
            | NegativeExpression
            | BooleanExpression
            | LSString
            | Number
            | SelectorNode
            | Array
            | Regexp
            | None
        ) = None
        self.children = body
        self.combined_expr = None

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}ElseCondition"
        header += f"(expr={self.expr._to_python_dict()})" if self.expr else ""
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_pydantic_model(self):
        return ElseConditionSchema(
            else_condition=[child._to_pydantic_model() for child in self.children],
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "ElseCondition":
        assert isinstance(schema, ElseConditionSchema)
        body = tuple(ASTNode.from_schema(child) for child in schema.else_condition)
        node = cls(body)
        return node

    def to_logstash(self, indent=0, is_dm_branch=False, **kwargs):
        if not is_dm_branch:
            if self.combined_expr and self.expr:
                out = f"else if {self.expr.to_logstash(**kwargs)} "
            else:
                out = "else"
            return out

        ind = " " * indent
        if self.combined_expr and self.expr:
            out = f" else if {self.expr.to_logstash(**kwargs)} {{\n"
        else:
            out = " else {\n"
        for child in self.children:
            child_out = child.to_logstash(indent + 2, is_dm_branch=is_dm_branch, **kwargs)
            out += child_out
            # Only add newline if child doesn't already end with one
            if not child_out.endswith("\n"):
                out += "\n"
        out += f"{ind}}}\n"
        return out


class Branch(ASTNode[IfCondition | ElseIfCondition | ElseCondition, BranchSchema]):
    schema_class = BranchSchema
    _parser_name = "branch"
    _parser_element_for_get_source = grammar.branch_with_source
    _parser_element_for_parsing = branch

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
        self.children = tuple(children)

    def _to_pydantic_model(self):
        return BranchSchema(
            branch=[child._to_pydantic_model() for child in self.children],
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "Branch":
        assert isinstance(schema, BranchSchema)
        # 从 schema.branch 重建 if/elseif/else 条件
        if_rule = None
        else_if_rules = []
        else_rule = None

        for child in schema.branch:
            if isinstance(child, IfConditionSchema):
                if_rule = IfCondition._from_pydantic(child)
            elif isinstance(child, ElseIfConditionSchema):
                else_if_rules.append(ElseIfCondition._from_pydantic(child))
            elif isinstance(child, ElseConditionSchema):
                else_rule = ElseCondition._from_pydantic(child)

        if if_rule is None:
            raise ValueError("Branch must have an if condition")

        node = cls(if_rule, else_if_rules if else_if_rules else None, else_rule)
        return node

    def to_logstash(self, indent=0, is_dm_branch=False, **kwargs) -> str:
        out = ""
        for i, child in enumerate(self.children):
            child_out = child.to_logstash(indent, is_dm_branch=True, **kwargs)
            if i > 0:
                # For else if and else, they should be on the same line as the closing brace
                # Remove the trailing newline from previous output
                out = out.rstrip("\n")
                # child_out starts with " else if" or " else", keep the leading space
            out += child_out
        return out

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{ind}Branch {{\n{children}\n{ind}}}"


class PluginSectionNode(ASTNode[Plugin | Branch, PluginSectionSchema]):
    schema_class = PluginSectionSchema
    _parser_name = "plugin_section"
    _parser_element_for_get_source = grammar.plugin_section_with_source
    _parser_element_for_parsing = plugin_section

    def __init__(self, plugin_type, children, s: str | None = None, loc: int | None = None):
        super().__init__(s=s, loc=loc)
        self.plugin_type = plugin_type
        self.children = children

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        header = f"{ind}PluginSection(type={self.plugin_type})"
        children = "\n".join(c.to_repr(indent + 2) for c in self.children)
        return f"{header} {{\n{children}\n{ind}}}"

    def _to_pydantic_model(self):
        return PluginSectionSchema(
            plugin_section={self.plugin_type: [child._to_pydantic_model() for child in self.children]}
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "PluginSectionNode":
        assert isinstance(schema, PluginSectionSchema)
        # 从 schema.plugin_section dict 重建 Plugin 或 Branch
        # dict 应该只有一个 key-value 对
        plugin_type, children_schemas = next(iter(schema.plugin_section.items()))
        children = [ASTNode.from_schema(child) for child in children_schemas]
        node = cls(plugin_type, children)
        return node

    def to_logstash(self, indent=0, is_dm_branch=False, **kwargs) -> str:
        ind = " " * indent
        out = f"{ind}{self.plugin_type} {{\n"
        for i, child in enumerate(self.children):
            child_out = child.to_logstash(indent + 2, is_dm_branch, **kwargs)
            out += child_out
            # Ensure child ends with newline
            if not child_out.endswith("\n"):
                out += "\n"
            # Add blank line between children (except after the last one)
            if i < len(self.children) - 1:
                out += "\n"
        out += f"{ind}}}"

        return out


class Config(ASTNode[PluginSectionNode, ConfigSchema]):
    schema_class = ConfigSchema
    _parser_name = "config"
    _parser_element_for_get_source = grammar.config_with_source
    _parser_element_for_parsing = config

    def __init__(
        self,
        toks: tuple[PluginSectionNode, ...],
        s: str | None = None,
        loc: int | None = None,
    ):
        super().__init__(s=s, loc=loc)
        self.children = toks

    def to_repr(self, indent: int = 0) -> str:
        ind = " " * indent
        children = "\n".join(child.to_repr(indent + 2) for child in self.children)
        return f"{ind}Config {{\n{children}\n{ind}}}"

    def _to_pydantic_model(self):
        return ConfigSchema(
            config=[child._to_pydantic_model() for child in self.children],
        )

    @classmethod
    def _from_pydantic(cls, schema) -> "Config":
        assert isinstance(schema, ConfigSchema)
        # 从 schema.config 重建 PluginSectionNode
        children = tuple(PluginSectionNode._from_pydantic(child) for child in schema.config)
        node = cls(children)
        return node

    def to_logstash(self, indent=0, is_dm_branch=False, **kwargs) -> str:
        """Convert the Config AST back to Logstash configuration format."""
        out = ""
        for i, child in enumerate(self.children):
            if isinstance(child, PluginSectionNode):
                out += child.to_logstash(indent, is_dm_branch, **kwargs)
                out += "\n"
                # Add blank line between sections (except after the last one)
                if i < len(self.children) - 1:
                    out += "\n"
        return out.rstrip() + "\n"


# ============================================================================
# Schema to Node mapping
# ============================================================================

# Mapping from Schema class to AST Node class for efficient conversion
# Note: Key type is BaseModel (not ASTNodeSchema) to accommodate AttributeSchema (RootModel)
SCHEMA_TO_NODE: dict[type[BaseModel], type[ASTNode]] = {
    # Simple types
    LSStringSchema: LSString,
    LSBareWordSchema: LSBareWord,
    NumberSchema: Number,
    BooleanSchema: Boolean,
    RegexpSchema: Regexp,
    SelectorNodeSchema: SelectorNode,
    # Data structures
    ArraySchema: Array,
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
    # Conditions
    IfConditionSchema: IfCondition,
    ElseIfConditionSchema: ElseIfCondition,
    ElseConditionSchema: ElseCondition,
    BranchSchema: Branch,
    # Configuration
    PluginSectionSchema: PluginSectionNode,
    ConfigSchema: Config,
}


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
    value = toks.as_list()[0]
    return Number(value)


def build_array_node(s, loc, toks: ParseResults) -> Array:
    values = list(toks)[0]
    return Array(values, s=s, loc=loc)


def build_hash_entry_node(s, loc, toks: ParseResults) -> HashEntryNode:
    toks_list = list(toks)[0]
    return HashEntryNode(toks_list[0], toks_list[1][0], s=s, loc=loc)


def build_hash_node(s, loc, toks: ParseResults) -> Hash:
    return Hash(tuple(list(toks)[0].as_list()), s=s, loc=loc)


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


def build_expression_unwrap(toks: ParseResults):
    """Unwrap expression Group to get the actual expression node.
    Since expression is defined as a Group in grammar, we need to extract
    the first element which is the actual expression node.

    IMPORTANT: isinstance(toks[0], ParseResults) indicates explicit parentheses!
    When user writes (expr), it creates an extra ParseResults wrapper.
    """
    # NOTE: This function is currently not used because we handle unwrapping
    # in build_condition_node to preserve parentheses information.
    return toks[0][0] if isinstance(toks[0], ParseResults) else toks[0]


# Boolean operators set (defined once)
BOOL_OPS = {"and", "or", "xor", "nand"}


def unwrap_and_process(operand_item):
    """Unwrap operand if wrapped (has parentheses) and process it.

    Returns: (processed_node, had_parens)
    """
    # Check if wrapped (has explicit parentheses)
    if isinstance(operand_item, (list, ParseResults)) and len(operand_item) == 1:
        # Unwrap and process
        node = process_infix_result(operand_item[0])
        # Mark if it's a BooleanExpression
        if isinstance(node, BooleanExpression):
            node.has_explicit_parens = True
        return node

    # Not wrapped, process directly
    return process_infix_result(operand_item)


def process_infix_result(item):
    """Recursively process infixNotation result."""
    # Not a list - return as is
    if not isinstance(item, (list, ParseResults)):
        return item

    item_len = len(item)

    # Single element list - unwrap it
    if item_len == 1:
        return process_infix_result(item[0])

    # Binary expression: [left, op, right]
    if item_len == 3 and isinstance(item[1], str) and item[1] in BOOL_OPS:
        left = unwrap_and_process(item[0])
        operator = item[1]
        right = unwrap_and_process(item[2])
        return BooleanExpression(left, operator, right)

    # Flat list (old format): [expr1, 'and', expr2, 'or', expr3, ...]
    # Check if it contains boolean operators
    if any(isinstance(x, str) and x in BOOL_OPS for x in item):
        condition_expr = process_infix_result(item[0])
        for i in range(1, item_len, 2):
            boolean_operator = item[i]
            next_expression = process_infix_result(item[i + 1])
            condition_expr = BooleanExpression(condition_expr, boolean_operator, next_expression)
        return condition_expr

    # Fallback: return first item or the item itself
    return item[0] if item_len == 1 else item


def build_condition_node(toks):
    """Build condition node from infixNotation output.

    infixNotation returns nested lists:
    - Single expression: ['expr']
    - Binary expression: [['expr1', 'op', 'expr2']]
    - Nested: [[['expr1', 'op1', 'expr2'], 'op2', 'expr3']]

    Parentheses detection:
    - Since we disabled build_expression_unwrap, expressions with parentheses
      will be wrapped: (expr) becomes [expr] instead of just expr
    - We detect this by checking if len(item) == 1
    """

    return process_infix_result(toks[0])


def build_if_condition_node(s, loc, toks):
    return IfCondition(toks[0][1][0], tuple(toks[0][1][1][0].as_list()), s=s, loc=loc)


def build_condition_else_if_node(s, loc, toks):
    return ElseIfCondition(toks[0][1][0], tuple(toks[0][1][1][0].as_list()), s=s, loc=loc)


def build_condition_else_node(s, loc, toks):
    return ElseCondition(tuple(toks[0][1].as_list()), s=s, loc=loc)


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


def build_config_node(s, loc, toks: ParseResults):
    """Build config node with original source text.

    Args:
        s: The original parse string
        loc: Current location in the string (unused but required by pyparsing)
        toks: Parse results
    """
    # Config node represents the entire document
    config = Config(tuple(toks.as_list()), s=s, loc=loc)
    return config
