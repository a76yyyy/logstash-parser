# 更新日志

本文档记录 Logstash Parser 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### 新增

#### MethodCall 方法调用支持

- ✅ 添加 `MethodCall` AST 节点，支持解析方法调用（如 `sprintf("%{field}", arg1, arg2)`）
- ✅ 添加 `MethodCallSchema` 和 `MethodCallData` Schema 定义
- ✅ 支持嵌套方法调用（如 `upper(lower("TEST"))`）
- ✅ 支持多种参数类型：字符串、数字、选择器、数组、正则表达式
- ✅ 方法调用可用于条件表达式的右值位置
- ✅ 完整的测试覆盖（单元测试、集成测试、往返测试）

### 修复

#### 布尔表达式优先级

- ✅ 修复布尔运算符优先级：`and`/`nand` (3) > `xor` (2) > `or` (1)
- ✅ 使用 `pyparsing.infixNotation` 正确处理运算符优先级
- ✅ 确保 `A or B and C` 解析为 `A or (B and C)`，而非 `(A or B) and C`
- ✅ 支持显式括号标记（`has_explicit_parens`），保留用户添加的括号
- ✅ 根据优先级自动添加必要的括号

#### 条件语句格式化

- ✅ 修复 `if` 语句前导空格问题
- ✅ 修复 `else if` 和 `else` 与前面 `}` 的换行问题（应在同一行）
- ✅ 修复 Hash 和 Plugin 嵌套时的格式问题（开括号应在同一行）
- ✅ 修复 Regexp 重复斜杠问题（`lexeme` 已包含斜杠）
- ✅ 修复 NotInExpression 多余括号问题
- ✅ 修复 NegativeExpression 不必要的括号（简单选择器不需要括号）
- ✅ 修复 PluginSection 和 Config 的换行和空行问题

#### 注释处理

- ✅ 简化注释正则表达式，移除复杂的 `newline_or_eoi` 处理
- ✅ 使用 `r"[ \t]*#[^\r\n]*(?:\r?\n|$)"` 直接匹配注释模式

### 改进

#### 代码质量

- ✅ 添加全面的回归测试类（9 个测试类，覆盖所有修复的问题）
- ✅ 所有测试包含往返一致性验证
- ✅ 改进类型注解的准确性（使用具体类型而非 `ASTNode`）

---

## [0.4.0] - 2025-11-01

### 新增

#### 语法规则修复与测试

- ✅ 修复 `bareword` 规则：要求至少 2 个字符（符合 grammar.treetop 规范）
- ✅ 修复 `config` 规则：要求至少一个 plugin_section（符合 grammar.treetop 规范）
- ✅ 修复 `not_in_operator` 规则：正确处理空白符和注释（使用 `pp.Combine`）
- ✅ 添加 `TestGrammarRuleFixes` 测试类，包含 11 个新测试用例
- ✅ 全面的测试覆盖

### 重构

#### 简化 PluginSectionSchema 结构

- ✅ 移除 `PluginSectionData` 类
- ✅ `PluginSectionSchema` 直接使用 `dict[Literal["input", "filter", "output"], list[BranchOrPluginSchema]]`
- ✅ 更简洁的 JSON 格式: `{"plugin_section": {"filter": [...]}}`
- ✅ 类型更安全: 使用 `Literal` 限制 key 的取值
- ✅ 与 `AttributeSchema` 的 dict 风格保持一致

#### 移除 Expression 包装器节点

- ✅ 将 `ExpressionSchema` 从类改为类型别名（Union type）
- ✅ 移除 `Expression` AST 节点类
- ✅ 简化 AST 结构，减少不必要的嵌套层级
- ✅ `IfCondition` 和 `ElseIfCondition` 的 `expr` 字段现在直接使用具体的表达式类型
- ✅ `BooleanExpression` 的 `left` 和 `right` 现在直接是具体的表达式类型

#### 改进

- ✅ 更简洁的 AST 和 Schema 结构
- ✅ 与 Schema 定义更加一致
- ✅ 减少了不必要的嵌套层级
- ✅ 更好的类型安全性
- ✅ 完全符合 grammar.treetop 规范

#### Schema 类型定义

