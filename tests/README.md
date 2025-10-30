# Logstash Parser 测试文档

## 📋 目录

- [测试结构](#测试结构)
- [运行测试](#运行测试)
- [测试覆盖](#测试覆盖)
- [测试类型](#测试类型)
- [编写测试](#编写测试)

---

## 测试结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # Pytest fixtures 和配置
├── test_parser.py           # 解析器测试
├── test_ast_nodes.py        # AST 节点测试
├── test_conversions.py      # 转换方法测试
├── test_schemas.py          # Pydantic Schema 测试
├── test_integration.py      # 集成测试
├── test_helpers.py          # 测试辅助工具
└── README.md                # 本文件
```

---

## 运行测试

### 安装测试依赖

```bash
# 使用 UV (推荐)
uv sync --group test

# 或使用 pip
pip install -e ".[test]"
```

### 运行所有测试

```bash
# 基本运行
pytest

# 详细输出
pytest -v

# 显示测试覆盖率
pytest --cov

# 生成 HTML 覆盖率报告
pytest --cov --cov-report=html
```

### 运行特定测试

```bash
# 运行单个测试文件
pytest tests/test_parser.py

# 运行单个测试类
pytest tests/test_parser.py::TestBasicParsing

# 运行单个测试方法
pytest tests/test_parser.py::TestBasicParsing::test_parse_simple_filter

# 运行匹配模式的测试
pytest -k "test_parse"
```

### 使用标记运行测试

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 排除慢速测试
pytest -m "not slow"
```

### 并行运行测试

```bash
# 使用多个 CPU 核心
pytest -n auto

# 使用指定数量的核心
pytest -n 4
```

---

## 测试覆盖

### 当前覆盖目标

- **总体覆盖率**: > 90%
- **核心模块覆盖率**: > 95%
  - `ast_nodes.py`
  - `schemas.py`
  - `__init__.py`

### 查看覆盖率报告

```bash
# 生成覆盖率报告
pytest --cov --cov-report=html

# 在浏览器中打开报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 覆盖率配置

覆盖率配置在 `pyproject.toml` 中：

```toml
[tool.coverage.run]
source = ["."]
branch = true

[tool.coverage.report]
precision = 2
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "pass",
    "raise ImportError",
    "if TYPE_CHECKING:",
    "@overload",
]
```

---

## 测试类型

### 1. 单元测试 (`@pytest.mark.unit`)

测试单个函数或类的功能。

**文件**: `test_parser.py`, `test_ast_nodes.py`, `test_schemas.py`

**示例**:
```python
def test_lsstring_creation():
    """Test LSString node creation."""
    node = LSString('"hello world"')
    assert node.lexeme == '"hello world"'
    assert node.value == "hello world"
```

### 2. 集成测试 (`@pytest.mark.integration`)

测试多个组件的集成。

**文件**: `test_integration.py`

**示例**:
```python
@pytest.mark.integration
def test_full_roundtrip_workflow(full_config):
    """Test: Parse -> to_logstash -> Parse -> Compare."""
    ast1 = parse_logstash_config(full_config)
    logstash_str = ast1.to_logstash()
    ast2 = parse_logstash_config(logstash_str)
    assert ast1.to_python() == ast2.to_python()
```

### 3. 转换测试

测试 AST 转换方法。

**文件**: `test_conversions.py`

**覆盖**:
- `to_python()` - AST → Python dict
- `to_python(as_pydantic=True)` - AST → Pydantic Schema
- `to_logstash()` - AST → Logstash 配置
- `to_source()` - 获取原始源文本
- `from_python()` - Python dict/Schema → AST

### 4. Schema 测试

测试 Pydantic Schema 类。

**文件**: `test_schemas.py`

**覆盖**:
- Schema 创建和验证
- Schema 序列化/反序列化
- Schema 类型检查
- Schema 字段验证

---

## 编写测试

### 测试命名规范

- 测试文件: `test_*.py`
- 测试类: `Test*`
- 测试方法: `test_*`

### 使用 Fixtures

在 `conftest.py` 中定义的 fixtures:

```python
def test_with_fixture(simple_filter_config):
    """Use predefined fixture."""
    ast = parse_logstash_config(simple_filter_config)
    assert ast is not None
```

### 可用的 Fixtures

- `simple_filter_config` - 简单 filter 配置
- `simple_input_config` - 简单 input 配置
- `simple_output_config` - 简单 output 配置
- `full_config` - 完整配置 (input + filter + output)
- `conditional_config` - 条件分支配置
- `complex_expression_config` - 复杂表达式配置
- `array_hash_config` - 数组和哈希配置
- `number_boolean_config` - 数字和布尔值配置
- `selector_config` - 字段选择器配置
- `regexp_config` - 正则表达式配置

### 测试模板

#### 基本测试

```python
def test_feature_name():
    """Test description."""
    # Arrange
    config = """
    filter {
        mutate {
            add_field => { "field" => "value" }
        }
    }
    """

    # Act
    ast = parse_logstash_config(config)
    result = ast.to_python()

    # Assert
    assert "filter" in result
```

#### 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    ('"hello"', "hello"),
    ("'world'", "world"),
])
def test_string_parsing(input, expected):
    """Test string parsing with different quotes."""
    node = LSString(input)
    assert node.value == expected
```

#### 异常测试

```python
def test_invalid_config():
    """Test that invalid config raises error."""
    with pytest.raises(ParseError):
        parse_logstash_config("invalid config")
```

### 使用测试辅助工具

```python
from tests.test_helpers import (
    assert_roundtrip_equal,
    assert_pydantic_roundtrip_equal,
    ConfigBuilder,
)

def test_with_helpers():
    """Test using helper functions."""
    # Use ConfigBuilder
    config = (
        ConfigBuilder()
        .add_input("beats", port=5044)
        .add_filter("mutate", add_field="test")
        .build()
    )

    # Assert roundtrip
    assert_roundtrip_equal(config)
    assert_pydantic_roundtrip_equal(config)
```

---

## 测试最佳实践

### 1. 测试独立性

每个测试应该独立运行，不依赖其他测试的状态。

```python
# ✅ Good
def test_feature_a():
    config = create_config()
    assert test_something(config)

def test_feature_b():
    config = create_config()
    assert test_something_else(config)

# ❌ Bad
shared_config = None

def test_feature_a():
    global shared_config
    shared_config = create_config()
    assert test_something(shared_config)

def test_feature_b():
    assert test_something_else(shared_config)  # 依赖 test_feature_a
```

### 2. 清晰的测试名称

测试名称应该清楚地描述测试内容。

```python
# ✅ Good
def test_parse_simple_filter_with_grok_plugin():
    """Test parsing a simple filter configuration with grok plugin."""
    pass

# ❌ Bad
def test_1():
    """Test something."""
    pass
```

### 3. AAA 模式

使用 Arrange-Act-Assert 模式组织测试。

```python
def test_feature():
    """Test description."""
    # Arrange - 准备测试数据
    config = create_config()

    # Act - 执行被测试的操作
    result = parse_and_process(config)

    # Assert - 验证结果
    assert result == expected
```

### 4. 使用有意义的断言消息

```python
# ✅ Good
assert len(plugins) == 3, f"Expected 3 plugins, got {len(plugins)}"

# ❌ Bad
assert len(plugins) == 3
```

### 5. 测试边界情况

```python
def test_empty_array():
    """Test parsing empty array."""
    node = Array([])
    assert len(node.children) == 0

def test_single_element_array():
    """Test parsing array with single element."""
    node = Array([LSString('"test"')])
    assert len(node.children) == 1

def test_large_array():
    """Test parsing array with many elements."""
    elements = [LSString(f'"item{i}"') for i in range(1000)]
    node = Array(elements)
    assert len(node.children) == 1000
```

---

## 持续集成

### GitHub Actions 配置示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --group test
      - name: Run tests
        run: pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 故障排查

### 测试失败

1. **查看详细输出**:
   ```bash
   pytest -vv
   ```

2. **查看完整的 traceback**:
   ```bash
   pytest --tb=long
   ```

3. **进入调试模式**:
   ```bash
   pytest --pdb
   ```

### 覆盖率不足

1. **查看未覆盖的行**:
   ```bash
   pytest --cov --cov-report=term-missing
   ```

2. **生成 HTML 报告**:
   ```bash
   pytest --cov --cov-report=html
   open htmlcov/index.html
   ```

### 慢速测试

1. **查看最慢的测试**:
   ```bash
   pytest --durations=10
   ```

2. **跳过慢速测试**:
   ```bash
   pytest -m "not slow"
   ```

---

## 贡献指南

### 添加新测试

1. 在适当的测试文件中添加测试
2. 使用清晰的测试名称和文档字符串
3. 遵循现有的测试模式
4. 确保测试通过: `pytest`
5. 检查覆盖率: `pytest --cov`

### 添加新 Fixture

1. 在 `conftest.py` 中添加 fixture
2. 添加文档字符串说明用途
3. 在测试中使用新 fixture

### 报告问题

如果发现测试问题，请提供:
- 测试名称
- 错误消息
- 重现步骤
- 预期行为

---

## 参考资源

- [Pytest 文档](https://docs.pytest.org/)
- [Pytest Coverage 插件](https://pytest-cov.readthedocs.io/)
- [Pydantic 测试](https://docs.pydantic.dev/latest/concepts/testing/)
- [Python 测试最佳实践](https://docs.python-guide.org/writing/tests/)

---

## 更新日志

### 2025-10-30
- ✅ 创建完整的测试框架
- ✅ 添加单元测试
- ✅ 添加集成测试
- ✅ 添加 Schema 测试
- ✅ 添加转换测试
- ✅ 添加测试辅助工具
- ✅ 配置测试覆盖率
- ✅ 添加测试文档
