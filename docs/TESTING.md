# Logstash Parser Testing Guide

## 📋 Table of Contents

- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Test Types](#test-types)
- [Writing Tests](#writing-tests)
- [Testing Best Practices](#testing-best-practices)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)

---

## Test Structure

```Tree
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── test_parser.py           # Parser tests (includes TestGrammarRuleFixes)
├── test_ast_nodes.py        # AST node tests
├── test_conversions.py      # Conversion method tests
├── test_schemas.py          # Pydantic Schema tests
├── test_integration.py      # Integration tests
├── test_to_source.py        # to_source() method tests
├── test_to_logstash.py      # to_logstash() method tests (includes regression tests)
├── test_from_python.py      # from_python() method tests
├── test_from_logstash.py    # from_logstash() method tests
├── test_error_handling.py   # Error handling tests
└── test_helpers.py          # Test helper utilities

Total: 11 test files

**Important Test Classes**:
- `TestGrammarRuleFixes` (test_parser.py) - Grammar rule fix tests
- `TestRegressionFixes` (test_to_logstash.py) - Regression tests with 9 subclasses:
  - `TestNotInExpressionFix` - NotInExpression format fix
  - `TestBranchIndentationFix` - Conditional branch indentation fix
  - `TestHashNestedFormatFix` - Hash nested format fix
  - `TestPluginNestedFormatFix` - Plugin nested format fix
  - `TestRegexpDuplicateSlashFix` - Regexp duplicate slash fix
  - `TestPluginSectionNewlineFix` - PluginSection newline fix
  - `TestBooleanExpressionParenthesesFix` - Boolean expression parentheses fix
  - `TestNegativeExpressionParenthesesFix` - Negative expression parentheses fix
  - `TestOperatorPrecedenceFix` - Operator precedence fix
  - `TestRoundtripConsistency` - Roundtrip consistency tests
```

---

## Running Tests

### Install Test Dependencies

```bash
# Using UV (recommended)
uv sync --group test

# Or using pip
pip install -e ".[test]"
```

### Using Makefile

```bash
# View all available commands
make help

# Run all tests
make test

# Run tests (verbose output)
make test-v

# Run tests with coverage report
make test-cov

# Quick test (no coverage)
make test-fast

# Run tests in parallel
make test-parallel
```

### Using pytest Directly

```bash
# Basic run
pytest

# Verbose output
pytest -v

# Show test coverage
pytest --cov

# Generate HTML coverage report
pytest --cov --cov-report=html
```

### Run Specific Tests

```bash
# Run single test file
pytest tests/test_parser.py

# Run single test class
pytest tests/test_parser.py::TestBasicParsing

# Run single test method
pytest tests/test_parser.py::TestBasicParsing::test_parse_simple_filter

# Run tests matching pattern
pytest -k "test_parse"
```

### Run Tests with Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run Tests in Parallel

```bash
# Use multiple CPU cores
pytest -n auto

# Use specified number of cores
pytest -n 4
```

---

## Test Coverage

### Current Coverage

Run `make test-cov` to view the latest coverage report.

**Coverage Goals**:

- **Overall Coverage**: > 90%
- **Core Module Coverage**: > 95%
  - `__init__.py`
  - `grammar.py`
  - `schemas.py`
  - `ast_nodes.py`

### View Coverage Report

```bash
# Generate coverage report
pytest --cov --cov-report=html

# Open report in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Configuration

Coverage configuration in `pyproject.toml`:

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

## Test Types

### 1. Unit Tests (`@pytest.mark.unit`)

Test individual functions or classes.

**Files**: `test_parser.py`, `test_ast_nodes.py`, `test_schemas.py`

**Example**:

```python
def test_lsstring_creation():
    """Test LSString node creation."""
    node = LSString('"hello world"')
    assert node.lexeme == '"hello world"'
    assert node.value == "hello world"
```

### 2. Integration Tests (`@pytest.mark.integration`)

Test integration of multiple components.

**Files**: `test_integration.py`

**Example**:

```python
@pytest.mark.integration
def test_full_roundtrip_workflow(full_config):
    """Test: Parse -> to_logstash -> Parse -> Compare."""
    ast1 = parse_logstash_config(full_config)
    logstash_str = ast1.to_logstash()
    ast2 = parse_logstash_config(logstash_str)
    assert ast1.to_python() == ast2.to_python()
```

### 3. Conversion Tests

Test AST conversion methods.

**Files**: `test_conversions.py`, `test_to_source.py`, `test_to_logstash.py`, `test_from_python.py`

**Coverage**:

- `to_python()` - AST → Python dict
- `to_python(as_pydantic=True)` - AST → Pydantic Schema
- `to_logstash()` - AST → Logstash configuration
- `to_source()` - Get original source text
- `from_python()` - Python dict/Schema → AST

### 4. Schema Tests

Test Pydantic Schema classes.

**Files**: `test_schemas.py`

**Coverage**:

- Schema creation and validation
- Schema serialization/deserialization
- Schema type checking
- Schema field validation

### 5. Error Handling Tests

Test error handling and edge cases.

**Files**: `test_error_handling.py`

**Coverage**:

- Parse errors
- Validation errors
- Edge cases
- Exception handling

---

## Writing Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Using Fixtures

Fixtures defined in `conftest.py`:

```python
def test_with_fixture(simple_filter_config):
    """Use predefined fixture."""
    ast = parse_logstash_config(simple_filter_config)
    assert ast is not None
```

### Available Fixtures

- `simple_filter_config` - Simple filter configuration
- `simple_input_config` - Simple input configuration
- `simple_output_config` - Simple output configuration
- `full_config` - Full configuration (input + filter + output)
- `conditional_config` - Conditional branch configuration
- `complex_expression_config` - Complex expression configuration
- `array_hash_config` - Array and hash configuration
- `number_boolean_config` - Number and boolean configuration
- `selector_config` - Field selector configuration
- `regexp_config` - Regular expression configuration

### Test Templates

#### Basic Test

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

#### Parameterized Test

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

#### Exception Test

```python
def test_invalid_config():
    """Test that invalid config raises error."""
    with pytest.raises(ParseError):
        parse_logstash_config("invalid config")
```

### Using Test Helpers

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

## Testing Best Practices

### 1. Test Independence

Each test should run independently, not depending on other tests' state.

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
    assert test_something_else(shared_config)  # Depends on test_feature_a
```

### 2. Clear Test Names

Test names should clearly describe what is being tested.

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

### 3. AAA Pattern

Use Arrange-Act-Assert pattern to organize tests.

```python
def test_feature():
    """Test description."""
    # Arrange - prepare test data
    config = create_config()

    # Act - execute tested operation
    result = parse_and_process(config)

    # Assert - verify results
    assert result == expected
```

### 4. Use Meaningful Assertion Messages

```python
# ✅ Good
assert len(plugins) == 3, f"Expected 3 plugins, got {len(plugins)}"

# ❌ Bad
assert len(plugins) == 3
```

### 5. Test Edge Cases

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

## Continuous Integration

### GitHub Actions Configuration Example

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

## Troubleshooting

### Test Failures

1. **View detailed output**:

   ```bash
   pytest -vv
   ```

2. **View full traceback**:

   ```bash
   pytest --tb=long
   ```

3. **Enter debug mode**:

   ```bash
   pytest --pdb
   ```

### Insufficient Coverage

1. **View uncovered lines**:

   ```bash
   pytest --cov --cov-report=term-missing
   ```

2. **Generate HTML report**:

   ```bash
   pytest --cov --cov-report=html
   open htmlcov/index.html
   ```

### Slow Tests

1. **View slowest tests**:

   ```bash
   pytest --durations=10
   ```

2. **Skip slow tests**:

   ```bash
   pytest -m "not slow"
   ```

---

## Contribution Guidelines

### Adding New Tests

1. Add tests in appropriate test file
2. Use clear test names and docstrings
3. Follow existing test patterns
4. Ensure tests pass: `pytest`
5. Check coverage: `pytest --cov`

### Adding New Fixtures

1. Add fixture in `conftest.py`
2. Add docstring explaining purpose
3. Use new fixture in tests

### Reporting Issues

If you find test issues, please provide:

- Test name
- Error message
- Reproduction steps
- Expected behavior

---

## Reference Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Coverage Plugin](https://pytest-cov.readthedocs.io/)
- [Pydantic Testing](https://docs.pydantic.dev/latest/concepts/testing/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

## Related Documentation

- [Architecture Design](./ARCHITECTURE.md)
- [API Reference](./API_REFERENCE.md)
- [User Guide](./USER_GUIDE.md)
- [Changelog](./CHANGELOG.md)

**中文文档 (Chinese)**:

- [测试指南 (中文)](./zh_cn/TESTING.md)
