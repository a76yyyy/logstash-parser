# Logstash Parser 使用指南

## 📋 目录

- [快速开始](#快速开始)
- [基本用法](#基本用法)
- [高级特性](#高级特性)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)
- [故障排查](#故障排查)

---

## 快速开始

### 安装

```bash
uv add logstash-parser
```

### 第一个示例

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

ast = parse_logstash_config(config_text)
print(ast.to_logstash())
```

---

## 基本用法

### 1. 解析配置

```python
from logstash_parser import parse_logstash_config

config_text = """
input {
    beats {
        port => 5044
        host => "0.0.0.0"
    }
}

filter {
    if [type] == "nginx" {
        grok {
            match => { "message" => "%{COMBINEDAPACHELOG}" }
        }
    }
}

output {
    elasticsearch {
        hosts => ["localhost:9200"]
        index => "logs-%{+YYYY.MM.dd}"
    }
}
"""

# 解析为 AST
ast = parse_logstash_config(config_text)
```

### 2. 转换为 Python 字典

```python
# 转换为 dict（默认行为）
python_dict = ast.to_python()

print(python_dict)
# {
#     "input": [...],
#     "filter": [...],
#     "output": [...]
# }
```

### 3. 转换为 Pydantic Schema

```python
# 转换为 Pydantic Schema
schema = ast.to_python(as_pydantic=True)

print(type(schema))  # <class 'ConfigSchema'>
```

### 4. 序列化为 JSON

```python
# 序列化为 JSON
json_str = schema.model_dump_json(indent=2)

print(json_str)
# {
#   "config": [
#     {
#       "plugin_section": {
#         "filter": [...]
#       }
#     }
#   ]
# }
```

**注意**: JSON 使用 snake_case 字段名,结构更简洁。

### 5. 从 JSON 反序列化

```python
from logstash_parser.schemas import ConfigSchema

# 从 JSON 反序列化
loaded_schema = ConfigSchema.model_validate_json(json_str)
```

### 6. 转换回 AST

```python
from logstash_parser.ast_nodes import Config

# 从 Schema 转换回 AST
reconstructed_ast = Config.from_python(loaded_schema)
```

### 7. 生成 Logstash 配置

```python
# 生成 Logstash 配置文本
output_text = reconstructed_ast.to_logstash()

print(output_text)
```

---

## 高级特性

### 1. 遍历 AST

```python
def traverse_ast(node, depth=0):
    """递归遍历 AST"""
    indent = "  " * depth
    print(f"{indent}{type(node).__name__}")

    if hasattr(node, 'children'):
        for child in node.children:
            traverse_ast(child, depth + 1)

traverse_ast(ast)
```

### 2. 查找特定节点

```python
def find_plugins(node, plugin_name):
    """查找特定名称的插件"""
    from logstash_parser.ast_nodes import Plugin

    plugins = []

    if isinstance(node, Plugin) and node.plugin_name == plugin_name:
        plugins.append(node)

    if hasattr(node, 'children'):
        for child in node.children:
            plugins.extend(find_plugins(child, plugin_name))

    return plugins

# 查找所有 grok 插件
grok_plugins = find_plugins(ast, "grok")
```

### 3. 修改 AST

```python
from logstash_parser.ast_nodes import (
    Plugin, Attribute, LSBareWord, LSString,
    Hash, HashEntryNode
)

# 创建新插件
new_plugin = Plugin(
    "mutate",
    [
        Attribute(
            LSBareWord("add_field"),
            Hash([
                HashEntryNode(
                    LSString('"new_field"'),
                    LSString('"value"')
                )
            ])
        )
    ]
)

# 添加到 filter 段
for section in ast.children:
    if section.plugin_type == "filter":
        section.children.append(new_plugin)

# 生成更新后的配置
updated_config = ast.to_logstash()
print(updated_config)
```

### 4. 条件表达式处理

```python
from logstash_parser.ast_nodes import (
    Branch, IfCondition, ElseCondition,
    CompareExpression, SelectorNode, LSString
)

# 创建条件分支
condition = CompareExpression(
    SelectorNode("[type]"),
    "==",
    LSString('"nginx"')
)

# 直接使用表达式，无需包装
if_branch = IfCondition(
    condition,
    [grok_plugin]
)

else_branch = ElseCondition([mutate_plugin])

branch = Branch(if_branch, [], else_branch)

# 添加到 filter 段
for section in ast.children:
    if section.plugin_type == "filter":
        section.children.append(branch)
```

### 5. 验证配置

```python
from pydantic import ValidationError

try:
    schema = ConfigSchema.model_validate(data)
    print("✅ 配置有效")
except ValidationError as e:
    print(f"❌ 配置无效:")
    for error in e.errors():
        print(f"  - {error['loc']}: {error['msg']}")
```

### 6. 部分序列化

```python
# 包含 source_text
full_data = schema.model_dump(exclude_none=False)

# 排除 source_text（默认）
minimal_data = schema.model_dump()

# 只序列化特定字段
partial_data = schema.model_dump(include={'node_type', 'children'})
```

### 7. 生成 JSON Schema

```python
# 生成 JSON Schema（用于文档或验证）
json_schema = ConfigSchema.model_json_schema()

import json
print(json.dumps(json_schema, indent=2))
```

---

## 最佳实践

### 1. 错误处理

```python
from logstash_parser import parse_logstash_config, ParseError

try:
    ast = parse_logstash_config(config_text)
except ParseError as e:
    print(f"解析失败: {e}")
    # 处理错误
```

### 2. 类型检查

```python
from logstash_parser.ast_nodes import Plugin, Branch

for child in section.children:
    if isinstance(child, Plugin):
        print(f"插件: {child.plugin_name}")
    elif isinstance(child, Branch):
        print("分支")
```

### 3. 使用 Schema 验证

```python
# 在接收外部数据时使用 Schema 验证
def load_config(json_str: str):
    try:
        schema = ConfigSchema.model_validate_json(json_str)
        return Config.from_python(schema)
    except ValidationError as e:
        raise ValueError(f"无效的配置: {e}")
```

### 4. 保留源文本

```python
# 解析时保留源文本
ast = parse_logstash_config(config_text)

# 获取源文本
source = ast.get_source_text()
if source:
    print(f"原始文本: {source}")
```

### 5. 增量构建配置

```python
from logstash_parser.ast_nodes import Config, PluginSectionNode

# 创建空配置
config = Config([])

# 添加 input 段
input_section = PluginSectionNode("input", [beats_plugin])
config.children.append(input_section)

# 添加 filter 段
filter_section = PluginSectionNode("filter", [grok_plugin])
config.children.append(filter_section)

# 添加 output 段
output_section = PluginSectionNode("output", [es_plugin])
config.children.append(output_section)
```

### 6. 配置合并

```python
def merge_configs(config1, config2):
    """合并两个配置"""
    merged = Config([])

    # 合并各个段
    for section_type in ["input", "filter", "output"]:
        sections1 = [s for s in config1.children if s.plugin_type == section_type]
        sections2 = [s for s in config2.children if s.plugin_type == section_type]

        if sections1 or sections2:
            merged_section = PluginSectionNode(section_type, [])
            for s in sections1 + sections2:
                merged_section.children.extend(s.children)
            merged.children.append(merged_section)

    return merged
```

---

## 常见问题

### Q1: 如何处理复杂的条件表达式？

**A:** 使用 `BooleanExpression` 组合多个条件：

```python
from logstash_parser.ast_nodes import BooleanExpression

# [type] == "nginx" and [status] == 200
condition = BooleanExpression(
    CompareExpression(SelectorNode("[type]"), "==", LSString('"nginx"')),
    "and",
    CompareExpression(SelectorNode("[status]"), "==", Number(200))
)
```

### Q2: 如何处理嵌套的哈希表？

**A:** 递归创建 `Hash` 和 `HashEntryNode`：

```python
nested_hash = Hash([
    HashEntryNode(
        LSString('"outer"'),
        Hash([
            HashEntryNode(
                LSString('"inner"'),
                LSString('"value"')
            )
        ])
    )
])
```

### Q3: 如何验证生成的配置是否正确？

**A:** 重新解析生成的配置：

```python
# 生成配置
output_text = ast.to_logstash()

# 重新解析
reparsed_ast = parse_logstash_config(output_text)

# 比较结构
assert ast.to_python() == reparsed_ast.to_python()
```

### Q4: 如何处理大型配置文件？

**A:** 使用流式处理或分段处理：

```python
# 分段解析
sections = config_text.split('\n\n')
for section in sections:
    if section.strip():
        try:
            ast = parse_logstash_config(section)
            # 处理每个段
        except ParseError:
            continue
```

### Q5: 如何自定义序列化格式？

**A:** 使用 Pydantic 的序列化选项：

```python
# 自定义序列化
json_str = schema.model_dump_json(
    indent=2,
    exclude_none=True,
    by_alias=True
)
```

---

## 故障排查

### 问题 1: 解析失败

**症状：** `ParseError: Failed to parse configuration`

**解决方案：**
1. 检查配置语法是否正确
2. 确保引号匹配
3. 检查括号是否闭合
4. 验证操作符是否正确

```python
# 调试解析
try:
    ast = parse_logstash_config(config_text)
except ParseError as e:
    print(f"解析错误: {e}")
    # 逐行检查
    for i, line in enumerate(config_text.split('\n'), 1):
        print(f"{i}: {line}")
```

### 问题 2: 序列化失败

**症状：** `ValidationError` 或序列化错误

**解决方案：**
1. 检查数据类型是否正确
2. 确保必填字段存在
3. 验证字段值是否有效

```python
# 调试序列化
try:
    json_str = schema.model_dump_json()
except Exception as e:
    print(f"序列化错误: {e}")
    # 检查 schema
    print(schema.model_dump())
```

### 问题 3: 类型错误

**症状：** `TypeError` 或类型不匹配

**解决方案：**
1. 使用类型检查
2. 验证节点类型
3. 使用 isinstance 检查

```python
# 类型检查
from logstash_parser.ast_nodes import Plugin

if isinstance(node, Plugin):
    print(f"插件名: {node.plugin_name}")
else:
    print(f"不是插件节点: {type(node)}")
```

### 问题 4: 内存占用过高

**症状：** 处理大型配置时内存占用高

**解决方案：**
1. 使用流式处理
2. 及时释放不需要的对象
3. 避免保留完整的 source_text

```python
# 不保留 source_text
schema = ast.to_python(as_pydantic=True)
json_str = schema.model_dump_json(exclude={'source_text'})
```

### 问题 5: 性能问题

**症状：** 解析或序列化速度慢

**解决方案：**
1. 使用缓存
2. 批量处理
3. 避免重复解析

```python
# 使用缓存
from functools import lru_cache

@lru_cache(maxsize=128)
def parse_cached(config_text):
    return parse_logstash_config(config_text)
```

---

## 示例集合

### 示例 1: 完整的转换链

```python
from logstash_parser import parse_logstash_config
from logstash_parser.schemas import ConfigSchema
from logstash_parser.ast_nodes import Config

# 1. 解析
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

# 验证
assert ast.to_python() == reconstructed_ast.to_python()
```

### 示例 2: 配置模板

```python
def create_grok_filter(pattern):
    """创建 grok filter 模板"""
    return Plugin(
        "grok",
        [
            Attribute(
                LSBareWord("match"),
                Hash([
                    HashEntryNode(
                        LSString('"message"'),
                        LSString(f'"{pattern}"')
                    )
                ])
            )
        ]
    )

# 使用模板
nginx_filter = create_grok_filter("%{COMBINEDAPACHELOG}")
syslog_filter = create_grok_filter("%{SYSLOGLINE}")
```

### 示例 3: 配置验证器

```python
def validate_config(config_text):
    """验证 Logstash 配置"""
    try:
        # 解析
        ast = parse_logstash_config(config_text)

        # 转换为 Schema（触发验证）
        schema = ast.to_python(as_pydantic=True)

        # 检查必要的段
        sections = {s.plugin_type for s in schema.children}
        if 'input' not in sections:
            return False, "缺少 input 段"
        if 'output' not in sections:
            return False, "缺少 output 段"

        return True, "配置有效"
    except Exception as e:
        return False, str(e)

# 使用
is_valid, message = validate_config(config_text)
print(f"{'✅' if is_valid else '❌'} {message}")
```

---

## 相关文档

- [架构设计](./ARCHITECTURE.md)
- [API 参考](./API_REFERENCE.md)
- [测试指南](./TESTING.md)
- [更新日志](./CHANGELOG.md)
