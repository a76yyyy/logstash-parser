# 🧩 Logstash Parser

A Python-based Logstash pipeline configuration parser powered by [`pyparsing`](https://github.com/pyparsing/pyparsing). This tool parses Logstash config strings into an Abstract Syntax Tree (AST) with a consistent structure, making it easier to traverse, manipulate, and convert configurations between Logstash and Python representations.

---

## ✨ Features

* Parses Logstash pipeline configuration strings into a clean, traversable AST.
* Each AST node supports:

  * `.to_python()`: Convert the subtree into Python-native data structures.
  * `.to_logstash()`: Convert the subtree back into a valid Logstash config string.
* Suitable for building tools that need to analyze, transform, or generate Logstash configurations.

---

## Installation

```bash
pip install pyparsing
# Clone this repo
git clone https://github.com/yourusername/logstash-pipeline-parser.git
cd logstash-pipeline-parser
```

---

## Usage

```python
from peg import PEG 

logstash_conf = """
filter {
  if [type] == "nginx" {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
  }
}
"""

ast = PEG.config.parse_string(logstash_conf)[0]

# Convert to Python
print(ast.to_python())

# Convert back to Logstash config
print(ast.to_logstash())
```

---

## AST Structure

Each parsed node is an instance of `ASTNode` or a subclass. These nodes expose a consistent API:

```python
node.children     # List of child AST nodes
node.to_python()  # Recursively convert node and children to Python data
node.to_logstash()  # Recursively convert node and children to Logstash config string
```

---

## Credits:

To build this parser, I have taken references from [this](https://pypi.org/project/logstash-pipeline-parser/) module. Specifically, the grammar definition has been referenced from this package.
