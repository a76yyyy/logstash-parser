# Logstash Parser 架构设计

## 📋 概述

Logstash Parser 是一个用于解析、转换和生成 Logstash 配置的 Python 库。它提供了完整的双向转换能力，支持 Logstash 配置文本、AST（抽象语法树）、Python 字典和 Pydantic Schema 之间的相互转换。

---

## 🏗️ 系统架构

### 三层架构（双向转换）

```
┌─────────────────────────────────────────────────────────┐
│                  Logstash 配置文本                       │
│  filter {                                               │
│    grok { match => { "message" => "%{PATTERN}" } }     │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
         ↓ parse_logstash_config()    ↑ to_logstash()
┌─────────────────────────────────────────────────────────┐
│              AST 层 (Abstract Syntax Tree)               │
│  - 职责：解析、转换、生成                                 │
│  - 特点：包含运行时状态                                   │
│  - 用途：内部处理和转换                                   │
└─────────────────────────────────────────────────────────┘
    ↓ to_python(as_pydantic=True)    ↑ from_python()
┌─────────────────────────────────────────────────────────┐
│              Schema 层 (Pydantic Models)                 │
│  - 职责：验证、序列化、存储                               │
│  - 特点：纯数据，无运行时状态                             │
│  - 用途：外部交互和持久化                                 │
└─────────────────────────────────────────────────────────┘
         ↓ model_dump_json()    ↑ model_validate_json()
┌─────────────────────────────────────────────────────────┐
│                    JSON 文本                             │
│  - 可序列化、可传输                                       │
│  - 可持久化存储                                           │
└─────────────────────────────────────────────────────────┘
```

**转换方法说明：**

| 方向 | 方法 | 说明 |
|------|------|------|
| Logstash → AST | `parse_logstash_config()` | 解析配置文本为 AST |
| AST → Logstash | `ast.to_logstash()` | 生成 Logstash 配置文本 |
| AST → Schema | `ast.to_python(as_pydantic=True)` | 转换为 Pydantic Schema |
| Schema → AST | `ASTNode.from_python(schema)` | 从 Schema 创建 AST |
| Schema → JSON | `schema.model_dump_json()` | 序列化为 JSON |
| JSON → Schema | `Schema.model_validate_json()` | 从 JSON 反序列化 |
| AST → dict | `ast.to_python()` | 转换为 Python 字典 |
| dict → AST | `ASTNode.from_python(dict)` | 从字典创建 AST |

---

## 🎯 核心设计决策

### 决策 1：双层定义（AST + Schema）

**为什么需要两套定义？**

| 方面 | AST 层 | Schema 层 |
|------|--------|-----------|
| **职责** | 解析、转换、生成 | 验证、序列化、存储 |
| **状态** | 有运行时状态 (_s, _loc, in_expression_context) | 纯数据模型 |
| **循环引用** | 无（已移除 parent） | 无 |
| **用途** | 内部处理 | 外部交互 |
| **性能** | 优化解析和生成 | 优化序列化 |

**优势：**
- ✅ 职责分离，各司其职
- ✅ AST 专注于语法处理
- ✅ Schema 专注于数据验证
- ✅ 更好的可维护性

### 决策 2：移除 parent 链接 + 延迟计算 source_text

**原因：**
- 避免循环引用
- 简化序列化
- 大多数节点都有 `_s` 和 `_loc`，不需要向上查找
- 延迟计算 source_text 可以提高性能

**实现：**
- 每个节点保存 `_s`（原始字符串）和 `_loc`（解析位置）
- 每个节点类定义 `_parser_name` 和 `_parser_element`
- `get_source_text()` 方法延迟提取并缓存结果

**影响：**
- ✅ 功能不变（大多数节点都能获取 source_text）
- ✅ 性能提升（减少内存占用，延迟计算）
- ✅ 序列化更简单
- ✅ 只在需要时才提取 source_text

### 决策 3：统一的 API 设计

**核心方法：**

```python
# 转换为 Python 表示
ast.to_python()                    # → dict（默认，向后兼容）
ast.to_python(as_pydantic=True)   # → Schema（新功能）

# 从 Python 表示创建 AST
ASTNode.from_python(dict)          # 从 dict
ASTNode.from_python(schema)        # 从 Schema
```

**优势：**
- ✅ API 简洁（只有两个核心方法）
- ✅ 向后兼容（默认行为不变）
- ✅ 类型安全（使用 overload）
- ✅ 易于理解和使用

### 决策 4：细粒度 Schema

**设计原则：**
- 每个 AST 节点一个 Schema
- 简单类型也有 Schema（LSString, Number 等）
- 使用 snake_case 字段名作为类型标识
- 复杂类型使用嵌套结构（外层 Schema + 内层 Data）
- 不使用 `node_type` 字段,而是通过字段名识别类型

**示例：**

