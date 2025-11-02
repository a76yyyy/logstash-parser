# Logstash Parser Architecture Design

## 📋 Overview

Logstash Parser is a Python library for parsing, transforming, and generating Logstash configurations. It provides complete bidirectional conversion capabilities, supporting mutual conversion between Logstash configuration text, AST (Abstract Syntax Tree), Python dictionaries, and Pydantic Schemas.

**Grammar Compliance**: This implementation fully complies with the official Logstash grammar.treetop specification and has been verified through comprehensive test cases.

---

## 🏗️ System Architecture

### Three-Layer Architecture (Bidirectional Conversion)

```PlainText
┌─────────────────────────────────────────────────────────┐
│                  Logstash Config Text                    │
│  filter {                                               │
│    grok { match => { "message" => "%{PATTERN}" } }     │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
         ↓ parse_logstash_config()    ↑ to_logstash()
         ↓ Config.from_logstash()
         ↓ ASTNode.from_logstash()
┌─────────────────────────────────────────────────────────┐
│              AST Layer (Abstract Syntax Tree)            │
│  - Responsibility: Parse, transform, generate            │
│  - Characteristics: Contains runtime state               │
│  - Purpose: Internal processing and transformation       │
└─────────────────────────────────────────────────────────┘
    ↓ to_python(as_pydantic=True)    ↑ from_python()
┌─────────────────────────────────────────────────────────┐
│              Schema Layer (Pydantic Models)              │
│  - Responsibility: Validate, serialize, store            │
│  - Characteristics: Pure data, no runtime state          │
│  - Purpose: External interaction and persistence         │
└─────────────────────────────────────────────────────────┘
         ↓ model_dump_json()    ↑ model_validate_json()
┌─────────────────────────────────────────────────────────┐
│                    JSON Text                             │
│  - Serializable, transferable                            │
│  - Persistable storage                                   │
└─────────────────────────────────────────────────────────┘
```

**Conversion Methods:**

| Direction          | Method                            | Description                                                      |
| ------------------ | --------------------------------- | ---------------------------------------------------------------- |
| Logstash → AST     | `parse_logstash_config()`         | **Recommended**: Parse complete config text to AST with validation |
| Logstash → AST     | `Config.from_logstash()`          | Low-level method: Direct parsing without extra validation        |
| Logstash → ASTNode | `ASTNode.from_logstash()`         | Parse specific node type fragments (e.g., `Plugin.from_logstash()`) |
| AST → Logstash     | `ast.to_logstash()`               | Generate Logstash config text                                    |
| AST → Schema       | `ast.to_python(as_pydantic=True)` | Convert to Pydantic Schema                                       |
| Schema → AST       | `ASTNode.from_python(schema)`     | Create AST from Schema                                           |
| Schema → JSON      | `schema.model_dump_json()`        | Serialize to JSON                                                |
| JSON → Schema      | `Schema.model_validate_json()`    | Deserialize from JSON                                            |
| AST → dict         | `ast.to_python()`                 | Convert to Python dictionary                                     |
| dict → AST         | `ASTNode.from_python(dict)`       | Create AST from dictionary                                       |

---

## 🎯 Core Design Decisions

### Decision 1: Dual-Layer Definition (AST + Schema)

**Why do we need two sets of definitions?**

| Aspect             | AST Layer                                                                  | Schema Layer                |
| ------------------ | -------------------------------------------------------------------------- | --------------------------- |
| **Responsibility** | Parse, transform, generate                                                 | Validate, serialize, store  |
| **State**          | Has runtime state (`_s`, `_loc`, `_source_text_cache`, `in_expression_context`) | Pure data model             |
| **Circular Refs**  | None (parent removed)                                                      | None                        |
| **Purpose**        | Internal processing                                                        | External interaction        |
| **Performance**    | Optimized for parsing and generation                                       | Optimized for serialization |

**Advantages:**

- ✅ Separation of concerns
- ✅ AST focuses on syntax processing
- ✅ Schema focuses on data validation
- ✅ Better maintainability

### Decision 2: Remove parent Link + Lazy source_text Computation

**Reasons:**

- Avoid circular references
- Simplify serialization
- Most nodes have `_s` and `_loc`, no need to look up parent
- Lazy computation of source_text improves performance

**Implementation:**

- Each node stores `_s` (original string) and `_loc` (parse position)
- Each node class defines `_parser_name`, `_parser_element_for_parsing`, and `_parser_element_for_get_source`
- `get_source_text()` method lazily extracts and caches to `_source_text_cache`

**Impact:**

- ✅ Functionality unchanged (most nodes can get source_text)
- ✅ Performance improved (reduced memory usage, lazy computation)
- ✅ Serialization simplified
- ✅ Extract source_text only when needed

### Decision 3: Unified API Design

**Core Methods:**

