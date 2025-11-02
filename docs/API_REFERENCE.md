# Logstash Parser API Reference

## 📋 Table of Contents

- [Core Functions](#core-functions)
- [AST Nodes](#ast-nodes)
- [Schema Types](#schema-types)
- [Conversion Methods](#conversion-methods)
- [Exceptions](#exceptions)
- [Type Mapping Table](#type-mapping-table)

---

## Core Functions

### `parse_logstash_config(config_text: str) -> Config`

Parse Logstash configuration text into AST.

**Parameters:**

- `config_text` (str): Logstash configuration text

**Returns:**

- `Config`: Configuration AST root node

**Raises:**

- `ParseError`: Raised when parsing fails

**Example:**

```python
from logstash_parser import parse_logstash_config

config_text = """
filter {
    grok {
        match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
}
"""

ast = parse_logstash_config(config_text)
```

---

## AST Nodes

### Base Class: `ASTNode`

Base class for all AST nodes.

#### Class Attributes

- `schema_class: type[S]` - Corresponding Schema class (must be overridden by subclasses)
- `_parser_name: str | None` - Parser name (optional)
- `_parser_element_for_get_source: ParserElement` - Parser element for `get_source_text()` (usually `xxx_with_source`)
- `_parser_element_for_parsing: ParserElement` - Parser element for `from_logstash()` (with parse_action set)

#### Instance Attributes

- `children: tuple[T, ...]` - Child node tuple
- `in_expression_context: bool` - Whether in expression context
- `uid: int` - Unique identifier
- `_s: str | None` - Original parse string (for lazy computation)
- `_loc: int | None` - Parse position (for lazy computation)
- `_source_text_cache: str | None` - Cached source text

#### Methods

##### `to_python(as_pydantic: bool = False) -> dict | BaseModel`

Convert to Python representation.

**Parameters:**

- `as_pydantic` (bool): Whether to return Pydantic Schema (default False)

**Returns:**

- `dict`: When `as_pydantic=False`
- `BaseModel`: When `as_pydantic=True`

**Example:**

```python
# Return dict
python_dict = ast.to_python()

# Return Pydantic Schema
schema = ast.to_python(as_pydantic=True)
```

##### `from_python(data: dict | BaseModel) -> ASTNode`

Create AST node from Python representation (class method).

**Parameters:**

- `data` (dict | BaseModel): Python dictionary or Pydantic Schema

**Returns:**

- `ASTNode`: AST node instance

**Implementation Details:**

- If `data` is dict, first convert to Schema using `schema_class.model_validate(data)`
- Then call `_from_pydantic(schema)` to create AST node

**Example:**

```python
# Create from dict
ast = Plugin.from_python({"plugin": {"plugin_name": "grok", "attributes": []}})

# Create from Schema
ast = Plugin.from_python(plugin_schema)
```

##### `from_schema(schema: ASTNodeSchema) -> ASTNode`

Create AST node from Pydantic Schema (class method).

**Parameters:**

- `schema` (ASTNodeSchema): Pydantic Schema object

**Returns:**

- `ASTNode`: Corresponding AST node instance

**Raises:**

- `ValueError`: If schema type is unknown

**Type Hints:**

- Provides 23 `@overload` declarations covering all Schema to Node mappings
- Type checker can automatically infer correct return type

**Example:**

```python
# Basic usage
schema = LSStringSchema(ls_string='"hello"')
node = ASTNode.from_schema(schema)
# Type checker infers: node: LSString

# Number type
number_schema = NumberSchema(number=42)
number_node = ASTNode.from_schema(number_schema)
# Type checker infers: number_node: Number

# Array type
array_schema = ArraySchema(array=[...])
array_node = ASTNode.from_schema(array_schema)
# Type checker infers: array_node: Array
```

**Supported Type Mappings:**

| Category    | Schema Types | Node Types | Count |
| ----------- | ------------ | ---------- | ----- |
| Simple      | LSStringSchema, LSBareWordSchema, NumberSchema, BooleanSchema, RegexpSchema, SelectorNodeSchema | LSString, LSBareWord, Number, Boolean, Regexp, SelectorNode | 6     |
| Structures  | ArraySchema, HashSchema, AttributeSchema | Array, Hash, Attribute | 3     |
| Plugin      | PluginSchema | Plugin     | 1     |
| Expressions | CompareExpressionSchema, RegexExpressionSchema, InExpressionSchema, NotInExpressionSchema, NegativeExpressionSchema, BooleanExpressionSchema | CompareExpression, RegexExpression, InExpression, NotInExpression, NegativeExpression, BooleanExpression | 6     |
| Conditions  | IfConditionSchema, ElseIfConditionSchema, ElseConditionSchema, BranchSchema | IfCondition, ElseIfCondition, ElseCondition, Branch | 4     |
| Config      | PluginSectionSchema, ConfigSchema | PluginSectionNode, Config | 2     |
| Fallback    | ASTNodeSchema | ASTNode   | 1     |

**Type Safety Best Practices:**

```python
# ✓ Good - use concrete type
schema: LSStringSchema = LSStringSchema(ls_string='"hello"')
node = ASTNode.from_schema(schema)  # Type: LSString

# ✗ Bad - using base class loses type inference
schema: ASTNodeSchema = LSStringSchema(ls_string='"hello"')
node = ASTNode.from_schema(schema)  # Type: ASTNode (fallback)

# ✓ Good - use type narrowing
schema: ASTNodeSchema = get_schema()
if isinstance(schema, LSStringSchema):
    node = ASTNode.from_schema(schema)  # Type: LSString
    print(node.lexeme)  # ✓ Type safe
```

##### `to_logstash(indent: int = 0) -> str`

Generate Logstash configuration text.

**Parameters:**

- `indent` (int): Indentation level (default 0)

**Returns:**

- `str`: Logstash configuration text

**Example:**

```python
config_text = ast.to_logstash()
```

##### `get_source_text() -> str | None`

Lazily get original source text, extract only when needed.

**Returns:**

- `str | None`: Original source text, or None if unavailable

**Implementation Details:**

- First check cache `_source_text_cache`
- If not cached and has `_s`, `_loc`, `_parser_name`, `_parser_element_for_get_source`, extract from original string
- Cache result after extraction for performance

##### `set_expression_context(value: bool)`

Set expression context flag and recursively set all child nodes.

**Parameters:**

- `value` (bool): Whether in expression context

##### `traverse()`

Recursively traverse all child nodes.

##### `to_repr(indent: int = 0) -> str`

Generate string representation of node (for debugging).

**Parameters:**

- `indent` (int): Indentation level

**Returns:**

- `str`: String representation of node

##### `_to_python_dict() -> Any`

Convert to Python dict (internal method).

**Returns:**

- `Any`: Python native data structure

**Implementation Details:**

- Default implementation calls `_to_pydantic_model()` then uses `model_dump(mode="json", exclude_none=True)`
- Subclasses can override for custom behavior

##### `_to_pydantic_model() -> S`

Convert to Pydantic Schema (internal method, must be implemented by subclasses).

**Returns:**

- `S`: Pydantic Schema object

##### `_from_pydantic(schema: S) -> ASTNode`

Create AST node from Pydantic Schema (class method, must be implemented by subclasses).

**Parameters:**

- `schema` (S): Pydantic Schema object

**Returns:**

- `ASTNode`: AST node instance

##### `_get_snake_case_key() -> str`

Get snake_case key name for node type (internal method).

**Returns:**

- `str`: snake_case key name

**Example:**

- `LSString` → `"ls_string"`
- `CompareExpression` → `"compare_expression"`

---

### Simple Types

#### `LSString`

String node.

**Attributes:**

- `lexeme: str` - Original string (with quotes)
- `value: str` - Parsed value (parsed using `ast.literal_eval`)

**Implementation Details:**

- Uses Python's `ast.literal_eval()` to parse string literals
- Automatically handles escape characters (e.g., `\n`, `\t`, `\f`, etc.)
- Special handling for `\r\n` and `\n`, replaced with `\\n` to avoid parse errors
- Supports single and double quotes

**Example:**

```python
s = LSString('"hello world"')
print(s.lexeme)  # '"hello world"'
print(s.value)   # 'hello world'

# Escape character handling
s2 = LSString('"line1\\nline2"')
print(s2.value)  # 'line1\nline2' (actual newline)
```

#### `LSBareWord`

Bare word node.

**Attributes:**

- `value: str` - Bare word value

#### `Number`

Number node.

**Attributes:**

- `value: int | float` - Number value

#### `Boolean`

Boolean node.

**Attributes:**

- `value: bool` - Boolean value

#### `Regexp`

Regular expression node.

**Attributes:**

- `lexeme: str` - Original regular expression
- `value: str` - Parsed value

#### `SelectorNode`

Field selector node.

**Attributes:**

- `raw: str` - Original selector string (e.g., `[foo][bar]`)

#### `MethodCall`

Method call node.

**Attributes:**

- `method_name: str` - Method name
- `children: tuple[LSString | Number | SelectorNode | Array | MethodCall | Regexp, ...]` - Method argument tuple

**Example:**

```python
# Simple method call
method = MethodCall("sprintf", (LSString('"%{field}"'),))

# Multi-argument method call
method = MethodCall("format", (
    LSString('"Hello"'),
    LSString('"World"')
))

# Nested method call
inner = MethodCall("lower", (LSString('"TEST"'),))
outer = MethodCall("upper", (inner,))
```

**Usage:**

- Can be used in rvalue position of conditional expressions
- Supports nested calls
- Supports multiple argument types

---

### Data Structures

#### `Array`

Array node.

**Attributes:**

- `children: tuple[Plugin | Boolean | LSBareWord | LSString | Number | Array | Hash, ...]` - Array element tuple

**Example:**

```python
arr = Array([LSString('"a"'), LSString('"b"')])
```

#### `Hash`

Hash table node.

**Attributes:**

- `children: tuple[HashEntryNode, ...]` - Hash entry tuple

#### `HashEntryNode`

Hash entry node.

**Attributes:**

- `key: LSString | LSBareWord | Number` - Key
- `value: ASTNode` - Value

#### `Attribute`

Attribute node.

**Attributes:**

- `name: LSString | LSBareWord` - Attribute name
- `value: ASTNode` - Attribute value

---

### Plugin

#### `Plugin`

Plugin node.

**Attributes:**

- `plugin_name: str` - Plugin name
- `children: tuple[Attribute, ...]` - Attribute tuple

**Example:**

```python
plugin = Plugin("grok", [
    Attribute(LSBareWord("match"), Hash(...))
])
```

---

### Expressions

#### `CompareExpression`

Comparison expression node.

**Attributes:**

- `left: ASTNode` - Left operand
- `operator: str` - Comparison operator (`==`, `!=`, `<`, `>`, `<=`, `>=`)
- `right: ASTNode` - Right operand

#### `RegexExpression`

Regular expression node.

**Attributes:**

- `left: ASTNode` - Left operand
- `operator: str` - Regex operator (`=~`, `!~`)
- `pattern: ASTNode` - Regex pattern

#### `InExpression`

In expression node.

**Attributes:**

- `value: ASTNode` - Value to check
- `operator: str` - Operator (`in`)
- `collection: ASTNode` - Collection

#### `NotInExpression`

Not In expression node.

**Attributes:**

- `value: ASTNode` - Value to check
- `operator: str` - Operator (`not in`, supports whitespace and comments)
- `collection: ASTNode` - Collection

**Implementation Details:**

- Uses `pp.Combine()` to merge "not", whitespace/comments, "in" into single token
- Supports formats like `not in`, `not  in`, `not\tin`, `not # comment\n in`
- Complies with grammar.treetop specification: `"not " cs "in"`

#### `NegativeExpression`

Negative expression node.

**Attributes:**

- `operator: str` - Negation operator (`!`)
- `expression: ASTNode` - Negated expression

#### `BooleanExpression`

Boolean expression node.

**Attributes:**

- `left: ASTNode` - Left operand
- `operator: str` - Boolean operator (`and`, `or`, `xor`, `nand`)
- `right: ASTNode` - Right operand
- `has_explicit_parens: bool` - Whether has explicit parentheses (to preserve user-added parentheses)

**Operator Precedence:**

- `and` / `nand`: Precedence 3 (highest)
- `xor`: Precedence 2
- `or`: Precedence 1 (lowest)

**Parsing Behavior:**

- `A or B and C` parses as `A or (B and C)` (automatically adds parentheses based on precedence)
- `(A or B) and C` preserves explicit parentheses, `has_explicit_parens=True`

**Example:**

```python
# Simple boolean expression
expr = BooleanExpression(
    SelectorNode("[a]"),
    "and",
    SelectorNode("[b]")
)

# Nested expression (precedence)
# A or B and C
expr = BooleanExpression(
    SelectorNode("[a]"),
    "or",
    BooleanExpression(
        SelectorNode("[b]"),
        "and",
        SelectorNode("[c]")
    )
)
```

---

### Conditional Branches

#### `IfCondition`

If condition node.

**Attributes:**

- `expr: Expression | BooleanExpression` - Condition expression
- `children: list[Plugin | Branch]` - Condition body

#### `ElseIfCondition`

Else If condition node.

**Attributes:**

- `expr: CompareExpression | RegexExpression | InExpression | NotInExpression | NegativeExpression | BooleanExpression | SelectorNode` - Condition expression
- `children: tuple[Plugin | Branch, ...]` - Condition body tuple

#### `ElseCondition`

Else condition node.

**Attributes:**

- `expr: CompareExpression | ... | None` - Condition expression (usually None unless merged else if)
- `children: tuple[Plugin | Branch, ...]` - Condition body tuple

#### `Branch`

Branch node.

**Attributes:**

- `children: tuple[IfCondition | ElseIfCondition | ElseCondition, ...]` - Condition tuple

---

### Configuration

#### `PluginSectionNode`

Plugin section node.

**Attributes:**

- `plugin_type: str` - Section type (`input`, `filter`, `output`)
- `children: tuple[Plugin | Branch, ...]` - Plugin or branch tuple

#### `Config`

Configuration root node.

---

## Schema Types

### Base Class: `ASTNodeSchema`

Base class for all Schemas.

**Fields:**

- `node_type: str` - Node type
- `source_text: str | None` - Original source text (not serialized)

**Configuration:**

```python
model_config = {"extra": "forbid"}  # Forbid extra fields
```

---

### Simple Type Schemas

#### `LSStringSchema`

```python
class LSStringSchema(BaseModel):
    ls_string: str  # Original string (with quotes)
    model_config = {"extra": "forbid"}
```

#### `LSBareWordSchema`

```python
class LSBareWordSchema(BaseModel):
    ls_bare_word: str  # Bare word value
    model_config = {"extra": "forbid"}
```

#### `NumberSchema`

```python
class NumberSchema(BaseModel):
    number: int | float  # Number value
    model_config = {"extra": "forbid"}
```

#### `BooleanSchema`

```python
class BooleanSchema(BaseModel):
    boolean: bool  # Boolean value
    model_config = {"extra": "forbid"}
```

#### `RegexpSchema`

```python
class RegexpSchema(BaseModel):
    regexp: str  # Original regex (with slashes)
    model_config = {"extra": "forbid"}
```

#### `SelectorNodeSchema`

```python
class SelectorNodeSchema(BaseModel):
    selector_node: str  # Original selector string (e.g., [foo][bar])
    model_config = {"extra": "forbid"}
```

#### `MethodCallData` / `MethodCallSchema`

```python
class MethodCallData(BaseModel):
    method_name: str  # Method name
    arguments: list[RValueSchema] = []  # Method argument list
    model_config = {"extra": "forbid"}

class MethodCallSchema(BaseModel):
    method_call: MethodCallData
    model_config = {"extra": "forbid"}
```

**Note**: MethodCall uses nested structure, outer layer is `method_call` field, inner layer is `MethodCallData`.

---

### Data Structure Schemas

#### `ArraySchema`

```python
class ArraySchema(BaseModel):
    array: list[ValueSchema]  # Array elements
    model_config = {"extra": "forbid"}
```

#### `HashSchema`

```python
class HashSchema(BaseModel):
    hash: dict[str, ValueSchema]  # Hash key-value pairs
    model_config = {"extra": "forbid"}
```

**Note**: Hash uses dict representation, keys are strings, values are ValueSchema.

#### `AttributeSchema`

```python
class AttributeSchema(RootModel[dict[str, ValueSchema]]):
    """Attribute uses RootModel to serialize directly as dict"""
    root: dict[str, ValueSchema]
```

**Note**: Attribute uses RootModel, serializes directly as `{"attribute_name": value}` format.

---

### Plugin Schema

#### `PluginData`

```python
class PluginData(BaseModel):
    plugin_name: str
    attributes: list[AttributeSchema] = []
    model_config = {"extra": "forbid"}
```

#### `PluginSchema`

```python
class PluginSchema(BaseModel):
    plugin: PluginData
    model_config = {"extra": "forbid"}
```

**Note**: Plugin uses nested structure, outer layer is `plugin` field, inner layer is `PluginData`.

---

### Expression Schemas

#### `CompareExpressionData` / `CompareExpressionSchema`

```python
class CompareExpressionData(BaseModel):
    left: ValueSchema
    operator: str  # ==, !=, <, >, <=, >=
    right: ValueSchema
    model_config = {"extra": "forbid"}

class CompareExpressionSchema(BaseModel):
    compare_expression: CompareExpressionData
    model_config = {"extra": "forbid"}
```

#### `RegexExpressionData` / `RegexExpressionSchema`

```python
class RegexExpressionData(BaseModel):
    left: ValueSchema
    operator: str  # =~, !~
    pattern: ValueSchema
    model_config = {"extra": "forbid"}

class RegexExpressionSchema(BaseModel):
    regex_expression: RegexExpressionData
    model_config = {"extra": "forbid"}
```

#### `InExpressionData` / `InExpressionSchema`

```python
class InExpressionData(BaseModel):
    value: ValueSchema
    operator: str = "in"
    collection: ValueSchema
    model_config = {"extra": "forbid"}

class InExpressionSchema(BaseModel):
    in_expression: InExpressionData
    model_config = {"extra": "forbid"}
```

#### `NotInExpressionData` / `NotInExpressionSchema`

```python
class NotInExpressionData(BaseModel):
    value: ValueSchema
    operator: str = "not in"
    collection: ValueSchema
    model_config = {"extra": "forbid"}

class NotInExpressionSchema(BaseModel):
    not_in_expression: NotInExpressionData
    model_config = {"extra": "forbid"}
```

#### `NegativeExpressionData` / `NegativeExpressionSchema`

```python
class NegativeExpressionData(BaseModel):
    operator: str  # !
    expression: ValueSchema
    model_config = {"extra": "forbid"}

class NegativeExpressionSchema(BaseModel):
    negative_expression: NegativeExpressionData
    model_config = {"extra": "forbid"}
```

#### `BooleanExpressionData` / `BooleanExpressionSchema`

```python
class BooleanExpressionData(BaseModel):
    left: ValueSchema
    operator: str  # and, or, xor, nand
    right: ValueSchema
    model_config = {"extra": "forbid"}

class BooleanExpressionSchema(BaseModel):
    boolean_expression: BooleanExpressionData
    model_config = {"extra": "forbid"}
```

**Note**: All expressions use nested structure, outer layer is snake_case field name, inner layer is corresponding Data class.

---

### Conditional Branch Schemas

#### `IfConditionData` / `IfConditionSchema`

```python
class IfConditionData(BaseModel):
    expr: ExpressionSchema  # Note: This is a type alias, actually uses concrete expression Schema
    body: list[BranchOrPluginSchema] = []
    model_config = {"extra": "forbid"}

class IfConditionSchema(BaseModel):
    if_condition: IfConditionData
    model_config = {"extra": "forbid"}
```

#### `ElseIfConditionData` / `ElseIfConditionSchema`

```python
class ElseIfConditionData(BaseModel):
    expr: ExpressionSchema  # Note: This is a type alias, actually uses concrete expression Schema
    body: list[BranchOrPluginSchema] = []
    model_config = {"extra": "forbid"}

class ElseIfConditionSchema(BaseModel):
    else_if_condition: ElseIfConditionData
    model_config = {"extra": "forbid"}
```

#### `ElseConditionSchema`

```python
class ElseConditionSchema(BaseModel):
    else_condition: list[BranchOrPluginSchema] = []
    model_config = {"extra": "forbid"}
```

#### `BranchSchema`

```python
class BranchSchema(BaseModel):
    branch: list[ConditionSchema] = []
    model_config = {"extra": "forbid"}
```

**Note**: Branch contains list of If/ElseIf/Else conditions.

---

### Configuration Schemas

#### `PluginSectionSchema`

```python
class PluginSectionSchema(BaseModel):
    plugin_section: dict[Literal["input", "filter", "output"], list[BranchOrPluginSchema]]
    model_config = {"extra": "forbid"}
```

**Description**: PluginSection uses dict representation, where key is plugin_type (input/filter/output), value is children list.

**Example**:

```python
schema = PluginSectionSchema(
    plugin_section={
        "filter": [
            PluginSchema(...)
        ]
    }
)
```

#### `ConfigSchema`

```python
class ConfigSchema(BaseModel):
    config: list[PluginSectionSchema] = []
    model_config = {"extra": "forbid"}
```

---

### Union Types

#### `NameSchema`

Attribute name type (LSString or LSBareWord):

```python
NameSchema: TypeAlias = Annotated[
    LSStringSchema | LSBareWordSchema,
    Field(discriminator=None)
]
```

#### `RValueSchema`

Right value type (for values in expressions):

```python
RValueSchema: TypeAlias = Annotated[
    LSStringSchema | NumberSchema | SelectorNodeSchema | ArraySchema | MethodCallSchema | RegexpSchema,
    Field(discriminator=None),
]
```

**Description**: Corresponds to Logstash grammar rule `rule rvalue = string / number / selector / array / method_call / regexp`

**Note**: `RValueSchema` is a type alias, not a class. It automatically expands to its member types in unions.

#### `ValueSchema`

All possible value types:

```python
ValueSchema = Annotated[
    LSStringSchema
    | LSBareWordSchema
    | NumberSchema
    | BooleanSchema
    | RegexpSchema
    | SelectorNodeSchema
    | HashSchema
    | ArraySchema
    | PluginSchema
    | CompareExpressionSchema
    | RegexExpressionSchema
    | InExpressionSchema
    | NotInExpressionSchema
    | NegativeExpressionSchema
    | BooleanExpressionSchema,
    Field(discriminator=None)
]
```

**Note**: Uses `discriminator=None`, Pydantic automatically identifies type by field name.

#### `ExpressionSchema`

All possible expression types (type alias, not a class):

```python
ExpressionSchema: TypeAlias = Annotated[
    CompareExpressionSchema
    | RegexExpressionSchema
    | InExpressionSchema
    | NotInExpressionSchema
    | NegativeExpressionSchema
    | BooleanExpressionSchema
    | RValueSchema,  # ← Uses RValueSchema, automatically expands
    Field(discriminator=None)
]
```

**Description**: Corresponds to Logstash grammar rule `rule expression = ... / rvalue`

**Notes**:

- `ExpressionSchema` is a type alias, not a class. Should directly use concrete expression Schema types when using.
- `RValueSchema` automatically expands in union to `LSStringSchema | NumberSchema | SelectorNodeSchema | ArraySchema | RegexpSchema`

#### `ConditionSchema`

Condition type (If/ElseIf/Else):

```python
ConditionSchema = Annotated[
    IfConditionSchema | ElseIfConditionSchema | ElseConditionSchema,
    Field(discriminator=None)
]
```

#### `BranchOrPluginSchema`

Branch or plugin:

```python
BranchOrPluginSchema = Annotated[
    BranchSchema | PluginSchema,
    Field(discriminator=None)
]
```

---

## Conversion Methods

### Schema Methods

All Schema classes provide the following methods:

#### `model_dump() -> dict`

Convert to dictionary.

```python
data = schema.model_dump()
```

#### `model_dump_json(indent: int = None) -> str`

Serialize to JSON.

```python
json_str = schema.model_dump_json(indent=2)
```

#### `model_validate(data: dict) -> Schema`

Validate and create Schema from dictionary.

```python
schema = ConfigSchema.model_validate(data)
```

#### `model_validate_json(json_str: str) -> Schema`

Validate and create Schema from JSON.

```python
schema = ConfigSchema.model_validate_json(json_str)
```

---

## Exceptions

### `ParseError`

Parse error exception.

**Inherits:** `Exception`

**Usage:**

```python
try:
    ast = parse_logstash_config(config_text)
except ParseError as e:
    print(f"Parse failed: {e}")
```

---

## Type Mapping Table

| AST Node           | Schema Class             | Schema Field Name     |
| ------------------ | ------------------------ | --------------------- |
| LSString           | LSStringSchema           | `ls_string`           |
| LSBareWord         | LSBareWordSchema         | `ls_bare_word`        |
| Number             | NumberSchema             | `number`              |
| Boolean            | BooleanSchema            | `boolean`             |
| Regexp             | RegexpSchema             | `regexp`              |
| SelectorNode       | SelectorNodeSchema       | `selector_node`       |
| MethodCall         | MethodCallSchema         | `method_call`         |
| Array              | ArraySchema              | `array`               |
| Hash               | HashSchema               | `hash`                |
| Attribute          | AttributeSchema          | (RootModel)           |
| Plugin             | PluginSchema             | `plugin`              |
| CompareExpression  | CompareExpressionSchema  | `compare_expression`  |
| RegexExpression    | RegexExpressionSchema    | `regex_expression`    |
| InExpression       | InExpressionSchema       | `in_expression`       |
| NotInExpression    | NotInExpressionSchema    | `not_in_expression`   |
| NegativeExpression | NegativeExpressionSchema | `negative_expression` |
| BooleanExpression  | BooleanExpressionSchema  | `boolean_expression`  |
| IfCondition        | IfConditionSchema        | `if_condition`        |
| ElseIfCondition    | ElseIfConditionSchema    | `else_if_condition`   |
| ElseCondition      | ElseConditionSchema      | `else_condition`      |
| Branch             | BranchSchema             | `branch`              |
| PluginSectionNode  | PluginSectionSchema      | `plugin_section`      |
| Config             | ConfigSchema             | `config`              |

**Note**: Schema uses snake_case field names as type identifiers, not `node_type` field.

---

## Related Documentation

- [Architecture Design](./ARCHITECTURE.md)
- [User Guide](./USER_GUIDE.md)
- [Testing Guide](./TESTING.md)
- [Changelog](./CHANGELOG.md)

**中文文档 (Chinese)**:

- [API 参考 (中文)](./zh_cn/API_REFERENCE.md)