```python
# 简单类型 - 直接使用 snake_case 字段
class LSStringSchema(BaseModel):
    ls_string: str  # ← 字段名即类型标识
    model_config = {"extra": "forbid"}

# 复杂类型 - 使用嵌套结构
class PluginData(BaseModel):
    plugin_name: str
    attributes: list[AttributeSchema] = []
    model_config = {"extra": "forbid"}

class PluginSchema(BaseModel):
    plugin: PluginData  # ← 外层包装
    model_config = {"extra": "forbid"}
```

---

## 🔄 转换流程

### 转换路径总览

```
                    parse_logstash_config()
    Logstash Text ─────────────────────────────→ AST
         ↑                                        │
         │                                        │ to_python()
         │                                        ↓
         │                                      dict
         │                                        │
         │                                        │ (自动转换)
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

**关键转换点：**

1. **Logstash ↔ AST**: 解析和生成
   - `parse_logstash_config()`: 解析 Logstash 文本为 AST
   - `ast.to_logstash()`: 从 AST 生成 Logstash 文本

2. **AST ↔ dict**: 简单数据转换
   - `ast.to_python()`: AST 转为 Python 字典
   - `ASTNode.from_python(dict)`: 从字典创建 AST

3. **AST ↔ Schema**: 类型安全转换
   - `ast.to_python(as_pydantic=True)`: AST 转为 Schema
   - `ASTNode.from_python(schema)`: 从 Schema 创建 AST

4. **Schema ↔ JSON**: 序列化
   - `schema.model_dump_json()`: Schema 序列化为 JSON
   - `Schema.model_validate_json()`: JSON 反序列化为 Schema

### 完整转换链

#### 正向转换（Logstash → JSON）

```
Logstash 文本
    ↓ parse_logstash_config()
AST 树形结构
    ↓ to_python(as_pydantic=True)
Pydantic Schema 对象
    ↓ model_dump_json()
JSON 文本
```

#### 反向转换（JSON → Logstash）

```
JSON 文本
    ↓ model_validate_json()
Pydantic Schema 对象
    ↓ from_python()
AST 树形结构
    ↓ to_logstash()
Logstash 文本
```

#### 完整往返示例

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

# 验证往返一致性
assert ast.to_python() == reconstructed_ast.to_python()
```

### 转换方法实现

#### AST → Schema

```python
class Plugin(ASTNode[Attribute]):
    def _to_pydantic_model(self) -> PluginSchema:
        return PluginSchema(
            source_text=self.get_source_text(),
            plugin_name=self.plugin_name,
            attributes=[
                attr.to_python(as_pydantic=True)
                for attr in self.children
            ]
        )
```

#### Schema → AST

```python
class PluginSchema(ASTNodeSchema):
    @classmethod
    def _from_pydantic(cls, schema: ASTNodeSchema) -> Plugin:
        attributes = [Attribute._from_pydantic(attr) for attr in schema.attributes]
        node = Plugin(schema.plugin_name, attributes)
        node._source_text_cache = schema.source_text
        return node
```

---

## 📦 模块结构

### 文件组织

```
logstash-parser/src/logstash_parser/
├── __init__.py              # 公开 API 导出
├── grammar.py               # 语法定义（pyparsing）
├── ast_nodes.py             # AST 节点定义 + 构建器函数
├── schemas.py               # Pydantic Schema 定义
└── py.typed                 # 类型提示标记
```

### 构建器函数

`ast_nodes.py` 包含用于 pyparsing 的构建器函数：

```python
def build_lsstring(toks: ParseResults) -> LSString:
    """从 ParseResults 构建 LSString 节点"""
    value = toks.as_list()[0]
    return LSString(value)

def build_plugin_node(s, loc, toks: ParseResults) -> Plugin:
    """从 ParseResults 构建 Plugin 节点，保存原始位置信息"""
    return Plugin(list(toks)[0][0], list(toks)[0][1], s=s, loc=loc)
```

**特点：**
- 构建器函数接收 `s`（原始字符串）和 `loc`（位置）参数
- 这些参数用于延迟计算 source_text
- 构建器函数在 `grammar.py` 中通过 `setParseAction` 注册

### 模块职责

| 模块 | 职责 | 主要内容 |
|------|------|----------|
| `grammar.py` | 语法定义 | pyparsing 规则、解析器元素 |
| `ast_nodes.py` | AST 实现 | 25 个 AST 节点类、转换方法 |
| `schemas.py` | Schema 定义 | 24 个 Schema 类、验证规则 |
| `__init__.py` | API 导出 | 公开接口、便捷函数 |

---

## 🎨 节点类型体系

### 节点分类

#### 1. 简单类型（6 个）
- `LSString` / `LSStringSchema` - 字符串
- `LSBareWord` / `LSBareWordSchema` - 裸词
- `Number` / `NumberSchema` - 数字
- `Boolean` / `BooleanSchema` - 布尔值
- `Regexp` / `RegexpSchema` - 正则表达式
- `SelectorNode` / `SelectorNodeSchema` - 字段选择器

