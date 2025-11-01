# Logstash Parser 文档

## 📚 文档索引

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

# 解析为 AST
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

---

## 📝 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解详情。

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](../LICENSE) 文件。