- ✅ 添加 `RValueSchema` TypeAlias，明确表达 `rvalue` 的类型范围
- ✅ 更新 `ExpressionSchema` 使用 `RValueSchema`（自动展开为成员类型）
- ✅ 添加注释说明与 Logstash 语法规则的对应关系
- ✅ 代码可维护性：如果需要修改 `rvalue` 类型，只需修改 `RValueSchema` 一处
- ✅ 语义清晰：明确表达 `rvalue` 在 Schema 层面的类型定义

### 文档改进

- ✅ 统一所有文档使用推荐的 `parse_logstash_config()` API
- ✅ 移除文档中硬编码的测试统计数据，改为动态查看方式
- ✅ 更正 `children` 类型说明为 `tuple`（不可变）
- ✅ 移除已废弃的 `parent` 属性引用
- ✅ 添加文档维护指南到 `docs/README.md`
- ✅ 保持中英文文档一致性

### 破坏性变更

⚠️ **Schema 变更**:

- 移除了 `PluginSectionData` 类
- `PluginSectionSchema.plugin_section` 从嵌套对象改为 dict 格式
- JSON 格式变化: `{"plugin_type": "filter", "children": [...]}` → `{"filter": [...]}`

⚠️ **API 变更**:

- 移除了 `Expression` 类，不能再使用 `Expression(condition)` 包装表达式
- `IfCondition` 和 `ElseIfCondition` 的 `expr` 参数类型从 `Expression | BooleanExpression` 改为具体的表达式类型联合
- `BooleanExpression` 的 `left` 和 `right` 不再是 `Expression` 类型

### 迁移指南

#### 从 0.3.x 迁移到 0.4.x

**1. PluginSectionSchema 变更**

**旧代码**:

```python
from logstash_parser.schemas import PluginSectionSchema, PluginSectionData

schema = PluginSectionSchema(
    plugin_section=PluginSectionData(
        plugin_type="filter",
        children=[...]
    )
)

# 访问
plugin_type = schema.plugin_section.plugin_type
children = schema.plugin_section.children
```

**新代码**:

```python
from logstash_parser.schemas import PluginSectionSchema

schema = PluginSectionSchema(
    plugin_section={
        "filter": [...]
    }
)

# 访问
plugin_type = next(iter(schema.plugin_section.keys()))  # "filter"
children = schema.plugin_section[plugin_type]
```

**JSON 格式变化**:

```python
# 旧格式
{
  "plugin_section": {
    "plugin_type": "filter",
    "children": [...]
  }
}

# 新格式
{
  "plugin_section": {
    "filter": [...]
  }
}
```

**2. Expression 包装器移除**

**旧代码**:

```python
from logstash_parser.ast_nodes import Expression, CompareExpression

# 创建条件时需要包装
condition = CompareExpression(...)
expr = Expression(condition)  # ← 需要包装
if_branch = IfCondition(expr, [...])
```

**新代码**:

```python
from logstash_parser.ast_nodes import CompareExpression

# 直接使用表达式，无需包装
condition = CompareExpression(...)
if_branch = IfCondition(condition, [...])  # ← 直接使用
```

**Schema 使用**:

```python
# 旧代码
schema = IfConditionSchema(
    if_condition=IfConditionData(
        expr=ExpressionSchema(  # ← 不能再这样使用
            condition=CompareExpressionSchema(...)
        )
    )
)

# 新代码
schema = IfConditionSchema(
    if_condition=IfConditionData(
        expr=CompareExpressionSchema(...)  # ← 直接使用具体类型
    )
)
```

---

## [0.3.0] - 2025-10-30

### 新增

#### Pydantic Schema 支持

- ✅ 添加完整的 Pydantic Schema 定义（21 个 Schema 类 + 9 个 Data 类）
- ✅ 支持 AST ↔ Schema 双向转换
- ✅ 支持 Schema ↔ JSON 序列化/反序列化
- ✅ 使用 snake_case 字段名作为类型标识
- ✅ 使用 `discriminator=None` 实现自动类型识别

#### 转换方法

- ✅ `ASTNode.to_python(as_pydantic=True)` - 转换为 Pydantic Schema
- ✅ `ASTNode.from_python(data)` - 从 dict 或 Schema 创建 AST
- ✅ `ASTNode.from_schema(schema)` - 从 Schema 创建 AST（替代 `_schema_to_node`）
- ✅ `Schema.model_dump_json()` - 序列化为 JSON
- ✅ `Schema.model_validate_json()` - 从 JSON 反序列化