```python
# Convert to Python representation
ast.to_python()                    # → dict (default, backward compatible)
ast.to_python(as_pydantic=True)   # → Schema (new feature)

# Create AST from Python representation
ASTNode.from_python(dict)          # From dict
ASTNode.from_python(schema)        # From Schema
```

**Advantages:**

- ✅ Concise API (only two core methods)
- ✅ Backward compatible (default behavior unchanged)
- ✅ Type-safe (using overload)
- ✅ Easy to understand and use

### Decision 4: Fine-Grained Schema

**Design Principles:**

- One Schema per AST node
- Simple types also have Schemas (LSString, Number, etc.)
- Use snake_case field names as type identifiers
- Complex types use nested structure (outer Schema + inner Data)
- Don't use `node_type` field; identify type by field name
- Use TypeAlias to define Union types (e.g., `NameSchema`, `ValueSchema`, `ExpressionSchema`, `RValueSchema`)

**Examples:**

```python
# Simple type - directly use snake_case field
class LSStringSchema(BaseModel):
    ls_string: str  # ← Field name is type identifier
    model_config = {"extra": "forbid"}

# Complex type - use nested structure
class PluginData(BaseModel):
    plugin_name: str
    attributes: list[AttributeSchema] = []
    model_config = {"extra": "forbid"}

class PluginSchema(BaseModel):
    plugin: PluginData  # ← Outer wrapper
    model_config = {"extra": "forbid"}

# Dict-based type - more concise
class PluginSectionSchema(BaseModel):
    plugin_section: dict[Literal["input", "filter", "output"], list[BranchOrPluginSchema]]
    model_config = {"extra": "forbid"}

# Union type - use TypeAlias
RValueSchema: TypeAlias = Annotated[
    LSStringSchema | NumberSchema | SelectorNodeSchema | ArraySchema | RegexpSchema,
    Field(discriminator=None),
]
```

**Special Node Handling:**

- `RValue` is a transparent wrapper; when serializing, it directly returns the inner value's schema without creating a separate Schema class
- `RValueSchema` is a TypeAlias corresponding to the grammar rule `rule rvalue = string / number / selector / array / regexp`
- `ExpressionSchema` uses `RValueSchema`, which automatically expands to its member types in unions

---

## 🔄 Conversion Flow

### Conversion Path Overview

```PlainText
                    parse_logstash_config() (recommended)
                    Config.from_logstash() (low-level)
                    ASTNode.from_logstash() (fragment)
    Logstash Text ─────────────────────────────→ AST
         ↑                                        │
         │                                        │ to_python()
         │                                        ↓
         │                                      dict
         │                                        │
         │                                        │ (auto convert)
         │                                        ↓
         │                              to_python(as_pydantic=True)
         │                                        │
         │                                        ↓
    to_logstash()                             Schema
         │                                        │
         │                                        │ model_dump_json()
         │                                        ↓
         │                                      JSON
         │                                        │
         │                                        │ model_validate_json()
         │                                        ↓
         │                                     Schema
         │                                        │
         │                                        │ from_python()
         │                                        ↓
         └────────────────────────────────────── AST
```

**Key Conversion Points:**

1. **Logstash ↔ AST**: Parsing and generation

   - `parse_logstash_config()`: **Recommended** - Parse complete Logstash config text to AST with validation
   - `Config.from_logstash()`: Low-level method - Direct parsing without extra validation
   - `ASTNode.from_logstash()`: Parse specific node type fragments (e.g., `Plugin.from_logstash()`)
   - `ast.to_logstash()`: Generate Logstash text from AST

2. **AST ↔ dict**: Simple data conversion

   - `ast.to_python()`: AST to Python dictionary
   - `ASTNode.from_python(dict)`: Create AST from dictionary

3. **AST ↔ Schema**: Type-safe conversion

   - `ast.to_python(as_pydantic=True)`: AST to Schema
   - `ASTNode.from_python(schema)`: Create AST from Schema

4. **Schema ↔ JSON**: Serialization
   - `schema.model_dump_json()`: Serialize Schema to JSON
   - `Schema.model_validate_json()`: Deserialize JSON to Schema

### Complete Conversion Chain

#### Forward Conversion (Logstash → JSON)

```PlainText
Logstash Text
    ↓ parse_logstash_config() / Config.from_logstash() / ASTNode.from_logstash()
AST Tree Structure
    ↓ to_python(as_pydantic=True)
Pydantic Schema Object
    ↓ model_dump_json()
JSON Text
```

#### Reverse Conversion (JSON → Logstash)

```PlainText
JSON Text
    ↓ model_validate_json()
Pydantic Schema Object
    ↓ from_python()
AST Tree Structure
    ↓ to_logstash()
Logstash Text
```

#### Complete Roundtrip Example

