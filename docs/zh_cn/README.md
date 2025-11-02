# Logstash Parser 文档

## 📚 文档索引

### 项目说明

- **[完整项目说明](./README_ZH.md)** - 项目介绍、特性、快速开始、API 参考

### 核心文档

- **[架构设计](./ARCHITECTURE.md)** - 系统架构和设计决策
- **[API 参考](./API_REFERENCE.md)** - 完整的 API 文档
- **[使用指南](./USER_GUIDE.md)** - 使用示例和最佳实践
- **[测试指南](./TESTING.md)** - 测试框架和最佳实践

### 更新日志

- **[更新日志](./CHANGELOG.md)** - 版本更新记录

---

## 🚀 快速开始

### 安装

```bash
uv add logstash-parser
```

### 基本使用

```python
from logstash_parser import parse_logstash_config

# 解析 Logstash 配置
config_text = """
filter {
    grok {
        match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
}
"""

# 解析为 AST（推荐使用 parse_logstash_config）
ast = parse_logstash_config(config_text)

# 转换为 dict
python_dict = ast.to_python()

# 转换为 Pydantic Schema
schema = ast.to_python(as_pydantic=True)

# 序列化为 JSON
json_str = schema.model_dump_json(indent=2)

# 生成 Logstash 配置
output = ast.to_logstash()
```

---

## 📖 文档说明

### 架构设计 (ARCHITECTURE.md)

包含：

- 系统架构概览
- 核心设计决策
- AST 与 Schema 的关系
- 转换流程说明

### API 参考 (API_REFERENCE.md)

包含：

- 所有公开 API
- AST 节点类型
- Schema 类型
- 转换方法
- 工具函数

### 使用指南 (USER_GUIDE.md)

包含：

- 基本用法
- 高级特性
- 最佳实践
- 常见问题
- 故障排查

### 测试指南 (TESTING.md)

包含：

- 测试结构和组织
- 运行测试的方法
- 测试覆盖率
- 编写测试的最佳实践
- 持续集成配置

### 更新日志 (CHANGELOG.md)

包含：

- 版本历史
- 功能变更
- 破坏性变更
- 迁移指南

---

## 🔗 相关资源

- [Logstash 官方文档](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [项目 GitHub](https://github.com/your-org/logstash-parser)

**English Documentation**:

- [English Documentation Index](../README.md) - Complete English documentation index

---

## 📝 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解详情。

---

## 🔧 文档维护指南

### 维护原则

为保持文档的准确性和时效性，请遵循以下原则：

#### 1. 避免硬编码动态数据

**❌ 不推荐**:

```markdown
- 测试覆盖率: 90.75%
- 测试用例数: 425 个
- 配置文件大小: 200+ 行
```

**✅ 推荐**:

```markdown
- 测试覆盖率: 运行 `make test-cov` 查看最新报告
- 测试用例: 全面的测试套件
- 支持复杂配置文件
```

#### 2. 使用推荐的 API

**示例代码应使用公开的推荐 API**:

**✅ 推荐**:

```python
from logstash_parser import parse_logstash_config

ast = parse_logstash_config(config_text)
```

**⚠️ 仅在说明底层实现时使用**:

```python
from logstash_parser.ast_nodes import Config

ast = Config.from_logstash(config_text)  # 底层方法
```

#### 3. 保持数据结构准确性

- 使用正确的类型注解（如 `tuple` 而非 `list`）
- 及时移除已废弃的特性说明
- 确保示例代码可以直接运行

#### 4. 定期检查清单

**每次发布前检查**:

- [ ] 所有示例代码可以运行
- [ ] API 文档与实际代码一致
- [ ] 没有硬编码的版本号或统计数据
- [ ] 中英文文档内容一致
- [ ] 链接都有效

**每月检查**:

- [ ] 测试指南反映最新的测试结构
- [ ] 架构文档反映最新的设计决策
- [ ] 更新日志记录了所有重要变更

### 文档更新流程

1. **代码变更时**:

   - 同步更新相关 API 文档
   - 更新受影响的示例代码
   - 在 CHANGELOG.md 中记录变更

2. **添加新特性时**:

   - 在 API_REFERENCE.md 中添加 API 说明
   - 在 USER_GUIDE.md 中添加使用示例
   - 在 ARCHITECTURE.md 中说明设计决策（如需要）
   - 更新 CHANGELOG.md

3. **修复 Bug 时**:
   - 更新相关文档中的错误说明
   - 在 CHANGELOG.md 中记录修复

### 常见问题

**Q: 如何避免文档过时？**

A:

- 使用动态查看方式（命令、工具）而非硬编码数字
- 定期运行文档中的示例代码验证
- 使用自动化工具检查文档链接

**Q: 如何保持中英文文档一致？**

A:

- 同时更新两个版本
- 使用相同的代码示例
- 定期对比检查

**Q: 何时更新 CHANGELOG？**

A:

- 每次合并 PR 时
- 发布新版本前整理
- 记录所有用户可见的变更

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](../LICENSE) 文件。
