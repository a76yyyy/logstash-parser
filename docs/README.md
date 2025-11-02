# Logstash Parser Documentation

## 📚 Documentation Index

### Project Overview

- **[Complete Project Overview](../README.md)** - Project introduction, features, quick start, API reference

### Core Documentation

- **[Architecture Design](./ARCHITECTURE.md)** - System architecture and design decisions
- **[API Reference](./API_REFERENCE.md)** - Complete API documentation
- **[User Guide](./USER_GUIDE.md)** - Usage examples and best practices
- **[Testing Guide](./TESTING.md)** - Testing framework and best practices

### Changelog

- **[Changelog](./CHANGELOG.md)** - Version history

---

## 🚀 Quick Start

### Installation

```bash
uv add logstash-parser
```

### Basic Usage

```python
from logstash_parser import parse_logstash_config

# Parse Logstash configuration
config_text = """
filter {
    grok {
        match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
}
"""

# Parse to AST (recommended to use parse_logstash_config)
ast = parse_logstash_config(config_text)

# Convert to dict
python_dict = ast.to_python()

# Convert to Pydantic Schema
schema = ast.to_python(as_pydantic=True)

# Serialize to JSON
json_str = schema.model_dump_json(indent=2)

# Generate Logstash configuration
output = ast.to_logstash()
```

---

## 📖 Documentation Description

### Architecture Design (ARCHITECTURE.md)

Contains:

- System architecture overview
- Core design decisions
- Relationship between AST and Schema
- Conversion flow explanation

### API Reference (API_REFERENCE.md)

Contains:

- All public APIs
- AST node types
- Schema types
- Conversion methods
- Utility functions

### User Guide (USER_GUIDE.md)

Contains:

- Basic usage
- Advanced features
- Best practices
- Common questions
- Troubleshooting

### Testing Guide (TESTING.md)

Contains:

- Test structure and organization
- Methods to run tests
- Test coverage
- Best practices for writing tests
- Continuous integration configuration

### Changelog (CHANGELOG.md)

Contains:

- Version history
- Feature changes
- Breaking changes
- Migration guides

---

## 🔗 Related Resources

- [Logstash Official Documentation](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Project GitHub](https://github.com/your-org/logstash-parser)

**中文文档 (Chinese Documentation)**:

- [中文文档索引](./zh_cn/README.md) - Complete Chinese documentation index

---

## 📝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

---

## 🔧 Documentation Maintenance Guide

### Maintenance Principles

To maintain documentation accuracy and timeliness, please follow these principles:

#### 1. Avoid Hardcoding Dynamic Data

**❌ Not Recommended**:

```markdown
- Test coverage: 90.75%
- Test cases: 425
- Config file size: 200+ lines
```

**✅ Recommended**:

```markdown
- Test coverage: Run `make test-cov` to view latest report
- Test cases: Comprehensive test suite
- Supports complex configuration files
```

#### 2. Use Recommended APIs

**Example code should use public recommended APIs**:

**✅ Recommended**:

```python
from logstash_parser import parse_logstash_config

ast = parse_logstash_config(config_text)
```

**⚠️ Only use when explaining low-level implementation**:

```python
from logstash_parser.ast_nodes import Config

ast = Config.from_logstash(config_text)  # Low-level method
```

#### 3. Maintain Data Structure Accuracy

- Use correct type annotations (e.g., `tuple` not `list`)
- Remove deprecated feature descriptions promptly
- Ensure example code can run directly

#### 4. Regular Checklist

**Before Each Release**:

- [ ] All example code can run
- [ ] API documentation matches actual code
- [ ] No hardcoded version numbers or statistics
- [ ] Chinese and English documentation are consistent
- [ ] All links are valid

**Monthly Check**:

- [ ] Testing guide reflects latest test structure
- [ ] Architecture documentation reflects latest design decisions
- [ ] Changelog records all important changes

### Documentation Update Process

1. **When Code Changes**:

   - Update related API documentation synchronously
   - Update affected example code
   - Record changes in CHANGELOG.md

2. **When Adding New Features**:

   - Add API description in API_REFERENCE.md
   - Add usage examples in USER_GUIDE.md
   - Explain design decisions in ARCHITECTURE.md (if needed)
   - Update CHANGELOG.md

3. **When Fixing Bugs**:
   - Update error descriptions in related documentation
   - Record fix in CHANGELOG.md

### Common Questions

**Q: How to avoid outdated documentation?**

A:

- Use dynamic viewing methods (commands, tools) instead of hardcoded numbers
- Regularly run example code in documentation for verification
- Use automated tools to check documentation links

**Q: How to keep Chinese and English documentation consistent?**

A:

- Update both versions simultaneously
- Use same code examples
- Regular comparison checks

**Q: When to update CHANGELOG?**

A:

- When merging each PR
- Before releasing new version
- Record all user-visible changes

---

## 📄 License

This project uses MIT License. See [LICENSE](../LICENSE) file for details.