```python
from logstash_parser import parse_logstash_config
from logstash_parser.schemas import ConfigSchema
from logstash_parser.ast_nodes import Config

# 1. Logstash → AST
config_text = """
filter {
    grok {
        match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
}
"""
ast = parse_logstash_config(config_text)

# 2. AST → Schema
schema = ast.to_python(as_pydantic=True)

# 3. Schema → JSON
json_str = schema.model_dump_json(indent=2)

# 4. JSON → Schema
loaded_schema = ConfigSchema.model_validate_json(json_str)

# 5. Schema → AST
reconstructed_ast = Config.from_python(loaded_schema)

# 6. AST → Logstash
output_text = reconstructed_ast.to_logstash()

# Verify roundtrip consistency
assert ast.to_python() == reconstructed_ast.to_python()
```

### Conversion Method Implementation

#### AST → Schema

```python
class Plugin(ASTNode[Attribute, PluginSchema]):
    def _to_pydantic_model(self) -> PluginSchema:
        return PluginSchema(
            plugin=PluginData(
                plugin_name=self.plugin_name,
                attributes=[
                    attr._to_pydantic_model()
                    for attr in self.children
                ]
            )
        )
```

**Note**: Schema does not include `source_text` field, only structured data.

#### Schema → AST

```python
class Plugin(ASTNode[Attribute, PluginSchema]):
    @classmethod
    def _from_pydantic(cls, schema: PluginSchema) -> Plugin:
        attributes = tuple(
            Attribute._from_pydantic(attr)
            for attr in schema.plugin.attributes
        )
        node = cls(schema.plugin.plugin_name, attributes)
        # Note: Don't set _source_text_cache because Schema doesn't have this info
        return node
```

**Important Notes**:

- Schema doesn't preserve formatting information (whitespace, comments), only structured data
- AST rebuilt from Schema won't have source text
- If source text is needed, must parse from original Logstash text

---

## 📦 Module Structure

### File Organization

```Tree
logstash-parser/src/logstash_parser/
├── __init__.py              # Public API exports
├── grammar.py               # Grammar definition (pyparsing)
├── ast_nodes.py             # AST node definitions + builder functions
├── schemas.py               # Pydantic Schema definitions
└── py.typed                 # Type hint marker
```

### Grammar Rule Implementation

This implementation fully follows the official Logstash grammar.treetop specification, using the pyparsing library to implement all grammar rules.

**Compliance Verification:**

- ✅ 100% compliant with grammar.treetop specification
- ✅ Comprehensive test case coverage
- ✅ Supports all Logstash syntax features
- ✅ Edge case testing (whitespace, comments, minimum length, etc.)
- ✅ Real config file parsing tests (complex configurations)
- ✅ Roundtrip testing (Parse → AST → Logstash → Parse)

**Implementation Details:**

- All grammar rules defined in `grammar.py`
- Uses pyparsing's combinator pattern to build parser
- Supports flexible handling of comments and whitespace
- Preserves original source text for formatted output

### Builder Functions

`ast_nodes.py` contains builder functions for pyparsing:

```python
def build_lsstring(toks: ParseResults) -> LSString:
    """Build LSString node from ParseResults"""
    value = toks.as_list()[0]
    return LSString(value)

def build_plugin_node(s, loc, toks: ParseResults) -> Plugin:
    """Build Plugin node from ParseResults, save original position info"""
    return Plugin(list(toks)[0][0], list(toks)[0][1], s=s, loc=loc)
```

**Characteristics:**

- Builder functions receive `s` (original string) and `loc` (position) parameters
- These parameters are used for lazy source_text computation
- Builder functions are registered to grammar rules via `set_parse_action` in the `PEG` class in `__init__.py`

### Module Responsibilities

| Module         | Responsibility  | Main Content                                    |
| -------------- | --------------- | ----------------------------------------------- |
| `grammar.py`   | Grammar definition | pyparsing rules, parser elements                |
| `ast_nodes.py` | AST implementation | 25 AST node classes, conversion methods, builder functions |
| `schemas.py`   | Schema definition | 23 Schema classes, validation rules             |
| `__init__.py`  | API export      | Public interface (`parse_logstash_config`), PEG initialization |

---

## 🎨 Node Type System

### Node Classification

#### 1. Simple Types (7)

- `LSString` / `LSStringSchema` - String
- `LSBareWord` / `LSBareWordSchema` - Bare word
- `Number` / `NumberSchema` - Number
- `Boolean` / `BooleanSchema` - Boolean
- `Regexp` / `RegexpSchema` - Regular expression
- `SelectorNode` / `SelectorNodeSchema` - Field selector
- `MethodCall` / `MethodCallSchema` - Method call

#### 2. Data Structures (4)

- `Array` / `ArraySchema` - Array
- `HashEntryNode` - Hash entry (internal node, no corresponding Schema)
- `Hash` / `HashSchema` - Hash table
- `Attribute` / `AttributeSchema` - Attribute

