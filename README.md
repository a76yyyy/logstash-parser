# Logstash Parser

English | [简体中文](README_ZH.md)

A Python-based Logstash pipeline configuration parser powered by [`pyparsing`](https://github.com/pyparsing/pyparsing). This tool parses Logstash config strings into a well-structured Abstract Syntax Tree (AST), making it easier to traverse, manipulate, and convert configurations between Logstash and Python representations.

---

## Features

* Parse Logstash pipeline configuration strings into a clean, traversable AST
* Each AST node supports:
  * `.to_python()`: Convert the subtree into Python-native data structures
  * `.to_logstash()`: Convert the subtree back into a valid Logstash config string
  * `.to_source()`: Get the original source text of the node (preserving formatting)
* Support for complete Logstash syntax:
  * Plugin configurations (input/filter/output)
  * Conditional branches (if/else if/else)
  * Data types (strings, numbers, booleans, arrays, hashes)
  * Field references (selectors)
  * Expressions (comparison, regex, logical operations)
* Suitable for building tools that need to analyze, transform, or generate Logstash configurations

---

## Installation

### Using UV (Recommended)

```bash
cd /path/to/logstash-parser
uv pip install -e .
```

### Using pip

```bash
cd /path/to/logstash-parser
pip install -e .
```

---

## Quick Start

### Basic Usage

```python
from logstash_parser import PEG
from logstash_parser.grammar import config

# Logstash configuration example
logstash_conf = """
filter {
  if [type] == "nginx" {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
  }
}
"""

# Parse configuration
ast = config.parse_string(logstash_conf)[0]

# Convert to Python dictionary
python_dict = ast.to_python()
print(python_dict)

# Convert back to Logstash configuration
logstash_config = ast.to_logstash()
print(logstash_config)
```

### Complete Example

```python
from logstash_parser import PEG
from logstash_parser.grammar import config

# Full configuration with multiple sections
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

# Parse
ast = config.parse_string(full_config)[0]

# Access specific sections
python_repr = ast.to_python()
print("Filter plugins:", python_repr.get('filter', []))
```

### Traversing the AST

```python
from logstash_parser.grammar import config

logstash_conf = """
filter {
  mutate {
    add_field => { "foo" => "bar" }
  }
}
"""

ast = config.parse_string(logstash_conf)[0]

# Traverse all child nodes
for section in ast.children:
    print(f"Section type: {section.plugin_type}")
    for plugin in section.children:
        print(f"  Plugin: {plugin.plugin_name}")
        for attr in plugin.children:
            print(f"    Attribute: {attr.name.to_python()} => {attr.value.to_python()}")
```

---

## AST Node Types

All AST nodes inherit from the `ASTNode` base class and provide a unified API:

### Core Nodes

| Node Type | Description | Example |
|-----------|-------------|---------|
| `Config` | Root node containing all plugin sections | Entire configuration file |
| `PluginSectionNode` | Plugin section (input/filter/output) | `filter { ... }` |
| `Plugin` | Plugin definition | `grok { ... }` |
| `Attribute` | Plugin attribute | `match => { ... }` |
| `Branch` | Conditional branch | `if/else if/else` |

### Data Type Nodes

| Node Type | Description | Example |
|-----------|-------------|---------|
| `LSString` | String | `"message"` or `'message'` |
| `LSBareWord` | Bare word (identifier) | `mutate`, `grok` |
| `Number` | Number | `123`, `45.67` |
| `Boolean` | Boolean value | `true`, `false` |
| `Array` | Array | `[1, 2, 3]` |
| `Hash` | Hash table | `{ "key" => "value" }` |
| `Regexp` | Regular expression | `/pattern/` |
| `SelectorNode` | Field reference | `[field][subfield]` |

### Expression Nodes

| Node Type | Description | Example |
|-----------|-------------|---------|
| `CompareExpression` | Comparison expression | `[status] == 200` |
| `RegexExpression` | Regex match | `[message] =~ /error/` |
| `InExpression` | In expression | `[status] in [200, 201]` |
| `NotInExpression` | Not in expression | `[status] not in [400, 500]` |
| `BooleanExpression` | Boolean expression | `expr1 and expr2` |
| `NegativeExpression` | Negation expression | `![field]` |

### Condition Nodes

| Node Type | Description |
|-----------|-------------|
| `IfCondition` | If condition |
| `ElseIfCondition` | Else if condition |
| `ElseCondition` | Else condition |

---

## API Reference

### ASTNode Base Class Methods

```python
class ASTNode:
    # Properties
    children: list[ASTNode]  # List of child nodes
    parent: ASTNode | None   # Parent node

    # Methods
    def to_python(self) -> Any:
        """Convert to Python native data structure"""

    def to_logstash(self, indent: int = 0) -> str:
        """Convert to Logstash configuration string"""

    def to_source(self) -> str | int | float:
        """Get original source text (preserving formatting)"""

    def get_source_text(self) -> str | None:
        """Get the original source text of the node"""

    def traverse(self):
        """Recursively traverse all child nodes"""
```

---

## Development

### Project Structure

```
logstash-parser/
├── src/logstash_parser/
│   ├── __init__.py       # PEG class and parse actions
│   ├── grammar.py        # pyparsing grammar definitions
│   ├── ast_nodes.py      # AST node class definitions
│   └── py.typed          # Type annotation support
├── pyproject.toml        # Project configuration
├── LICENSE               # MIT License
├── README.md             # This file
└── README_ZH.md          # Chinese documentation
```

### Dependencies

- Python >= 3.10
- pyparsing >= 3.2.5

---

## Credits

The grammar definition of this parser is referenced from the [logstash-pipeline-parser](https://pypi.org/project/logstash-pipeline-parser/) module.

---

## License

MIT License - See [LICENSE](LICENSE) file for details
