# Logstash Parser API 参考

## 📋 目录

- [核心函数](#核心函数)
- [AST 节点](#ast-节点)
- [Schema 类型](#schema-类型)
- [转换方法](#转换方法)
- [工具函数](#工具函数)

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

#### 属性

- `children: list[T]` - 子节点列表
- `in_expression_context: bool` - 是否在表达式上下文中
- `uid: int` - 唯一标识符

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

从 Python 表示创建 AST 节点。

**参数：**
- `data` (dict | BaseModel): Python 字典或 Pydantic Schema

**返回：**
- `ASTNode`: AST 节点实例

**示例：**

```python
# 从 dict 创建
ast = Plugin.from_python({"plugin_name": "grok", ...})

# 从 Schema 创建
ast = Plugin.from_python(plugin_schema)
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

获取原始源文本。

**返回：**
- `str | None`: 原始源文本，如果不可用则返回 None

---

### 简单类型

#### `LSString`

字符串节点。

**属性：**
- `lexeme: str` - 原始字符串（带引号）
- `value: str` - 解析后的值

**示例：**

```python
s = LSString('"hello world"')
print(s.lexeme)  # '"hello world"'
print(s.value)   # 'hello world'
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
- `children: list[ASTNode]` - 数组元素

**示例：**

```python
arr = Array([LSString('"a"'), LSString('"b"')])
```

#### `Hash`

哈希表节点。

**属性：**
- `children: list[HashEntryNode]` - 哈希条目

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
- `children: list[Attribute]` - 属性列表

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
- `operator: str` - 操作符（`not in`）
- `collection: ASTNode` - 集合

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

#### `Expression`

表达式包装器节点。

**属性：**
- `condition: ASTNode` - 包装的条件

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
- `expr: Expression | BooleanExpression` - 条件表达式
- `children: list[Plugin | Branch]` - 条件体

#### `ElseCondition`

Else 条件节点。

**属性：**
- `children: list[Plugin | Branch]` - 条件体

#### `Branch`

分支节点。

**属性：**
- `children: list[IfCondition | ElseIfCondition | ElseCondition]` - 条件列表

---

### 配置

#### `PluginSectionNode`

插件段节点。

**属性：**
- `plugin_type: str` - 段类型（`input`, `filter`, `output`）
- `children: list[Plugin | Branch]` - 插件或分支列表

#### `Config`

配置根节点。

**属性：**
- `children: list[PluginSectionNode]` - 插件段列表

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
class LSStringSchema(ASTNodeSchema):
    node_type: Literal["LSString"] = "LSString"
    lexeme: str
    value: str
```

#### `LSBareWordSchema`

```python
class LSBareWordSchema(ASTNodeSchema):
    node_type: Literal["LSBareWord"] = "LSBareWord"
    value: str
```

#### `NumberSchema`

```python
class NumberSchema(ASTNodeSchema):
    node_type: Literal["Number"] = "Number"
    value: int | float
```

#### `BooleanSchema`

```python
class BooleanSchema(ASTNodeSchema):
    node_type: Literal["Boolean"] = "Boolean"
    value: bool
```

#### `RegexpSchema`

```python
class RegexpSchema(ASTNodeSchema):
    node_type: Literal["Regexp"] = "Regexp"
    lexeme: str
    value: str
```

#### `SelectorNodeSchema`

```python
class SelectorNodeSchema(ASTNodeSchema):
    node_type: Literal["SelectorNode"] = "SelectorNode"
    raw: str
```

---

### 数据结构 Schema

#### `ArraySchema`

```python
class ArraySchema(ASTNodeSchema):
    node_type: Literal["Array"] = "Array"
    children: list[ValueSchema]
```

#### `HashSchema`

```python
class HashSchema(ASTNodeSchema):
    node_type: Literal["Hash"] = "Hash"
    children: list[HashEntryNodeSchema]
```

#### `HashEntryNodeSchema`

```python
class HashEntryNodeSchema(ASTNodeSchema):
    node_type: Literal["HashEntry"] = "HashEntry"
    key: LSStringSchema | LSBareWordSchema | NumberSchema
    value: ValueSchema
```

#### `AttributeSchema`

```python
class AttributeSchema(ASTNodeSchema):
    node_type: Literal["Attribute"] = "Attribute"
    name: LSStringSchema | LSBareWordSchema
    value: ValueSchema
```

---

### 插件 Schema

#### `PluginSchema`

```python
class PluginSchema(ASTNodeSchema):
    node_type: Literal["Plugin"] = "Plugin"
    plugin_name: str
    attributes: list[AttributeSchema]
```

---

### 表达式 Schema

#### `CompareExpressionSchema`

```python
class CompareExpressionSchema(ASTNodeSchema):
    node_type: Literal["CompareExpression"] = "CompareExpression"
    left: ValueSchema
    operator: str
    right: ValueSchema
```

#### `RegexExpressionSchema`

```python
class RegexExpressionSchema(ASTNodeSchema):
    node_type: Literal["RegexExpression"] = "RegexExpression"
    left: ValueSchema
    operator: str
    pattern: ValueSchema
```

#### `InExpressionSchema`

```python
class InExpressionSchema(ASTNodeSchema):
    node_type: Literal["InExpression"] = "InExpression"
    value: ValueSchema
    operator: str = "in"
    collection: ValueSchema
```

#### `NotInExpressionSchema`

```python
class NotInExpressionSchema(ASTNodeSchema):
    node_type: Literal["NotInExpression"] = "NotInExpression"
    value: ValueSchema
    operator: str = "not in"
    collection: ValueSchema
```

#### `NegativeExpressionSchema`

```python
class NegativeExpressionSchema(ASTNodeSchema):
    node_type: Literal["NegativeExpression"] = "NegativeExpression"
    operator: str
    expression: ValueSchema
```

#### `BooleanExpressionSchema`

```python
class BooleanExpressionSchema(ASTNodeSchema):
    node_type: Literal["BooleanExpression"] = "BooleanExpression"
    left: ValueSchema
    operator: str
    right: ValueSchema
```

#### `ExpressionSchema`

```python
class ExpressionSchema(ASTNodeSchema):
    node_type: Literal["Expression"] = "Expression"
    condition: ValueSchema
```

---

### 条件分支 Schema

#### `IfConditionSchema`

```python
class IfConditionSchema(ASTNodeSchema):
    node_type: Literal["IfCondition"] = "IfCondition"
    expr: ExpressionValueSchema
    body: list[BranchOrPluginSchema]
```

#### `ElseIfConditionSchema`

```python
class ElseIfConditionSchema(ASTNodeSchema):
    node_type: Literal["ElseIfCondition"] = "ElseIfCondition"
    expr: ExpressionValueSchema
    body: list[BranchOrPluginSchema]
```

#### `ElseConditionSchema`

```python
class ElseConditionSchema(ASTNodeSchema):
    node_type: Literal["ElseCondition"] = "ElseCondition"
    body: list[BranchOrPluginSchema]
```

#### `BranchSchema`

```python
class BranchSchema(ASTNodeSchema):
    node_type: Literal["Branch"] = "Branch"
    children: list[IfConditionSchema | ElseIfConditionSchema | ElseConditionSchema]
```

---

### 配置 Schema

#### `PluginSectionNodeSchema`

```python
class PluginSectionNodeSchema(ASTNodeSchema):
    node_type: Literal["PluginSection"] = "PluginSection"
    plugin_type: str
    children: list[BranchOrPluginSchema]
```

#### `ConfigSchema`

```python
class ConfigSchema(ASTNodeSchema):
    node_type: Literal["Config"] = "Config"
    children: list[PluginSectionNodeSchema]
```

---

### Union 类型

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
    | BooleanExpressionSchema
    | ExpressionSchema,
    Field(discriminator="node_type")
]
```

#### `ExpressionValueSchema`

所有可能的表达式类型：

```python
ExpressionValueSchema = Annotated[
    CompareExpressionSchema
    | RegexExpressionSchema
    | InExpressionSchema
    | NotInExpressionSchema
    | NegativeExpressionSchema
    | BooleanExpressionSchema
    | ExpressionSchema,
    Field(discriminator="node_type")
]
```

#### `BranchOrPluginSchema`

分支或插件：

```python
BranchOrPluginSchema = Annotated[
    BranchSchema | PluginSchema,
    Field(discriminator="node_type")
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

## 工具函数

### `_schema_to_node(schema: ASTNodeSchema) -> ASTNode`

将 Schema 转换为 AST 节点（内部使用）。

**参数：**
- `schema` (ASTNodeSchema): Pydantic Schema 对象

**返回：**
- `ASTNode`: 对应的 AST 节点实例

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

| AST 节点 | Schema 类 | node_type |
|---------|----------|-----------|
| LSString | LSStringSchema | "LSString" |
| LSBareWord | LSBareWordSchema | "LSBareWord" |
| Number | NumberSchema | "Number" |
| Boolean | BooleanSchema | "Boolean" |
| Regexp | RegexpSchema | "Regexp" |
| SelectorNode | SelectorNodeSchema | "SelectorNode" |
| Array | ArraySchema | "Array" |
| Hash | HashSchema | "Hash" |
| HashEntryNode | HashEntryNodeSchema | "HashEntry" |
| Attribute | AttributeSchema | "Attribute" |
| Plugin | PluginSchema | "Plugin" |
| CompareExpression | CompareExpressionSchema | "CompareExpression" |
| RegexExpression | RegexExpressionSchema | "RegexExpression" |
| InExpression | InExpressionSchema | "InExpression" |
| NotInExpression | NotInExpressionSchema | "NotInExpression" |
| NegativeExpression | NegativeExpressionSchema | "NegativeExpression" |
| BooleanExpression | BooleanExpressionSchema | "BooleanExpression" |
| Expression | ExpressionSchema | "Expression" |
| IfCondition | IfConditionSchema | "IfCondition" |
| ElseIfCondition | ElseIfConditionSchema | "ElseIfCondition" |
| ElseCondition | ElseConditionSchema | "ElseCondition" |
| Branch | BranchSchema | "Branch" |
| PluginSectionNode | PluginSectionNodeSchema | "PluginSection" |
| Config | ConfigSchema | "Config" |

---

## 相关文档

- [架构设计](./ARCHITECTURE.md)
- [使用指南](./USER_GUIDE.md)
- [更新日志](./CHANGELOG.md)
