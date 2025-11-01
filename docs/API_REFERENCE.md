# Logstash Parser API 参考

## 📋 目录

- [核心函数](#核心函数)
- [AST 节点](#ast-节点)
- [Schema 类型](#schema-类型)
- [转换方法](#转换方法)
- [异常](#异常)
- [类型映射表](#类型映射表)

---

## 核心函数

### `parse_logstash_config(config_text: str) -> Config`

解析 Logstash 配置文本为 AST。

**参数：**

- `config_text` (str): Logstash 配置文本

**返回：**

- `Config`: 配置 AST 根节点

**异常：**

- `ParseError`: 解析失败时抛出

**示例：**

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

## AST 节点

### 基类：`ASTNode`

所有 AST 节点的基类。

#### 类属性

- `schema_class: type[S]` - 对应的 Schema 类（子类必须覆盖）
- `_parser_name: str | None` - 解析器名称（可选）
- `_parser_element_for_get_source: ParserElement` - 用于 `get_source_text()` 的解析器元素（通常是 `xxx_with_source`）
- `_parser_element_for_parsing: ParserElement` - 用于 `from_logstash()` 的解析器元素（已设置 parse_action）

#### 实例属性

- `children: tuple[T, ...]` - 子节点元组
- `in_expression_context: bool` - 是否在表达式上下文中
- `uid: int` - 唯一标识符
- `_s: str | None` - 原始解析字符串（用于延迟计算）
- `_loc: int | None` - 解析位置（用于延迟计算）
- `_source_text_cache: str | None` - 缓存的源文本

#### 方法

##### `to_python(as_pydantic: bool = False) -> dict | BaseModel`

转换为 Python 表示。

**参数：**

- `as_pydantic` (bool): 是否返回 Pydantic Schema（默认 False）

**返回：**

- `dict`: 当 `as_pydantic=False` 时
- `BaseModel`: 当 `as_pydantic=True` 时

**示例：**

```python
# 返回 dict
python_dict = ast.to_python()

# 返回 Pydantic Schema
schema = ast.to_python(as_pydantic=True)
```

##### `from_python(data: dict | BaseModel) -> ASTNode`

从 Python 表示创建 AST 节点（类方法）。

**参数：**

- `data` (dict | BaseModel): Python 字典或 Pydantic Schema

**返回：**

- `ASTNode`: AST 节点实例

**实现细节：**

- 如果 `data` 是 dict，先使用 `schema_class.model_validate(data)` 转换为 Schema
- 然后调用 `_from_pydantic(schema)` 创建 AST 节点

**示例：**

```python
# 从 dict 创建
ast = Plugin.from_python({"plugin": {"plugin_name": "grok", "attributes": []}})

# 从 Schema 创建
ast = Plugin.from_python(plugin_schema)
```

##### `from_schema(schema: ASTNodeSchema) -> ASTNode`

从 Pydantic Schema 创建 AST 节点（类方法）。

**参数：**

- `schema` (ASTNodeSchema): Pydantic Schema 对象

**返回：**

- `ASTNode`: 对应的 AST 节点实例

**异常：**

- `ValueError`: 如果 schema 类型未知

**类型提示：**

- 提供了 23 个 `@overload` 声明，覆盖所有 Schema 到 Node 的映射
- 类型检查器可以自动推断出正确的返回类型

**示例：**

```python
# 基本使用
schema = LSStringSchema(ls_string='"hello"')
node = ASTNode.from_schema(schema)
# 类型检查器推断: node: LSString

# 数字类型
number_schema = NumberSchema(number=42)
number_node = ASTNode.from_schema(number_schema)
# 类型检查器推断: number_node: Number

# 数组类型
array_schema = ArraySchema(array=[...])
array_node = ASTNode.from_schema(array_schema)
# 类型检查器推断: array_node: Array
```

**支持的类型映射：**

| 分类     | Schema 类型                                                                                                                                  | Node 类型                                                                                                | 数量 |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ---- |
| 简单类型 | LSStringSchema, LSBareWordSchema, NumberSchema, BooleanSchema, RegexpSchema, SelectorNodeSchema                                              | LSString, LSBareWord, Number, Boolean, Regexp, SelectorNode                                              | 6    |
| 数据结构 | ArraySchema, HashSchema, AttributeSchema                                                                                                     | Array, Hash, Attribute                                                                                   | 3    |
| 插件     | PluginSchema                                                                                                                                 | Plugin                                                                                                   | 1    |
| 表达式   | CompareExpressionSchema, RegexExpressionSchema, InExpressionSchema, NotInExpressionSchema, NegativeExpressionSchema, BooleanExpressionSchema | CompareExpression, RegexExpression, InExpression, NotInExpression, NegativeExpression, BooleanExpression | 6    |
| 条件     | IfConditionSchema, ElseIfConditionSchema, ElseConditionSchema, BranchSchema                                                                  | IfCondition, ElseIfCondition, ElseCondition, Branch                                                      | 4    |
| 配置     | PluginSectionSchema, ConfigSchema                                                                                                            | PluginSectionNode, Config                                                                                | 2    |
| 兜底     | ASTNodeSchema                                                                                                                                | ASTNode                                                                                                  | 1    |

**类型安全最佳实践：**

```python
# ✓ 好 - 使用具体类型
schema: LSStringSchema = LSStringSchema(ls_string='"hello"')
node = ASTNode.from_schema(schema)  # 类型: LSString

# ✗ 不好 - 使用基类会失去类型推断
schema: ASTNodeSchema = LSStringSchema(ls_string='"hello"')
node = ASTNode.from_schema(schema)  # 类型: ASTNode (回退)

# ✓ 好 - 使用类型窄化
schema: ASTNodeSchema = get_schema()
if isinstance(schema, LSStringSchema):
    node = ASTNode.from_schema(schema)  # 类型: LSString
    print(node.lexeme)  # ✓ 类型安全
```

##### `to_logstash(indent: int = 0) -> str`

生成 Logstash 配置文本。

**参数：**

- `indent` (int): 缩进级别（默认 0）

**返回：**

- `str`: Logstash 配置文本

**示例：**

```python
config_text = ast.to_logstash()
```

##### `get_source_text() -> str | None`

延迟获取原始源文本，只在需要时才提取。

**返回：**

- `str | None`: 原始源文本，如果不可用则返回 None

**实现细节：**

- 首先检查缓存 `_source_text_cache`
- 如果未缓存且有 `_s`, `_loc`, `_parser_name`, `_parser_element_for_get_source`，则从原始字符串提取
- 提取后缓存结果以提高性能

##### `set_expression_context(value: bool)`

设置表达式上下文标志，并递归设置所有子节点。

**参数：**

- `value` (bool): 是否在表达式上下文中

##### `traverse()`

递归遍历所有子节点。

##### `to_repr(indent: int = 0) -> str`

生成节点的字符串表示（用于调试）。

**参数：**

- `indent` (int): 缩进级别

**返回：**

- `str`: 节点的字符串表示

##### `_to_python_dict() -> Any`

转换为 Python dict（内部方法）。

**返回：**

- `Any`: Python 原生数据结构

**实现细节：**

- 默认实现调用 `_to_pydantic_model()` 然后使用 `model_dump(mode="json", exclude_none=True)`
- 子类可以覆盖以自定义行为

##### `_to_pydantic_model() -> S`

转换为 Pydantic Schema（内部方法，子类必须实现）。

**返回：**

- `S`: Pydantic Schema 对象

##### `_from_pydantic(schema: S) -> ASTNode`

从 Pydantic Schema 创建 AST 节点（类方法，子类必须实现）。

**参数：**

- `schema` (S): Pydantic Schema 对象

**返回：**

- `ASTNode`: AST 节点实例

##### `_get_snake_case_key() -> str`

获取节点类型的 snake_case 键名（内部方法）。

**返回：**

- `str`: snake_case 键名

**示例：**

- `LSString` → `"ls_string"`
- `CompareExpression` → `"compare_expression"`

---

### 简单类型

#### `LSString`

字符串节点。

**属性：**

- `lexeme: str` - 原始字符串（带引号）
- `value: str` - 解析后的值（使用 `ast.literal_eval` 解析）

**实现细节：**

- 使用 Python 的 `ast.literal_eval()` 解析字符串字面量
- 自动处理转义字符（如 `\n`, `\t`, `\f` 等）
- 特殊处理 `\r\n` 和 `\n`，替换为 `\\n` 以避免解析错误
- 支持单引号和双引号

**示例：**

```python
s = LSString('"hello world"')
print(s.lexeme)  # '"hello world"'
print(s.value)   # 'hello world'

# 转义字符处理
s2 = LSString('"line1\\nline2"')
print(s2.value)  # 'line1\nline2' (实际换行)
```

#### `LSBareWord`

裸词节点。

**属性：**

- `value: str` - 裸词值

#### `Number`

数字节点。

**属性：**

- `value: int | float` - 数字值

#### `Boolean`

布尔节点。

**属性：**

- `value: bool` - 布尔值

#### `Regexp`

正则表达式节点。

**属性：**

- `lexeme: str` - 原始正则表达式
- `value: str` - 解析后的值

#### `SelectorNode`

字段选择器节点。

**属性：**

- `raw: str` - 原始选择器字符串（如 `[foo][bar]`）

---

### 数据结构

#### `Array`

数组节点。

**属性：**

- `children: tuple[Plugin | Boolean | LSBareWord | LSString | Number | Array | Hash, ...]` - 数组元素元组

**示例：**

```python
arr = Array([LSString('"a"'), LSString('"b"')])
```

#### `Hash`

哈希表节点。

**属性：**

- `children: tuple[HashEntryNode, ...]` - 哈希条目元组

#### `HashEntryNode`

哈希条目节点。

**属性：**

- `key: LSString | LSBareWord | Number` - 键
- `value: ASTNode` - 值

#### `Attribute`

属性节点。

**属性：**

- `name: LSString | LSBareWord` - 属性名
- `value: ASTNode` - 属性值

---

### 插件

#### `Plugin`

插件节点。

**属性：**

- `plugin_name: str` - 插件名称
- `children: tuple[Attribute, ...]` - 属性元组

**示例：**

```python
plugin = Plugin("grok", [
    Attribute(LSBareWord("match"), Hash(...))
])
```

---

### 表达式

#### `CompareExpression`

比较表达式节点。

**属性：**

- `left: ASTNode` - 左操作数
- `operator: str` - 比较操作符（`==`, `!=`, `<`, `>`, `<=`, `>=`）
- `right: ASTNode` - 右操作数

#### `RegexExpression`

正则表达式节点。

**属性：**

- `left: ASTNode` - 左操作数
- `operator: str` - 正则操作符（`=~`, `!~`）
- `pattern: ASTNode` - 正则模式

#### `InExpression`

In 表达式节点。

**属性：**

- `value: ASTNode` - 要检查的值
- `operator: str` - 操作符（`in`）
- `collection: ASTNode` - 集合

#### `NotInExpression`

Not In 表达式节点。

**属性：**

- `value: ASTNode` - 要检查的值
- `operator: str` - 操作符（`not in`，支持空白符和注释）
- `collection: ASTNode` - 集合

**实现细节：**

- 使用 `pp.Combine()` 将 "not"、空白符/注释、"in" 合并为单个 token
- 支持 `not in`、`not  in`、`not\tin`、`not # comment\n in` 等格式
- 符合 grammar.treetop 规范：`"not " cs "in"`

#### `NegativeExpression`

否定表达式节点。

**属性：**

- `operator: str` - 否定操作符（`!`）
- `expression: ASTNode` - 被否定的表达式

#### `BooleanExpression`

布尔表达式节点。

**属性：**

- `left: ASTNode` - 左操作数
- `operator: str` - 布尔操作符（`and`, `or`, `xor`, `nand`）
- `right: ASTNode` - 右操作数

---

### 条件分支

#### `IfCondition`

If 条件节点。

**属性：**

- `expr: Expression | BooleanExpression` - 条件表达式
- `children: list[Plugin | Branch]` - 条件体

#### `ElseIfCondition`

Else If 条件节点。

**属性：**

- `expr: CompareExpression | RegexExpression | InExpression | NotInExpression | NegativeExpression | BooleanExpression | SelectorNode` - 条件表达式
- `children: tuple[Plugin | Branch, ...]` - 条件体元组

#### `ElseCondition`

Else 条件节点。

**属性：**

- `expr: CompareExpression | ... | None` - 条件表达式（通常为 None，除非是合并的 else if）
- `children: tuple[Plugin | Branch, ...]` - 条件体元组

#### `Branch`

分支节点。

**属性：**

- `children: tuple[IfCondition | ElseIfCondition | ElseCondition, ...]` - 条件元组

---

### 配置

#### `PluginSectionNode`

插件段节点。

**属性：**

- `plugin_type: str` - 段类型（`input`, `filter`, `output`）
- `children: tuple[Plugin | Branch, ...]` - 插件或分支元组

#### `Config`

配置根节点。

---

## Schema 类型

### 基类：`ASTNodeSchema`

所有 Schema 的基类。

**字段：**

- `node_type: str` - 节点类型
- `source_text: str | None` - 原始源文本（不序列化）

**配置：**

```python
model_config = {"extra": "forbid"}  # 禁止额外字段
```

---

### 简单类型 Schema

#### `LSStringSchema`

```python
class LSStringSchema(BaseModel):
    ls_string: str  # 原始字符串（带引号）
    model_config = {"extra": "forbid"}
```

#### `LSBareWordSchema`

```python
class LSBareWordSchema(BaseModel):
    ls_bare_word: str  # 裸词值
    model_config = {"extra": "forbid"}
```

#### `NumberSchema`

```python
class NumberSchema(BaseModel):
    number: int | float  # 数字值
    model_config = {"extra": "forbid"}
```

#### `BooleanSchema`

```python
class BooleanSchema(BaseModel):
    boolean: bool  # 布尔值
    model_config = {"extra": "forbid"}
```

#### `RegexpSchema`

```python
class RegexpSchema(BaseModel):
    regexp: str  # 原始正则表达式（带斜杠）
    model_config = {"extra": "forbid"}
```

#### `SelectorNodeSchema`

```python
class SelectorNodeSchema(BaseModel):
    selector_node: str  # 原始选择器字符串（如 [foo][bar]）
    model_config = {"extra": "forbid"}
```

---

### 数据结构 Schema

#### `ArraySchema`

```python
class ArraySchema(BaseModel):
    array: list[ValueSchema]  # 数组元素
    model_config = {"extra": "forbid"}
```

#### `HashSchema`

```python
class HashSchema(BaseModel):
    hash: dict[str, ValueSchema]  # 哈希表键值对
    model_config = {"extra": "forbid"}
```

**注意**: Hash 使用 dict 表示,键为字符串,值为 ValueSchema。

#### `AttributeSchema`

```python
class AttributeSchema(RootModel[dict[str, ValueSchema]]):
    """属性使用 RootModel 直接序列化为 dict"""
    root: dict[str, ValueSchema]
```

**注意**: Attribute 使用 RootModel,序列化时直接是 `{"attribute_name": value}` 格式。

---

### 插件 Schema

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

**注意**: Plugin 使用嵌套结构,外层是 `plugin` 字段,内层是 `PluginData`。

---

### 表达式 Schema

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

**注意**: 所有表达式都使用嵌套结构,外层是 snake_case 字段名,内层是对应的 Data 类。

---

### 条件分支 Schema

#### `IfConditionData` / `IfConditionSchema`

```python
class IfConditionData(BaseModel):
    expr: ExpressionSchema  # 注意：这是类型别名，实际使用具体的表达式 Schema
    body: list[BranchOrPluginSchema] = []
    model_config = {"extra": "forbid"}

class IfConditionSchema(BaseModel):
    if_condition: IfConditionData
    model_config = {"extra": "forbid"}
```

#### `ElseIfConditionData` / `ElseIfConditionSchema`

```python
class ElseIfConditionData(BaseModel):
    expr: ExpressionSchema  # 注意：这是类型别名，实际使用具体的表达式 Schema
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

**注意**: Branch 包含 If/ElseIf/Else 条件的列表。

---

### 配置 Schema

#### `PluginSectionSchema`

```python
class PluginSectionSchema(BaseModel):
    plugin_section: dict[Literal["input", "filter", "output"], list[BranchOrPluginSchema]]
    model_config = {"extra": "forbid"}
```

**说明**: PluginSection 使用 dict 表示,其中 key 是 plugin_type (input/filter/output),value 是 children 列表。

**示例**:

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

### Union 类型

#### `NameSchema`

属性名类型（LSString 或 LSBareWord）：

```python
NameSchema = Annotated[
    LSStringSchema | LSBareWordSchema,
    Field(discriminator=None)
]
```

#### `ValueSchema`

所有可能的值类型：

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

**注意**: 使用 `discriminator=None`,Pydantic 会根据字段名自动识别类型。

#### `ExpressionSchema`

所有可能的表达式类型（类型别名，不是类）：

```python
ExpressionSchema = Annotated[
    CompareExpressionSchema
    | RegexExpressionSchema
    | InExpressionSchema
    | NotInExpressionSchema
    | NegativeExpressionSchema
    | BooleanExpressionSchema
    | SelectorNodeSchema,
    Field(discriminator=None)
]
```

**注意**: `ExpressionSchema` 是一个类型别名，不是一个类。在使用时应该直接使用具体的表达式 Schema 类型。

#### `ConditionSchema`

条件类型（If/ElseIf/Else）：

```python
ConditionSchema = Annotated[
    IfConditionSchema | ElseIfConditionSchema | ElseConditionSchema,
    Field(discriminator=None)
]
```

#### `BranchOrPluginSchema`

分支或插件：

```python
BranchOrPluginSchema = Annotated[
    BranchSchema | PluginSchema,
    Field(discriminator=None)
]
```

---

## 转换方法

### Schema 方法

所有 Schema 类都提供以下方法：

#### `model_dump() -> dict`

转换为字典。

```python
data = schema.model_dump()
```

#### `model_dump_json(indent: int = None) -> str`

序列化为 JSON。

```python
json_str = schema.model_dump_json(indent=2)
```

#### `model_validate(data: dict) -> Schema`

从字典验证并创建 Schema。

```python
schema = ConfigSchema.model_validate(data)
```

#### `model_validate_json(json_str: str) -> Schema`

从 JSON 验证并创建 Schema。

```python
schema = ConfigSchema.model_validate_json(json_str)
```

---

## 异常

### `ParseError`

解析错误异常。

**继承：** `Exception`

**使用：**

```python
try:
    ast = parse_logstash_config(config_text)
except ParseError as e:
    print(f"解析失败: {e}")
```

---

## 类型映射表

| AST 节点           | Schema 类                | Schema 字段名         |
| ------------------ | ------------------------ | --------------------- |
| LSString           | LSStringSchema           | `ls_string`           |
| LSBareWord         | LSBareWordSchema         | `ls_bare_word`        |
| Number             | NumberSchema             | `number`              |
| Boolean            | BooleanSchema            | `boolean`             |
| Regexp             | RegexpSchema             | `regexp`              |
| SelectorNode       | SelectorNodeSchema       | `selector_node`       |
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

**注意**: Schema 使用 snake_case 字段名作为类型标识,而不是 `node_type` 字段。

---

## 相关文档

- [架构设计](./ARCHITECTURE.md)
- [使用指南](./USER_GUIDE.md)
- [测试指南](./TESTING.md)
- [更新日志](./CHANGELOG.md)

- [架构设计](./ARCHITECTURE.md)
- [使用指南](./USER_GUIDE.md)
- [测试指南](./TESTING.md)
- [更新日志](./CHANGELOG.md)