#### 类型安全增强

- ✅ 为 `ASTNode.from_schema()` 添加 23 个 `@overload` 类型注解
- ✅ 支持所有 Schema 到 Node 的精确类型推断
- ✅ IDE 可以自动推断正确的返回类型
- ✅ 提供完整的类型安全保证

#### 文档

- ✅ 添加架构设计文档
- ✅ 添加完整的 API 参考
- ✅ 添加使用指南
- ✅ 添加示例和最佳实践

### 变更

#### 架构优化

- ✅ 移除 parent 链接，避免循环引用
- ✅ 优化 source_text 获取机制
- ✅ 改进类型提示和类型安全

#### API 增强

- ✅ `to_python()` 方法支持 `as_pydantic` 参数
- ✅ 统一的 `from_python()` 方法支持多种输入
- ✅ 所有 AST 节点添加 `schema_class` 属性
- ✅ 重构 `_schema_to_node` 为 `ASTNode.from_schema` 类方法

#### 代码重构

- ✅ 将模块级函数 `_schema_to_node` 重构为类方法 `ASTNode.from_schema`
- ✅ 更新所有内部调用点（22 处）使用新 API
- ✅ 提高代码的面向对象设计和一致性
- ✅ 减少全局命名空间污染

### 修复

- ✅ 修复 source_text 缓存问题
- ✅ 修复类型提示不准确的问题
- ✅ 修复序列化循环引用问题

### 性能

- ✅ 减少内存占用（移除 parent）
- ✅ 优化序列化性能
- ✅ 延迟计算 source_text

---

## [0.2.0] - 2025-10-29

### 新增

#### Logstash 源文本配置支持

- ✅ 支持在配置模型中使用 `source` 字段存储原生 Logstash 配置
- ✅ 添加 `LogstashPluginConfig` 基类
- ✅ 更新 `InputConfig`, `FilterConfig`, `OutputConfig` 继承新基类

#### 配置生成器增强

- ✅ 优先使用 `source` 字段生成配置
- ✅ 保持对传统字典格式的向后兼容
- ✅ 改进配置生成逻辑

#### 解析器工具

- ✅ 添加 `parse_logstash_config()` 便捷函数
- ✅ 改进错误处理和错误消息
- ✅ 统一解析入口

### 文档

- ✅ 添加 Logstash 源文本配置格式指南
- ✅ 添加配置格式更新日志
- ✅ 更新使用示例

---

## [0.1.0] - 2025-10-28

### 新增

#### 核心功能

- ✅ Logstash 配置解析器（基于 pyparsing）
- ✅ 完整的 AST 节点定义（25 个节点类型）
- ✅ AST → Logstash 配置生成
- ✅ AST → Python dict 转换

#### 节点类型

- ✅ 简单类型：LSString, LSBareWord, Number, Boolean, Regexp, SelectorNode
- ✅ 数据结构：Array, Hash, HashEntryNode, Attribute
- ✅ 插件：Plugin
- ✅ 表达式：CompareExpression, RegexExpression, InExpression, NotInExpression, NegativeExpression, BooleanExpression, Expression
- ✅ 条件分支：IfCondition, ElseIfCondition, ElseCondition, Branch
- ✅ 配置：PluginSectionNode, Config

#### 特性

- ✅ 支持所有 Logstash 语法元素
- ✅ 保留原始源文本
- ✅ 支持条件分支（if/else if/else）
- ✅ 支持复杂表达式
- ✅ 支持嵌套数据结构

#### 测试

- ✅ 单元测试覆盖
- ✅ 集成测试
- ✅ 类型检查（mypy）
- ✅ 代码风格检查（ruff）

---

## 版本说明

### 版本号规则

- **主版本号（Major）**：不兼容的 API 变更
- **次版本号（Minor）**：向后兼容的功能新增
- **修订号（Patch）**：向后兼容的问题修复

### 兼容性保证

#### 向后兼容

- ✅ 现有 `to_python()` 调用返回 dict（默认行为）
- ✅ 现有 `to_logstash()` 方法不变
- ✅ 现有 `to_source()` 方法不变
- ✅ 现有 AST 结构不变

#### 破坏性变更