#### 2. 数据结构（4 个）
- `Array` / `ArraySchema` - 数组
- `HashEntryNode` / `HashEntryNodeSchema` - 哈希条目
- `Hash` / `HashSchema` - 哈希表
- `Attribute` / `AttributeSchema` - 属性

#### 3. 插件（1 个）
- `Plugin` / `PluginSchema` - 插件配置

#### 4. 表达式（7 个）
- `CompareExpression` / `CompareExpressionSchema` - 比较表达式
- `RegexExpression` / `RegexExpressionSchema` - 正则表达式
- `InExpression` / `InExpressionSchema` - In 表达式
- `NotInExpression` / `NotInExpressionSchema` - Not In 表达式
- `NegativeExpression` / `NegativeExpressionSchema` - 否定表达式
- `BooleanExpression` / `BooleanExpressionSchema` - 布尔表达式
- `Expression` / `ExpressionSchema` - 表达式包装器

#### 5. 条件分支（4 个）
- `IfCondition` / `IfConditionSchema` - If 条件
- `ElseIfCondition` / `ElseIfConditionSchema` - Else If 条件
- `ElseCondition` / `ElseConditionSchema` - Else 条件
- `Branch` / `BranchSchema` - 分支

#### 6. 配置（2 个）
- `PluginSectionNode` / `PluginSectionSchema` - 插件段
- `Config` / `ConfigSchema` - 配置根节点

#### 7. 特殊（1 个）
- `RValue` - 右值包装器（无 Schema）

**总计**: 24 个 AST 节点类, 20 个 Schema 类（不包括 Data 类和类型别名）

**注意**: `ExpressionSchema` 是类型别名，不计入 Schema 类数量。

---

## 🔒 类型安全

### Generic 类型参数

AST 节点使用 Generic 类型参数提供类型安全：

```python
T = TypeVar("T", bound="ASTNode")
S = TypeVar("S", bound="ASTNodeSchema")

class ASTNode(Generic[T, S]):
    children: list[T]  # ← 子节点类型
    schema_class: type[S]  # ← 对应的 Schema 类型
```

**优势：**
- 类型检查器可以推断子节点类型
- 每个节点类明确指定其 Schema 类型
- 提供更好的 IDE 支持和类型提示

### 字段名类型识别

使用 snake_case 字段名作为类型标识：

```python
class PluginSchema(BaseModel):
    plugin: PluginData  # ← 字段名 "plugin" 标识这是 Plugin 类型
    model_config = {"extra": "forbid"}
```

### Union 类型

使用 Annotated 和 `discriminator=None` 实现类型区分：

```python
ValueSchema = Annotated[
    LSStringSchema
    | LSBareWordSchema
    | NumberSchema
    | ...,
    Field(discriminator=None)  # ← Pydantic 根据字段名自动识别
]
```

**优势：**
- 更简洁的 JSON 表示
- 字段名即类型,无需额外的 `node_type` 字段
- Pydantic 自动根据字段名进行类型识别

### Overload

使用 overload 提供准确的返回类型：

```python
@overload
def to_python(self, as_pydantic: Literal[True]) -> BaseModel: ...

@overload
def to_python(self, as_pydantic: Literal[False] = False) -> dict[str, Any]: ...
```

---

## 📊 性能考虑

### 解析性能
- ✅ 使用 pyparsing 高效解析
- ✅ 延迟计算 source_text
- ✅ 缓存解析结果

### 序列化性能
- ✅ Pydantic 优化的序列化
- ✅ 可选的 source_text 排除
- ✅ 增量序列化支持

### 内存使用
- ✅ 移除 parent 减少内存
- ✅ 延迟计算减少开销
- ✅ 共享不可变数据

---

## 🔄 向后兼容性

### 保证

- ✅ 现有 `to_python()` 调用返回 dict（默认行为）
- ✅ 现有 `to_logstash()` 方法不变
- ✅ 现有 `to_source()` 方法不变
- ✅ 现有 AST 结构不变（只是移除 parent）

### 迁移路径

```python
# 旧代码（仍然工作）
data = ast.to_python()

# 新代码（可选）
schema = ast.to_python(as_pydantic=True)
json_str = schema.model_dump_json()
```

---

## 🎯 设计原则

1. **职责分离**：AST 和 Schema 各司其职
2. **类型安全**：充分利用 Python 类型系统
3. **向后兼容**：不破坏现有 API
4. **性能优先**：优化关键路径
5. **易于使用**：简洁的 API 设计
6. **可扩展性**：易于添加新节点类型

---

## 📚 相关文档

- [API 参考](./API_REFERENCE.md)
- [使用指南](./USER_GUIDE.md)
- [测试指南](./TESTING.md)
- [更新日志](./CHANGELOG.md)