#### 3. Plugin (1)

- `Plugin` / `PluginSchema` - Plugin configuration

#### 4. Expressions (7)

- `CompareExpression` / `CompareExpressionSchema` - Comparison expression
- `RegexExpression` / `RegexExpressionSchema` - Regex expression
- `InExpression` / `InExpressionSchema` - In expression
- `NotInExpression` / `NotInExpressionSchema` - Not In expression
- `NegativeExpression` / `NegativeExpressionSchema` - Negative expression
- `BooleanExpression` / `BooleanExpressionSchema` - Boolean expression
- `Expression` / `ExpressionSchema` - Expression wrapper

#### 5. Conditional Branches (4)

- `IfCondition` / `IfConditionSchema` - If condition
- `ElseIfCondition` / `ElseIfConditionSchema` - Else If condition
- `ElseCondition` / `ElseConditionSchema` - Else condition
- `Branch` / `BranchSchema` - Branch

#### 6. Configuration (2)

- `PluginSectionNode` / `PluginSectionSchema` - Plugin section
- `Config` / `ConfigSchema` - Config root node

#### 7. Special (1)

- `RValue` - Right value wrapper (no Schema)

**Total**: 26 AST node classes, 24 Schema classes (excluding Data classes and type aliases)

**Notes**:

- `ExpressionSchema` and `RValueSchema` are type aliases, not counted in Schema class count
- `HashEntryNode` and `RValue` are internal nodes without corresponding Schemas
- `AttributeSchema` uses `RootModel`, doesn't inherit `ASTNodeSchema`

---

## 🔒 Type Safety

### Generic Type Parameters

AST nodes use Generic type parameters for type safety:

```python
T = TypeVar("T", bound="ASTNode")
S = TypeVar("S", bound="ASTNodeSchema")

class ASTNode(Generic[T, S]):
    children: tuple[T, ...]  # ← Child node type (using tuple not list)
    schema_class: type[S]  # ← Corresponding Schema type
```

**Advantages:**

- Type checker can infer child node types
- Each node class explicitly specifies its Schema type
- Provides better IDE support and type hints

### Field Name Type Identification

Use snake_case field names as type identifiers:

```python
class PluginSchema(BaseModel):
    plugin: PluginData  # ← Field name "plugin" identifies this as Plugin type
    model_config = {"extra": "forbid"}
```

### Union Types

Use Annotated and `discriminator=None` for type discrimination:

```python
ValueSchema = Annotated[
    LSStringSchema
    | LSBareWordSchema
    | NumberSchema
    | ...,
    Field(discriminator=None)  # ← Pydantic auto-identifies by field name
]
```

**Advantages:**

- More concise JSON representation
- Field name is type, no need for extra `node_type` field
- Pydantic automatically identifies type by field name

### Overload

Use overload for accurate return types:

```python
@overload
def to_python(self, as_pydantic: Literal[True]) -> BaseModel: ...

@overload
def to_python(self, as_pydantic: Literal[False] = False) -> dict[str, Any]: ...
```

---

## 📊 Performance Considerations

### Parsing Performance

- ✅ Efficient parsing using pyparsing
- ✅ Lazy source_text computation
- ✅ Cache parsing results

### Serialization Performance

- ✅ Pydantic-optimized serialization
- ✅ Schema doesn't include source_text, reducing serialization overhead
- ✅ Supports JSON serialization and deserialization

### Memory Usage

- ✅ Removing parent reduces memory
- ✅ Lazy computation reduces overhead
- ✅ Share immutable data

---

## 🔄 Backward Compatibility

### Guarantees

- ✅ Existing `to_python()` calls return dict (default behavior)
- ✅ Existing `to_logstash()` method unchanged
- ✅ Existing `to_source()` method unchanged
- ✅ Existing AST structure unchanged (only parent removed)

### Migration Path

```python
# Old code (still works)
data = ast.to_python()

# New code (optional)
schema = ast.to_python(as_pydantic=True)
json_str = schema.model_dump_json()
```

---

## 🎯 Design Principles

1. **Separation of Concerns**: AST and Schema each have their own responsibilities
2. **Type Safety**: Fully utilize Python's type system
3. **Backward Compatible**: Don't break existing APIs
4. **Performance First**: Optimize critical paths
5. **Easy to Use**: Concise API design
6. **Extensibility**: Easy to add new node types

---

## 📚 Related Documentation

- [API Reference](./API_REFERENCE.md)
- [User Guide](./USER_GUIDE.md)
- [Testing Guide](./TESTING.md)
- [Changelog](./CHANGELOG.md)

**中文文档 (Chinese)**:

- [架构设计 (中文)](./zh_cn/ARCHITECTURE.md)
