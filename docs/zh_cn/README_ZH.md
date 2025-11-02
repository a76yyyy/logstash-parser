# Logstash Parser

[English](../../README.md) | 简体中文 | [文档索引](./README.md)

一个基于 [`pyparsing`](https://github.com/pyparsing/pyparsing) 的 Python Logstash 管道配置解析器。该工具将 Logstash 配置字符串解析为结构清晰的抽象语法树(AST),便于遍历、操作和在 Logstash 与 Python 表示之间进行转换。

---

## 特性

- **100% 语法兼容**: 完全符合 Logstash 官方 grammar.treetop 规范
- **全面测试**: 广泛的测试套件，高代码覆盖率
- 将 Logstash 管道配置字符串解析为清晰、可遍历的 AST
- 每个 AST 节点支持:
  - `.to_python()`: 将子树转换为 Python 原生数据结构（dict 或 Pydantic Schema）
  - `.to_logstash()`: 将子树转换回有效的 Logstash 配置字符串
  - `.to_source()`: 获取节点的原始源文本(保留格式)
- 支持完整的 Logstash 语法:
  - 插件配置(input/filter/output)
  - 条件分支(if/else if/else)
  - 数据类型(字符串、数字、布尔值、数组、哈希表)
  - 字段引用(selector)
  - 表达式(比较、正则、逻辑运算、in/not in)
- Pydantic Schema 支持，提供类型安全的序列化/反序列化
- 适用于构建需要分析、转换或生成 Logstash 配置的工具

---

## 安装

### 使用 UV (推荐)

```bash
cd /path/to/logstash-parser
uv pip install -e .
```

### 使用 pip

```bash
cd /path/to/logstash-parser
pip install -e .
```

---

## 快速开始

### 基本用法

```python
from logstash_parser import parse_logstash_config

# Logstash 配置示例
logstash_conf = """
filter {
  if [type] == "nginx" {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
  }
}
"""

# 解析配置（推荐）
ast = parse_logstash_config(logstash_conf)

# 转换为 Python 字典
python_dict = ast.to_python()
print(python_dict)

# 转换回 Logstash 配置
logstash_config = ast.to_logstash()
print(logstash_config)
```

### 完整示例

```python
from logstash_parser import parse_logstash_config

# 包含多个部分的完整配置
full_config = """
input {
  file {
    path => "/var/log/nginx/access.log"
    type => "nginx"
  }
}

filter {
  if [type] == "nginx" {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
    date {
      match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "nginx-%{+YYYY.MM.dd}"
  }
}
"""

# 解析
ast = parse_logstash_config(full_config)

# 访问特定部分
python_repr = ast.to_python()
print("Filter plugins:", python_repr.get('filter', []))
```

### 遍历 AST

```python
from logstash_parser import parse_logstash_config

logstash_conf = """
filter {
  mutate {
    add_field => { "foo" => "bar" }
  }
}
"""

ast = parse_logstash_config(logstash_conf)

# 遍历所有子节点
for section in ast.children:
    print(f"Section type: {section.plugin_type}")
    for plugin in section.children:
        print(f"  Plugin: {plugin.plugin_name}")
        for attr in plugin.children:
            print(f"    Attribute: {attr.name.to_python()} => {attr.value.to_python()}")
```

---

## AST 节点类型

所有 AST 节点都继承自 `ASTNode` 基类,并提供统一的 API:

### 核心节点

| 节点类型            | 说明                          | 示例               |
| ------------------- | ----------------------------- | ------------------ |
| `Config`            | 根节点,包含所有插件部分       | 整个配置文件       |
| `PluginSectionNode` | 插件部分(input/filter/output) | `filter { ... }`   |
| `Plugin`            | 插件定义                      | `grok { ... }`     |
| `Attribute`         | 插件属性                      | `match => { ... }` |
| `Branch`            | 条件分支                      | `if/else if/else`  |

### 数据类型节点

| 节点类型       | 说明         | 示例                       |
| -------------- | ------------ | -------------------------- |
| `LSString`     | 字符串       | `"message"` 或 `'message'` |
| `LSBareWord`   | 裸字(标识符) | `mutate`, `grok`           |
| `Number`       | 数字         | `123`, `45.67`             |
| `Boolean`      | 布尔值       | `true`, `false`            |
| `Array`        | 数组         | `[1, 2, 3]`                |
| `Hash`         | 哈希表       | `{ "key" => "value" }`     |
| `Regexp`       | 正则表达式   | `/pattern/`                |
| `SelectorNode` | 字段引用     | `[field][subfield]`        |

### 表达式节点

| 节点类型             | 说明          | 示例                         |
| -------------------- | ------------- | ---------------------------- |
| `CompareExpression`  | 比较表达式    | `[status] == 200`            |
| `RegexExpression`    | 正则匹配      | `[message] =~ /error/`       |
| `InExpression`       | in 表达式     | `[status] in [200, 201]`     |
| `NotInExpression`    | not in 表达式 | `[status] not in [400, 500]` |
| `BooleanExpression`  | 布尔表达式    | `expr1 and expr2`            |
| `NegativeExpression` | 否定表达式    | `![field]`                   |

### 条件节点

| 节点类型          | 说明         |
| ----------------- | ------------ |
| `IfCondition`     | if 条件      |
| `ElseIfCondition` | else if 条件 |
| `ElseCondition`   | else 条件    |

---

## API 参考

### ASTNode 基类方法

```python
class ASTNode:
    # 属性
    children: tuple[ASTNode, ...]  # 子节点元组（不可变）

    # 方法
    def to_python(self, as_pydantic: bool = False) -> dict | BaseModel:
        """转换为 Python 字典或 Pydantic Schema"""

    def to_logstash(self, indent: int = 0) -> str:
        """转换为 Logstash 配置字符串"""

    def to_source(self) -> str | int | float:
        """获取原始源文本(保留格式)"""

    def get_source_text(self) -> str | None:
        """获取节点的原始源文本（延迟求值）"""

    @classmethod
    def from_logstash(cls, config_text: str) -> ASTNode:
        """从 Logstash 配置字符串创建 AST"""

    @classmethod
    def from_python(cls, data: dict | BaseModel) -> ASTNode:
        """从 Python 字典或 Pydantic Schema 创建 AST"""

    def traverse(self):
        """递归遍历所有子节点"""
```

---

## 开发

### 项目结构

```Tree
logstash-parser/
├── src/logstash_parser/
│   ├── __init__.py       # PEG 类和解析动作
│   ├── grammar.py        # pyparsing 语法定义
│   ├── ast_nodes.py      # AST 节点类定义
│   ├── schemas.py        # Pydantic Schema 定义
│   └── py.typed          # 类型标注支持
├── tests/                # 测试套件（全面覆盖）
│   ├── conftest.py       # Pytest fixtures
│   ├── test_parser.py    # 解析器测试（包含 TestGrammarRuleFixes）
│   ├── test_ast_nodes.py # AST 节点测试
│   ├── test_conversions.py # 转换测试
│   ├── test_schemas.py   # Schema 测试
│   ├── test_integration.py # 集成测试
│   ├── test_from_logstash.py # from_logstash() 测试
│   └── test_helpers.py   # 测试工具
├── docs/                 # 文档
│   ├── TESTING.md        # 测试指南
│   ├── API_REFERENCE.md  # API 文档
│   ├── USER_GUIDE.md     # 使用指南
│   ├── ARCHITECTURE.md   # 架构设计
│   └── CHANGELOG.md      # 更新日志
├── scripts/
│   └── run_tests.sh      # 测试运行脚本
├── pyproject.toml        # 项目配置
├── Makefile              # 便捷命令
├── LICENSE               # MIT 许可证
├── README.md             # 英文文档（主文档）
└── docs/zh_cn/README_ZH.md # 中文文档(本文件)
```

### 依赖

- Python >= 3.10
- pyparsing >= 3.2.5

---

## 致谢

本解析器的语法定义参考了 [logstash-pipeline-parser](https://pypi.org/project/logstash-pipeline-parser/) 模块。

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