- ⚠️ v0.3.0 移除了 parent 链接（内部实现，不影响公开 API）

---

## 迁移指南

### 从 0.2.x 迁移到 0.3.x

#### 无需修改的代码

```python
# 这些代码无需修改，继续工作
ast = parse_logstash_config(config_text)
python_dict = ast.to_python()
output_text = ast.to_logstash()
```

#### 新功能使用

```python
# 使用新的 Pydantic Schema 功能
schema = ast.to_python(as_pydantic=True)
json_str = schema.model_dump_json()

# 从 JSON 恢复
from logstash_parser.schemas import ConfigSchema
loaded_schema = ConfigSchema.model_validate_json(json_str)
reconstructed_ast = Config.from_python(loaded_schema)
```

#### 注意事项

1. **parent 链接已移除**

   - 如果你的代码依赖 `node.parent`，需要修改
   - 大多数情况下不需要 parent，使用 `_s` 和 `_loc` 即可

2. **source_text 不再序列化**
   - JSON 中不包含 source_text
   - 如需保留，使用 `model_dump(exclude_none=False)`

### 从 0.1.x 迁移到 0.2.x

#### 配置模型更新

```python
# 旧代码（仍然工作）
config = InputConfig(
    type="beats",
    port=5044
)

# 新代码（推荐）
config = InputConfig(
    source="""
    beats {
        port => 5044
    }
    """
)
```

---

## 未来计划

### v0.5.0（计划中）

- [ ] 配置模板系统
- [ ] 配置片段合并
- [ ] 配置格式转换工具
- [ ] 配置可视化编辑器

### v0.6.0（计划中）

- [ ] 配置版本管理
- [ ] 配置差异比较
- [ ] 配置优化建议
- [ ] 性能分析工具

### v1.0.0（长期目标）

- [ ] 稳定的公开 API
- [ ] 完整的文档
- [ ] 100% 测试覆盖
- [ ] 生产环境验证

---

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解详情。

### 更新 CHANGELOG 的最佳实践

1. **何时更新**:

   - 每次合并 PR 时，在 `[Unreleased]` 部分添加变更
   - 发布新版本前，将 `[Unreleased]` 改为版本号和日期
   - 创建新的空 `[Unreleased]` 部分

2. **如何分类**:

   - **新增**: 新功能、新特性
   - **变更**: 现有功能的改进
   - **修复**: Bug 修复
   - **破坏性变更**: 不兼容的 API 变更
   - **文档改进**: 文档更新
   - **性能**: 性能优化
   - **重构**: 代码重构（不影响功能）

3. **编写规范**:

   - 使用清晰、简洁的语言
   - 从用户角度描述变更
   - 对于破坏性变更，提供迁移指南
   - 使用 ✅ 标记已完成的项目
   - 使用 ⚠️ 标记需要注意的变更

4. **避免的做法**:

   - ❌ 不要硬编码具体的测试数量或覆盖率
   - ❌ 不要包含内部实现细节（除非影响用户）
   - ❌ 不要使用模糊的描述（如"一些改进"）
   - ❌ 不要忘记更新迁移指南

5. **示例**:

**✅ 好的变更描述**:

```markdown
### 新增

- ✅ 添加 `parse_logstash_config()` 便捷函数，提供更好的错误处理

### 破坏性变更

⚠️ **API 变更**:

- 移除了 `Expression` 类，直接使用具体的表达式类型
- 迁移指南: 将 `Expression(condition)` 改为直接使用 `condition`
```

**❌ 不好的变更描述**:

```markdown
### 变更

- 修复了一些问题
- 改进了性能
- 更新了测试（425 个测试，90.75% 覆盖率）
```

---

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](../LICENSE) 文件。

---

## 致谢

感谢所有贡献者和用户的支持！

特别感谢：

- [pyparsing](https://github.com/pyparsing/pyparsing) - 强大的解析库
- [Pydantic](https://github.com/pydantic/pydantic) - 优秀的数据验证库
- [Logstash](https://www.elastic.co/logstash) - 灵感来源

---

## 链接

- [GitHub 仓库](https://github.com/your-org/logstash-parser)
- [问题追踪](https://github.com/your-org/logstash-parser/issues)
- [文档](https://logstash-parser.readthedocs.io/)
- [PyPI](https://pypi.org/project/logstash-parser/)
