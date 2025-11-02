# Changelog

This document records all important changes to Logstash Parser.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

#### MethodCall Support

- ✅ Added `MethodCall` AST node, supports parsing method calls (e.g., `sprintf("%{field}", arg1, arg2)`)
- ✅ Added `MethodCallSchema` and `MethodCallData` Schema definitions
- ✅ Supports nested method calls (e.g., `upper(lower("TEST"))`)
- ✅ Supports multiple argument types: strings, numbers, selectors, arrays, regular expressions
- ✅ Method calls can be used in rvalue position of conditional expressions
- ✅ Complete test coverage (unit tests, integration tests, roundtrip tests)

### Fixed

#### Boolean Expression Precedence

- ✅ Fixed boolean operator precedence: `and`/`nand` (3) > `xor` (2) > `or` (1)
- ✅ Use `pyparsing.infixNotation` to correctly handle operator precedence
- ✅ Ensure `A or B and C` parses as `A or (B and C)`, not `(A or B) and C`
- ✅ Support explicit parentheses marker (`has_explicit_parens`), preserve user-added parentheses
- ✅ Automatically add necessary parentheses based on precedence

#### Conditional Statement Formatting

- ✅ Fixed `if` statement leading space issue
- ✅ Fixed `else if` and `else` newline issue with preceding `}` (should be on same line)
- ✅ Fixed Hash and Plugin nested format issue (opening bracket should be on same line)
- ✅ Fixed Regexp duplicate slash issue (`lexeme` already includes slashes)
- ✅ Fixed NotInExpression extra parentheses issue
- ✅ Fixed NegativeExpression unnecessary parentheses (simple selectors don't need parentheses)
- ✅ Fixed PluginSection and Config newline and blank line issues

#### Comment Handling

- ✅ Simplified comment regex, removed complex `newline_or_eoi` handling
- ✅ Use `r"[ \t]*#[^\r\n]*(?:\r?\n|$)"` to directly match comment pattern

### Improved

#### Code Quality

- ✅ Added comprehensive regression test classes (9 test classes covering all fixed issues)
- ✅ All tests include roundtrip consistency verification
- ✅ Improved type annotation accuracy (use concrete types instead of `ASTNode`)

---

## [0.4.0] - 2025-11-01

### Added

#### Grammar Rule Fixes and Tests

- ✅ Fixed `bareword` rule: requires at least 2 characters (complies with grammar.treetop specification)
- ✅ Fixed `config` rule: requires at least one plugin_section (complies with grammar.treetop specification)
- ✅ Fixed `not_in_operator` rule: correctly handles whitespace and comments (using `pp.Combine`)
- ✅ Added `TestGrammarRuleFixes` test class with 11 new test cases
- ✅ Comprehensive test coverage

### Refactored

#### Simplified PluginSectionSchema Structure

- ✅ Removed `PluginSectionData` class
- ✅ `PluginSectionSchema` directly uses `dict[Literal["input", "filter", "output"], list[BranchOrPluginSchema]]`
- ✅ More concise JSON format: `{"plugin_section": {"filter": [...]}}`
- ✅ Type-safer: uses `Literal` to restrict key values
- ✅ Consistent with `AttributeSchema`'s dict style

#### Removed Expression Wrapper Node

- ✅ Changed `ExpressionSchema` from class to type alias (Union type)
- ✅ Removed `Expression` AST node class
- ✅ Simplified AST structure, reduced unnecessary nesting levels
- ✅ `IfCondition` and `ElseIfCondition`'s `expr` field now directly uses concrete expression types
- ✅ `BooleanExpression`'s `left` and `right` now directly use concrete expression types

#### Improvements

- ✅ More concise AST and Schema structure
- ✅ More consistent with Schema definitions
- ✅ Reduced unnecessary nesting levels
- ✅ Better type safety
- ✅ Fully complies with grammar.treetop specification

#### Schema Type Definitions

- ✅ Added `RValueSchema` TypeAlias, clearly expresses `rvalue` type range
- ✅ Updated `ExpressionSchema` to use `RValueSchema` (automatically expands to member types)
- ✅ Added comments explaining correspondence with Logstash grammar rules
- ✅ Code maintainability: if `rvalue` type needs modification, only need to modify `RValueSchema` in one place
- ✅ Semantic clarity: clearly expresses `rvalue` type definition at Schema level

### Documentation Improvements

- ✅ Unified all documentation to use recommended `parse_logstash_config()` API
- ✅ Removed hardcoded test statistics from documentation, changed to dynamic viewing methods
- ✅ Corrected `children` type description to `tuple` (immutable)
- ✅ Removed references to deprecated `parent` attribute
- ✅ Added documentation maintenance guide to `docs/README.md`
- ✅ Maintained consistency between Chinese and English documentation

### Breaking Changes

⚠️ **Schema Changes**:

- Removed `PluginSectionData` class
- `PluginSectionSchema.plugin_section` changed from nested object to dict format
- JSON format change: `{"plugin_type": "filter", "children": [...]}` → `{"filter": [...]}`

⚠️ **API Changes**:

- Removed `Expression` class, can no longer use `Expression(condition)` to wrap expressions
- `IfCondition` and `ElseIfCondition`'s `expr` parameter type changed from `Expression | BooleanExpression` to union of concrete expression types
- `BooleanExpression`'s `left` and `right` are no longer `Expression` type

### Migration Guide

#### Migrating from 0.3.x to 0.4.x

**1. PluginSectionSchema Changes**

**Old Code**:

```python
from logstash_parser.schemas import PluginSectionSchema, PluginSectionData

schema = PluginSectionSchema(
    plugin_section=PluginSectionData(
        plugin_type="filter",
        children=[...]
    )
)

# Access
plugin_type = schema.plugin_section.plugin_type
children = schema.plugin_section.children
```

**New Code**:

```python
from logstash_parser.schemas import PluginSectionSchema

schema = PluginSectionSchema(
    plugin_section={
        "filter": [...]
    }
)

# Access
plugin_type = next(iter(schema.plugin_section.keys()))  # "filter"
children = schema.plugin_section[plugin_type]
```

**JSON Format Change**:

```python
# Old format
{
  "plugin_section": {
    "plugin_type": "filter",
    "children": [...]
  }
}

# New format
{
  "plugin_section": {
    "filter": [...]
  }
}
```

**2. Expression Wrapper Removal**

**Old Code**:

```python
from logstash_parser.ast_nodes import Expression, CompareExpression

# Need to wrap when creating condition
condition = CompareExpression(...)
expr = Expression(condition)  # ← Need wrapping
if_branch = IfCondition(expr, [...])
```

**New Code**:

```python
from logstash_parser.ast_nodes import CompareExpression

# Use expression directly, no wrapping needed
condition = CompareExpression(...)
if_branch = IfCondition(condition, [...])  # ← Use directly
```

**Schema Usage**:

```python
# Old code
schema = IfConditionSchema(
    if_condition=IfConditionData(
        expr=ExpressionSchema(  # ← Can't use this way anymore
            condition=CompareExpressionSchema(...)
        )
    )
)

# New code
schema = IfConditionSchema(
    if_condition=IfConditionData(
        expr=CompareExpressionSchema(...)  # ← Use concrete type directly
    )
)
```

---

## [0.3.0] - 2025-10-30

### Added

#### Pydantic Schema Support

- ✅ Added complete Pydantic Schema definitions (21 Schema classes + 9 Data classes)
- ✅ Support AST ↔ Schema bidirectional conversion
- ✅ Support Schema ↔ JSON serialization/deserialization
- ✅ Use snake_case field names as type identifiers
- ✅ Use `discriminator=None` for automatic type identification

#### Conversion Methods

- ✅ `ASTNode.to_python(as_pydantic=True)` - Convert to Pydantic Schema
- ✅ `ASTNode.from_python(data)` - Create AST from dict or Schema
- ✅ `ASTNode.from_schema(schema)` - Create AST from Schema (replaces `_schema_to_node`)
- ✅ `Schema.model_dump_json()` - Serialize to JSON
- ✅ `Schema.model_validate_json()` - Deserialize from JSON

#### Type Safety Enhancement

- ✅ Added 23 `@overload` type annotations for `ASTNode.from_schema()`
- ✅ Support precise type inference for all Schema to Node mappings
- ✅ IDE can automatically infer correct return type
- ✅ Provide complete type safety guarantee

#### Documentation

- ✅ Added architecture design documentation
- ✅ Added complete API reference
- ✅ Added user guide
- ✅ Added examples and best practices

### Changed

#### Architecture Optimization

- ✅ Removed parent link, avoid circular references
- ✅ Optimized source_text retrieval mechanism
- ✅ Improved type hints and type safety

#### API Enhancement

- ✅ `to_python()` method supports `as_pydantic` parameter
- ✅ Unified `from_python()` method supports multiple inputs
- ✅ All AST nodes added `schema_class` attribute
- ✅ Refactored `_schema_to_node` to `ASTNode.from_schema` class method

#### Code Refactoring

- ✅ Refactored module-level function `_schema_to_node` to class method `ASTNode.from_schema`
- ✅ Updated all internal call sites (22 locations) to use new API
- ✅ Improved object-oriented design and consistency
- ✅ Reduced global namespace pollution

### Fixed

- ✅ Fixed source_text caching issues
- ✅ Fixed inaccurate type hints
- ✅ Fixed serialization circular reference issues

### Performance

- ✅ Reduced memory usage (removed parent)
- ✅ Optimized serialization performance
- ✅ Lazy source_text computation

---

## [0.2.0] - 2025-10-29

### Added

#### Logstash Source Text Configuration Support

- ✅ Support using `source` field in configuration models to store native Logstash configuration
- ✅ Added `LogstashPluginConfig` base class
- ✅ Updated `InputConfig`, `FilterConfig`, `OutputConfig` to inherit new base class

#### Configuration Generator Enhancement

- ✅ Prioritize using `source` field to generate configuration
- ✅ Maintain backward compatibility with traditional dict format
- ✅ Improved configuration generation logic

#### Parser Tools

- ✅ Added `parse_logstash_config()` convenience function
- ✅ Improved error handling and error messages
- ✅ Unified parsing entry point

### Documentation

- ✅ Added Logstash source text configuration format guide
- ✅ Added configuration format changelog
- ✅ Updated usage examples

---

## [0.1.0] - 2025-10-28

### Added

#### Core Features

- ✅ Logstash configuration parser (based on pyparsing)
- ✅ Complete AST node definitions (25 node types)
- ✅ AST → Logstash configuration generation
- ✅ AST → Python dict conversion

#### Node Types

- ✅ Simple types: LSString, LSBareWord, Number, Boolean, Regexp, SelectorNode
- ✅ Data structures: Array, Hash, HashEntryNode, Attribute
- ✅ Plugin: Plugin
- ✅ Expressions: CompareExpression, RegexExpression, InExpression, NotInExpression, NegativeExpression, BooleanExpression, Expression
- ✅ Conditional branches: IfCondition, ElseIfCondition, ElseCondition, Branch
- ✅ Configuration: PluginSectionNode, Config

#### Features

- ✅ Support all Logstash syntax elements
- ✅ Preserve original source text
- ✅ Support conditional branches (if/else if/else)
- ✅ Support complex expressions
- ✅ Support nested data structures

#### Testing

- ✅ Unit test coverage
- ✅ Integration tests
- ✅ Type checking (mypy)
- ✅ Code style checking (ruff)

---

## Version Notes

### Version Number Rules

- **Major Version**: Incompatible API changes
- **Minor Version**: Backward-compatible feature additions
- **Patch Version**: Backward-compatible bug fixes

### Compatibility Guarantees

#### Backward Compatible

- ✅ Existing `to_python()` calls return dict (default behavior)
- ✅ Existing `to_logstash()` method unchanged
- ✅ Existing `to_source()` method unchanged
- ✅ Existing AST structure unchanged

#### Breaking Changes

- ⚠️ v0.3.0 removed parent link (internal implementation, doesn't affect public API)

---

## Migration Guide

### Migrating from 0.2.x to 0.3.x

#### No Changes Needed

```python
# These codes need no modification, continue to work
ast = parse_logstash_config(config_text)
python_dict = ast.to_python()
output_text = ast.to_logstash()
```

#### Using New Features

```python
# Use new Pydantic Schema features
schema = ast.to_python(as_pydantic=True)
json_str = schema.model_dump_json()

# Restore from JSON
from logstash_parser.schemas import ConfigSchema
loaded_schema = ConfigSchema.model_validate_json(json_str)
reconstructed_ast = Config.from_python(loaded_schema)
```

#### Notes

1. **parent link removed**

   - If your code depends on `node.parent`, need to modify
   - Most cases don't need parent, use `_s` and `_loc` instead

2. **source_text no longer serialized**
   - JSON doesn't include source_text
   - If need to preserve, use `model_dump(exclude_none=False)`

### Migrating from 0.1.x to 0.2.x

#### Configuration Model Update

```python
# Old code (still works)
config = InputConfig(
    type="beats",
    port=5044
)

# New code (recommended)
config = InputConfig(
    source="""
    beats {
        port => 5044
    }
    """
)
```

---

## Future Plans

### v0.5.0 (Planned)

- [ ] Configuration template system
- [ ] Configuration fragment merging
- [ ] Configuration format conversion tools
- [ ] Configuration visual editor

### v0.6.0 (Planned)

- [ ] Configuration version management
- [ ] Configuration diff comparison
- [ ] Configuration optimization suggestions
- [ ] Performance analysis tools

### v1.0.0 (Long-term Goal)

- [ ] Stable public API
- [ ] Complete documentation
- [ ] 100% test coverage
- [ ] Production environment validation

---

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

### CHANGELOG Update Best Practices

1. **When to Update**:

   - Add changes to `[Unreleased]` section when merging PR
   - Before releasing new version, change `[Unreleased]` to version number and date
   - Create new empty `[Unreleased]` section

2. **How to Categorize**:

   - **Added**: New features, new capabilities
   - **Changed**: Improvements to existing features
   - **Fixed**: Bug fixes
   - **Breaking Changes**: Incompatible API changes
   - **Documentation Improvements**: Documentation updates
   - **Performance**: Performance optimizations
   - **Refactored**: Code refactoring (doesn't affect functionality)

3. **Writing Standards**:

   - Use clear, concise language
   - Describe changes from user perspective
   - For breaking changes, provide migration guide
   - Use ✅ to mark completed items
   - Use ⚠️ to mark changes needing attention

4. **Avoid**:

   - ❌ Don't hardcode specific test counts or coverage rates
   - ❌ Don't include internal implementation details (unless affects users)
   - ❌ Don't use vague descriptions (like "some improvements")
   - ❌ Don't forget to update migration guide

5. **Example**:

**✅ Good Change Description**:

```markdown
### Added

- ✅ Added `parse_logstash_config()` convenience function with better error handling

### Breaking Changes

⚠️ **API Changes**:

- Removed `Expression` class, directly use concrete expression types
- Migration guide: Change `Expression(condition)` to directly use `condition`
```

**❌ Bad Change Description**:

```markdown
### Changed

- Fixed some issues
- Improved performance
- Updated tests (425 tests, 90.75% coverage)
```

---

## License

This project uses MIT License. See [LICENSE](../LICENSE) file for details.

---

## Acknowledgments

Thanks to all contributors and users for their support!

Special thanks to:

- [pyparsing](https://github.com/pyparsing/pyparsing) - Powerful parsing library
- [Pydantic](https://github.com/pydantic/pydantic) - Excellent data validation library
- [Logstash](https://www.elastic.co/logstash) - Source of inspiration

---

## Links

- [GitHub Repository](https://github.com/your-org/logstash-parser)
- [Issue Tracker](https://github.com/your-org/logstash-parser/issues)
- [Documentation](https://logstash-parser.readthedocs.io/)
- [PyPI](https://pypi.org/project/logstash-parser/)
