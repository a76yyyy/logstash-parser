# 更新日志

本文档记录 Logstash Parser 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [0.3.0] - 2025-10-30

### 新增

#### Pydantic Schema 支持
- ✅ 添加完整的 Pydantic Schema 定义（24 个 Schema 类）
- ✅ 支持 AST ↔ Schema 双向转换
- ✅ 支持 Schema ↔ JSON 序列化/反序列化
- ✅ 使用 Literal 类型确保类型安全
- ✅ 使用 discriminator 实现 Union 类型区分

#### 转换方法
- ✅ `ASTNode.to_python(as_pydantic=True)` - 转换为 Pydantic Schema
- ✅ `ASTNode.from_python(data)` - 从 dict 或 Schema 创建 AST
- ✅ `Schema.model_dump_json()` - 序列化为 JSON
- ✅ `Schema.model_validate_json()` - 从 JSON 反序列化

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

### v0.4.0（计划中）
- [ ] 配置模板系统
- [ ] 配置片段合并
- [ ] 配置格式转换工具
- [ ] 配置可视化编辑器

### v0.5.0（计划中）
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
