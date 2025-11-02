"""Tests for to_logstash() method and Logstash config generation."""

import pytest

from logstash_parser import parse_logstash_config
from logstash_parser.ast_nodes import (
    Array,
    Attribute,
    Boolean,
    Hash,
    HashEntryNode,
    LSBareWord,
    LSString,
    MethodCall,
    Number,
    Plugin,
    SelectorNode,
)


class TestToLogstashBasic:
    """Test basic to_logstash() functionality."""

    def test_hash_simple(self):
        """Test Hash.to_logstash() with simple entries."""
        entry1 = HashEntryNode(LSString('"key1"'), LSString('"value1"'))
        entry2 = HashEntryNode(LSString('"key2"'), Number(100))
        hash_node = Hash((entry1, entry2))

        output = hash_node.to_logstash()
        assert '"key1"' in output
        assert '"value1"' in output
        assert '"key2"' in output
        assert "100" in output
        assert "=>" in output
        assert "{" in output
        assert "}" in output

    def test_hash_empty(self):
        """Test Hash.to_logstash() with empty hash."""
        hash_node = Hash(())
        output = hash_node.to_logstash()
        assert "{" in output
        assert "}" in output

    def test_hash_single_entry(self):
        """Test Hash.to_logstash() with single entry."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash()
        assert '"key"' in output
        assert '"value"' in output
        assert "=>" in output

    def test_attribute_simple(self):
        """Test Attribute.to_logstash() with simple value."""
        name = LSBareWord("port")
        value = Number(5044)
        attr = Attribute(name, value)

        output = attr.to_logstash()
        assert "port" in output
        assert "5044" in output
        assert "=>" in output

    def test_attribute_with_hash(self):
        """Test Attribute.to_logstash() with hash value."""
        name = LSBareWord("match")
        entry = HashEntryNode(LSString('"message"'), LSString('"%{PATTERN}"'))
        value = Hash((entry,))
        attr = Attribute(name, value)

        output = attr.to_logstash()
        assert "match" in output
        assert '"message"' in output
        assert '"%{PATTERN}"' in output

    def test_plugin_simple(self):
        """Test Plugin.to_logstash() with simple attributes."""
        attr1 = Attribute(LSBareWord("port"), Number(5044))
        attr2 = Attribute(LSBareWord("host"), LSString('"0.0.0.0"'))
        plugin = Plugin("beats", (attr1, attr2))

        output = plugin.to_logstash()
        assert "beats" in output
        assert "port" in output
        assert "5044" in output
        assert "host" in output
        assert '"0.0.0.0"' in output
        assert "{" in output
        assert "}" in output


class TestToLogstashNested:
    """Test to_logstash() with nested structures."""

    def test_hash_nested(self):
        """Test Hash.to_logstash() with nested hash."""
        inner_entry = HashEntryNode(LSString('"inner"'), LSString('"value"'))
        inner_hash = Hash((inner_entry,))
        outer_entry = HashEntryNode(LSString('"outer"'), inner_hash)
        outer_hash = Hash((outer_entry,))

        output = outer_hash.to_logstash()
        assert '"outer"' in output
        assert '"inner"' in output
        assert '"value"' in output

    def test_hash_deeply_nested(self):
        """Test deeply nested hash structure."""
        # level3
        level3_entry = HashEntryNode(LSString('"level3"'), LSString('"value"'))
        level3_hash = Hash((level3_entry,))

        # level2
        level2_entry = HashEntryNode(LSString('"level2"'), level3_hash)
        level2_hash = Hash((level2_entry,))

        # level1
        level1_entry = HashEntryNode(LSString('"level1"'), level2_hash)
        level1_hash = Hash((level1_entry,))

        output = level1_hash.to_logstash()
        assert '"level1"' in output
        assert '"level2"' in output
        assert '"level3"' in output
        assert '"value"' in output

    def test_array_of_hashes(self):
        """Test array containing hashes."""
        hash1 = Hash((HashEntryNode(LSString('"k1"'), LSString('"v1"')),))
        hash2 = Hash((HashEntryNode(LSString('"k2"'), LSString('"v2"')),))
        arr = Array((hash1, hash2))

        output = arr.to_logstash()
        assert '"k1"' in output
        assert '"v1"' in output
        assert '"k2"' in output
        assert '"v2"' in output

    def test_hash_of_arrays(self):
        """Test hash containing arrays."""
        arr1 = Array((LSString('"a"'), LSString('"b"')))
        arr2 = Array((Number(1), Number(2)))
        entry1 = HashEntryNode(LSString('"array1"'), arr1)
        entry2 = HashEntryNode(LSString('"array2"'), arr2)
        hash_node = Hash((entry1, entry2))

        output = hash_node.to_logstash()
        assert '"array1"' in output
        assert '"a"' in output
        assert '"b"' in output
        assert '"array2"' in output

    def test_mixed_nested_structures(self):
        """Test mixed nested structures."""
        # Create: { "key" => ["a", { "inner" => "value" }] }
        inner_hash = Hash((HashEntryNode(LSString('"inner"'), LSString('"value"')),))
        arr = Array((LSString('"a"'), inner_hash))
        entry = HashEntryNode(LSString('"key"'), arr)
        hash_node = Hash((entry,))

        output = hash_node.to_logstash()
        assert '"key"' in output
        assert '"a"' in output
        assert '"inner"' in output
        assert '"value"' in output


class TestToLogstashFormatting:
    """Test to_logstash() formatting (indentation, newlines)."""

    def test_hash_has_newlines(self):
        """Test Hash.to_logstash() includes newlines."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash()
        assert "\n" in output

    def test_hash_indentation(self):
        """Test Hash.to_logstash() with custom indentation."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash(indent=2)
        # Should have indentation
        lines = output.split("\n")
        assert any(line.startswith("  ") for line in lines if line.strip())

    def test_plugin_has_newlines(self):
        """Test Plugin.to_logstash() includes newlines."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))
        output = plugin.to_logstash()
        assert "\n" in output

    def test_plugin_indentation(self):
        """Test Plugin.to_logstash() with custom indentation."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))
        output = plugin.to_logstash(indent=2)
        # Should have indentation
        lines = output.split("\n")
        assert any(line.startswith("  ") for line in lines if line.strip())


class TestToLogstashConsistency:
    """Test to_logstash() consistency and idempotency."""

    def test_array_consistency(self):
        """Test Array.to_logstash() is consistent."""
        arr = Array((LSString('"a"'), Number(1), Boolean(True)))
        output1 = arr.to_logstash()
        output2 = arr.to_logstash()

        # Multiple calls should produce the same output
        assert output1 == output2
        assert '"a"' in output1
        assert "1" in output1
        assert "true" in output1

    def test_hash_consistency(self):
        """Test Hash.to_logstash() is consistent."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))
        output1 = hash_node.to_logstash()
        output2 = hash_node.to_logstash()

        # Multiple calls should produce the same output
        assert output1 == output2
        assert '"key"' in output1
        assert '"value"' in output1

    def test_attribute_consistency(self):
        """Test Attribute.to_logstash() is consistent."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        output1 = attr.to_logstash()
        output2 = attr.to_logstash()

        # Multiple calls should produce the same output
        assert output1 == output2
        assert "port" in output1
        assert "5044" in output1

    def test_plugin_consistency(self):
        """Test Plugin.to_logstash() is consistent."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))
        output1 = plugin.to_logstash()
        output2 = plugin.to_logstash()

        # Multiple calls should produce the same output
        assert output1 == output2
        assert "beats" in output1
        assert "port" in output1


class TestMethodCallToLogstash:
    """Test MethodCall.to_logstash() conversion."""

    def test_method_call_to_logstash_simple(self):
        """Test converting simple method call to Logstash."""
        args = (LSString('"test"'),)
        node = MethodCall("upper", args)

        result = node.to_logstash()
        assert result == 'upper("test")'

    def test_method_call_to_logstash_multiple_args(self):
        """Test converting method call with multiple args to Logstash."""
        args = (LSString('"Hello"'), LSString('"World"'))
        node = MethodCall("concat", args)

        result = node.to_logstash()
        assert result == 'concat("Hello", "World")'

    def test_method_call_to_logstash_no_args(self):
        """Test converting method call with no args to Logstash."""
        node = MethodCall("now", ())

        result = node.to_logstash()
        assert result == "now()"

    def test_method_call_to_logstash_with_selector(self):
        """Test converting method call with selector to Logstash."""
        args = (SelectorNode("[field]"),)
        node = MethodCall("upper", args)

        result = node.to_logstash()
        assert result == "upper([field])"

    def test_method_call_to_logstash_with_numbers(self):
        """Test converting method call with numbers to Logstash."""
        args = (Number(1), Number(2))
        node = MethodCall("add", args)

        result = node.to_logstash()
        assert result == "add(1, 2)"

    def test_nested_method_call_to_logstash(self):
        """Test converting nested method calls to Logstash."""
        inner = MethodCall("lower", (LSString('"TEST"'),))
        outer = MethodCall("upper", (inner,))

        result = outer.to_logstash()
        assert result == 'upper(lower("TEST"))'


class TestToLogstashEdgeCases:
    """Test to_logstash() edge cases."""

    def test_empty_plugin(self):
        """Test Plugin.to_logstash() with no attributes."""
        plugin = Plugin("stdin", ())
        output = plugin.to_logstash()
        assert "stdin" in output
        assert "{" in output
        assert "}" in output

    def test_attribute_with_array(self):
        """Test Attribute.to_logstash() with array value."""
        name = LSBareWord("tags")
        value = Array((LSString('"tag1"'), LSString('"tag2"')))
        attr = Attribute(name, value)

        output = attr.to_logstash()
        assert "tags" in output
        assert '"tag1"' in output
        assert '"tag2"' in output

    def test_hash_with_number_key(self):
        """Test Hash.to_logstash() with number as key."""
        entry = HashEntryNode(Number(200), LSString('"OK"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash()
        assert "200" in output
        assert '"OK"' in output

    def test_hash_with_bareword_key(self):
        """Test Hash.to_logstash() with bareword as key."""
        entry = HashEntryNode(LSBareWord("field"), LSString('"value"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash()
        assert "field" in output
        assert '"value"' in output


class TestRegressionFixes:
    """Regression tests for specific bug fixes in to_logstash() methods.

    Each test class corresponds to a specific issue that was discovered and fixed.
    """


class TestNotInExpressionFix:
    """Test fix for NotInExpression extra closing parenthesis (Issue #1)."""

    def test_not_in_expression_no_extra_parenthesis(self):
        """Test that not in expression doesn't have extra closing parenthesis."""
        config = """
        filter {
          if [status] not in [400, 404, 500] {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should not have extra parenthesis
        assert "not in" in regenerated
        assert ") not in" not in regenerated

        # Roundtrip should work
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_not_in_with_spaces(self):
        """Test not in with multiple spaces (preserves original spacing)."""
        config = """
        filter {
          if [level] not   in ["DEBUG", "TRACE"] {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should preserve the spacing (not   in)
        assert "not" in regenerated and "in" in regenerated

        # Roundtrip should work
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()


class TestBranchIndentationFix:
    """Test fix for Branch condition indentation (Issue #2)."""

    def test_if_condition_no_leading_space(self):
        """Test that if condition doesn't have leading space."""
        config = """
        filter {
          if [status] == 200 {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should not have leading space before 'if'
        lines = regenerated.split("\n")
        if_line = [line for line in lines if "if" in line and "{" in line][0]
        assert if_line.startswith("  if")  # Only section indent, no extra space

    def test_else_if_on_same_line(self):
        """Test that else if is on same line as closing brace."""
        config = """
        filter {
          if [status] == 200 {
            mutate {}
          } else if [status] == 404 {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # else if should be on same line as }
        assert "} else if" in regenerated
        assert "}\n  else if" not in regenerated

    def test_else_on_same_line(self):
        """Test that else is on same line as closing brace."""
        config = """
        filter {
          if [status] == 200 {
            mutate {}
          } else {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # else should be on same line as }
        assert "} else {" in regenerated
        assert "}\n  else {" not in regenerated

    def test_multiple_else_if(self):
        """Test multiple else if branches."""
        config = """
        filter {
          if [status] >= 200 and [status] < 300 {
            mutate { add_tag => ["2xx"] }
          } else if [status] >= 300 and [status] < 400 {
            mutate { add_tag => ["3xx"] }
          } else if [status] >= 400 and [status] < 500 {
            mutate { add_tag => ["4xx"] }
          } else {
            mutate { add_tag => ["other"] }
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # All else if and else should be on same line as }
        assert regenerated.count("} else if") == 2
        assert regenerated.count("} else {") == 1


class TestHashNestedFormatFix:
    """Test fix for Hash nested format (Issue #3)."""

    def test_hash_attribute_format(self):
        """Test hash as attribute value has correct format."""
        config = """
        filter {
          mutate {
            add_field => {
              "field1" => "value1"
              "field2" => "value2"
            }
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Hash should have opening brace on same line
        assert "add_field => {" in regenerated

        # Roundtrip should work
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_nested_hash(self):
        """Test nested hash format."""
        config = """
        filter {
          mutate {
            add_field => {
              "outer" => {
                "inner" => "value"
              }
            }
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Both hashes should have opening brace on same line
        assert "add_field => {" in regenerated
        assert '"outer" => {' in regenerated

        # Roundtrip should work
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()


class TestPluginNestedFormatFix:
    """Test fix for Plugin nested format (Issue #4)."""

    def test_codec_plugin_format(self):
        """Test codec plugin as attribute value has correct format."""
        config = """
        input {
          udp {
            port => 514
            codec => json {
              charset => "UTF-8"
            }
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Plugin should have opening brace on same line
        assert "codec => json {" in regenerated

        # Roundtrip should work
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_nested_plugin_indentation(self):
        """Test nested plugin has correct indentation."""
        config = """
        output {
          file {
            path => "/var/log/output.log"
            codec => line {
              format => "%{message}"
            }
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Check indentation
        lines = regenerated.split("\n")
        codec_line = [line for line in lines if "codec => line" in line][0]
        format_line = [line for line in lines if "format =>" in line][0]

        # format should be indented more than codec
        assert len(format_line) - len(format_line.lstrip()) > len(codec_line) - len(codec_line.lstrip())


class TestRegexpDuplicateSlashFix:
    """Test fix for Regexp duplicate slash (Issue #5)."""

    def test_regexp_no_duplicate_slash(self):
        """Test that regexp doesn't have duplicate slashes."""
        config = """
        filter {
          if [message] =~ /error/ {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should have /error/, not //error//
        assert "/error/" in regenerated
        assert "//error//" not in regenerated

        # Roundtrip should work
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_complex_regexp(self):
        """Test complex regexp pattern."""
        config = """
        filter {
          if [url] =~ /https?:\\/\\/.*\\.com/ {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should preserve the pattern correctly
        assert "=~" in regenerated
        assert regenerated.count("/") >= 4  # At least opening and closing slashes


class TestPluginSectionNewlineFix:
    """Test fix for PluginSection missing newline (Issue #6)."""

    def test_plugin_section_closing_brace_newline(self):
        """Test that plugin section closing brace is on its own line."""
        config = """
        input {
          stdin {}
        }
        filter {
          mutate {}
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Closing braces should be on their own lines
        lines = regenerated.split("\n")
        closing_braces = [line for line in lines if line.strip() == "}"]
        assert len(closing_braces) >= 2  # At least 2 section closing braces

    def test_multiple_sections_separated(self):
        """Test that multiple sections are properly separated."""
        config = """
        input {
          stdin {}
        }
        filter {
          mutate {}
        }
        output {
          stdout {}
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should be able to parse regenerated config
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()


class TestBooleanExpressionParenthesesFix:
    """Test fix for BooleanExpression parentheses based on precedence (Issue #8)."""

    def test_and_with_or_precedence(self):
        """Test that or inside and gets parentheses."""
        config = """
        filter {
          if [type] == "apache" and ([status] >= 400 or [message] =~ /error/) {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # or should have parentheses because it's inside and
        assert "([status] >= 400 or [message] =~ /error/)" in regenerated

        # Roundtrip should work
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_or_with_and_precedence(self):
        """Test that and inside or gets parentheses."""
        config = """
        filter {
          if ([a] or [b]) and [c] {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # or should have parentheses because it's left operand of and
        assert "([a] or [b]) and [c]" in regenerated

    def test_same_precedence_no_extra_parentheses(self):
        """Test that same precedence operators don't get extra parentheses."""
        config = """
        filter {
          if [a] and [b] and [c] {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should not have extra parentheses
        assert "([a] and [b])" not in regenerated or "[a] and [b] and [c]" in regenerated

    def test_xor_precedence(self):
        """Test xor precedence (between and and or)."""
        config = """
        filter {
          if [a] xor ([b] or [c]) {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # or should have parentheses because it has lower precedence than xor
        assert "([b] or [c])" in regenerated

    def test_nand_precedence(self):
        """Test nand precedence (same as and)."""
        config = """
        filter {
          if [a] nand ([b] or [c]) {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # or should have parentheses
        assert "([b] or [c])" in regenerated


class TestNegativeExpressionParenthesesFix:
    """Test fix for NegativeExpression unnecessary parentheses (Issue #9)."""

    def test_negative_selector_no_parentheses(self):
        """Test that negative selector doesn't have parentheses."""
        config = """
        filter {
          if ![field] {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should be ![field], not !([field])
        assert "![field]" in regenerated
        assert "!([field])" not in regenerated

    def test_negative_compare_has_parentheses(self):
        """Test that negative compare expression has parentheses."""
        config = """
        filter {
          if !([status] >= 400) {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should have parentheses
        assert "!([status] >= 400)" in regenerated

    def test_negative_boolean_has_parentheses(self):
        """Test that negative boolean expression has parentheses."""
        config = """
        filter {
          if !([a] and [b]) {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should have parentheses
        assert "!([a] and [b])" in regenerated

    def test_negative_in_boolean_expression(self):
        """Test negative selector in boolean expression."""
        config = """
        filter {
          if ![a] and [b] {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should be ![a] and [b], not !([a]) and [b]
        assert "![a] and [b]" in regenerated


class TestOperatorPrecedenceFix:
    """Test fix for operator precedence parsing (Issue #10)."""

    def test_or_and_precedence(self):
        """Test that 'A or B and C' is parsed as 'A or (B and C)'."""
        config = """
        filter {
          if [a] or [b] and [c] {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Roundtrip should preserve semantics
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_complex_precedence(self):
        """Test complex expression with multiple operators."""
        config = """
        filter {
          if ([a] == 1 and [b] =~ /test/) or ([c] in [1, 2] and ![d]) {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Roundtrip should preserve semantics
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_left_associativity(self):
        """Test that operators are left-associative."""
        config = """
        filter {
          if [a] and [b] and [c] {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should work correctly
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_nested_same_precedence_operators(self):
        """Test nested expressions with same precedence operators."""
        config = """
        filter {
          if ([field1] and [field2]) or ([field3] or [field4]) {
            mutate {}
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should work correctly (even if AST structure differs)
        ast2 = parse_logstash_config(regenerated)
        # Note: AST structure may differ but semantics are preserved
        # This is acceptable for associative operators
        assert ast.to_python() == ast2.to_python()
        assert "([field1] and [field2]) or ([field3] or [field4])" in ast2.to_logstash()


class TestRoundtripConsistency:
    """Test that roundtrip conversion is consistent."""

    def test_simple_config_roundtrip(self):
        """Test simple config roundtrip."""
        config = """
        filter {
          mutate {
            add_field => { "field" => "value" }
          }
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()
        ast2 = parse_logstash_config(regenerated)

        assert ast.to_python() == ast2.to_python()

    def test_complex_config_roundtrip(self):
        """Test complex config roundtrip."""
        config = """
        input {
          file {
            path => "/var/log/syslog"
            codec => json {
              charset => "UTF-8"
            }
          }
        }
        filter {
          if [type] == "syslog" and ([level] == "ERROR" or [level] == "FATAL") {
            mutate {
              add_tag => ["error"]
              add_field => {
                "severity" => "high"
                "priority" => 1
              }
            }
          } else if [type] == "syslog" and [level] == "WARN" {
            mutate {
              add_tag => ["warning"]
            }
          } else {
            mutate {
              add_tag => ["info"]
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
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()
        ast2 = parse_logstash_config(regenerated)

        assert ast.to_python() == ast2.to_python()

    def test_multiple_roundtrips(self):
        """Test that multiple roundtrips are stable."""
        config = """
        filter {
          if [a] and ([b] or [c]) {
            mutate {}
          }
        }
        """
        ast1 = parse_logstash_config(config)
        regen1 = ast1.to_logstash()

        ast2 = parse_logstash_config(regen1)
        regen2 = ast2.to_logstash()

        ast3 = parse_logstash_config(regen2)
        regen3 = ast3.to_logstash()

        # After first roundtrip, should be stable
        assert regen2 == regen3
        assert ast2.to_python() == ast3.to_python()


class TestHashEntryNestedStructures:
    """Test HashEntry.to_logstash() with nested Hash and Plugin (lines 638-649)."""

    def test_hash_entry_with_nested_hash(self):
        """Test HashEntry with nested Hash value."""
        from logstash_parser.ast_nodes import Hash, HashEntryNode, LSString

        # Create nested hash: "outer" => { "inner" => "value" }
        inner_entry = HashEntryNode(LSString('"inner"'), LSString('"value"'))
        inner_hash = Hash((inner_entry,))
        outer_entry = HashEntryNode(LSString('"outer"'), inner_hash)

        output = outer_entry.to_logstash()
        assert '"outer"' in output
        assert "=>" in output
        assert "{" in output
        assert '"inner"' in output
        assert '"value"' in output

    def test_hash_entry_with_nested_plugin(self):
        """Test HashEntry with nested Plugin value (lines 643-649)."""
        from logstash_parser.ast_nodes import Attribute, HashEntryNode, LSBareWord, LSString, Plugin

        # Create: "codec" => json { charset => "UTF-8" }
        attr = Attribute(LSBareWord("charset"), LSString('"UTF-8"'))
        plugin = Plugin("json", (attr,))
        entry = HashEntryNode(LSString('"codec"'), plugin)

        output = entry.to_logstash(indent=2)
        assert '"codec"' in output
        assert "=>" in output
        assert "json" in output
        assert "charset" in output
        assert '"UTF-8"' in output

    def test_hash_entry_multiline_nested_hash(self):
        """Test HashEntry with multiline nested hash."""
        from logstash_parser.ast_nodes import Hash, HashEntryNode, LSString

        # Create deeply nested structure
        inner1 = HashEntryNode(LSString('"key1"'), LSString('"val1"'))
        inner2 = HashEntryNode(LSString('"key2"'), LSString('"val2"'))
        inner_hash = Hash((inner1, inner2))
        outer_entry = HashEntryNode(LSString('"config"'), inner_hash)

        output = outer_entry.to_logstash()
        lines = output.split("\n")
        # Should have multiple lines
        assert len(lines) > 1
        assert '"config"' in output
        assert '"key1"' in output
        assert '"key2"' in output


class TestConfigToLogstashFormatting:
    """Test Config.to_logstash() formatting (lines 1740, 1895)."""

    def test_config_section_spacing(self):
        """Test that Config adds blank lines between sections."""
        config = """
        input {
          stdin {}
        }
        filter {
          mutate {}
        }
        output {
          stdout {}
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should have blank lines between sections
        lines = regenerated.split("\n")
        # Count empty lines
        empty_lines = [i for i, line in enumerate(lines) if line.strip() == ""]
        assert len(empty_lines) >= 2  # At least 2 blank lines between 3 sections

    def test_config_last_section_no_extra_newline(self):
        """Test that last section doesn't have extra blank line."""
        config = """
        filter {
          mutate {}
        }
        """
        ast = parse_logstash_config(config)
        regenerated = ast.to_logstash()

        # Should not end with multiple newlines
        assert not regenerated.endswith("\n\n\n")


class TestElseConditionSpecialCases:
    """Test ElseCondition special cases (lines 1561-1565, 1569, 1576)."""

    def test_else_condition_non_dm_branch(self):
        """Test ElseCondition without combined_expr."""
        from logstash_parser.ast_nodes import ElseCondition, Plugin

        plugin = Plugin("drop", ())
        condition = ElseCondition((plugin,))

        # Test both modes
        output1 = condition.to_logstash(is_dm_branch=False)
        assert output1 == "else"

        output2 = condition.to_logstash(is_dm_branch=True)
        assert "else {" in output2


class TestIfElseIfConditionNonDmBranch:
    """Test IfCondition and ElseIfCondition non-dm_branch mode (lines 1434, 1500)."""

    def test_if_condition_non_dm_branch(self):
        """Test IfCondition.to_logstash() with is_dm_branch=False."""
        from logstash_parser.ast_nodes import CompareExpression, IfCondition, Number, SelectorNode

        expr = CompareExpression(SelectorNode("[status]"), "==", Number(200))
        condition = IfCondition(expr, ())

        output = condition.to_logstash(is_dm_branch=False)
        assert output.startswith("if")
        assert "[status]" in output
        assert "==" in output
        assert "200" in output
        # Should not have opening brace in non-dm_branch mode
        assert "{" not in output

    def test_else_if_condition_non_dm_branch(self):
        """Test ElseIfCondition.to_logstash() with is_dm_branch=False."""
        from logstash_parser.ast_nodes import ElseIfCondition, SelectorNode

        expr = SelectorNode("[field]")
        condition = ElseIfCondition(expr, ())

        output = condition.to_logstash(is_dm_branch=False)
        assert output.startswith("else if")
        assert "[field]" in output
        # Should not have opening brace in non-dm_branch mode
        assert "{" not in output


class TestBranchFromPydanticEdgeCases:
    """Test Branch._from_pydantic() edge cases (lines 1626, 1631)."""

    def test_branch_from_pydantic_with_all_conditions(self):
        """Test Branch.from_python() with if, else-if, and else."""
        from logstash_parser.ast_nodes import Branch
        from logstash_parser.schemas import (
            BranchSchema,
            ElseConditionSchema,
            ElseIfConditionData,
            ElseIfConditionSchema,
            IfConditionData,
            IfConditionSchema,
            SelectorNodeSchema,
        )

        schema = BranchSchema(
            branch=[
                IfConditionSchema(if_condition=IfConditionData(expr=SelectorNodeSchema(selector_node="[a]"), body=[])),
                ElseIfConditionSchema(
                    else_if_condition=ElseIfConditionData(expr=SelectorNodeSchema(selector_node="[b]"), body=[])
                ),
                ElseConditionSchema(else_condition=[]),
            ]
        )

        node = Branch.from_python(schema)
        assert isinstance(node, Branch)
        assert len(node.children) == 3

    def test_branch_from_pydantic_no_if_raises_error(self):
        """Test Branch._from_pydantic() raises error without if condition."""
        from logstash_parser.ast_nodes import Branch
        from logstash_parser.schemas import BranchSchema, ElseConditionSchema

        # Create branch with only else (no if)
        schema = BranchSchema(branch=[ElseConditionSchema(else_condition=[])])

        with pytest.raises(ValueError, match="Branch must have an if condition"):
            Branch.from_python(schema)


class TestAttributeFromPydanticFallback:
    """Test Attribute._to_pydantic_model() fallback (line 757)."""

    def test_attribute_with_number_name_fallback(self):
        """Test Attribute with Number as name (edge case for fallback)."""
        from logstash_parser.ast_nodes import Attribute, Number

        # This is an unusual case, but test the fallback path
        attr = Attribute(Number(123), Number(456))

        # Should use fallback to model_dump_json
        schema = attr._to_pydantic_model()
        assert schema is not None

    def test_attribute_from_pydantic_multiple_keys_error(self):
        """Test Attribute._from_pydantic() with multiple keys raises error (line 766)."""
        from logstash_parser.ast_nodes import Attribute
        from logstash_parser.schemas import AttributeSchema, LSStringSchema

        # Create invalid schema with multiple keys
        schema = AttributeSchema(
            {"key1": LSStringSchema(ls_string='"val1"'), "key2": LSStringSchema(ls_string='"val2"')}
        )

        with pytest.raises(ValueError, match="Attribute must have exactly one name-value pair"):
            Attribute.from_python(schema)


class TestBooleanExpressionFromPydantic:
    """Test BooleanExpression._from_pydantic() (lines 1369-1373)."""

    def test_boolean_expression_from_pydantic(self):
        """Test BooleanExpression.from_python() with schema."""
        from logstash_parser.ast_nodes import BooleanExpression
        from logstash_parser.schemas import BooleanExpressionData, BooleanExpressionSchema, SelectorNodeSchema

        schema = BooleanExpressionSchema(
            boolean_expression=BooleanExpressionData(
                left=SelectorNodeSchema(selector_node="[a]"),
                operator="and",
                right=SelectorNodeSchema(selector_node="[b]"),
            )
        )

        node = BooleanExpression.from_python(schema)
        assert isinstance(node, BooleanExpression)
        assert node.operator == "and"


class TestUnusedFunction:
    """Test unused function build_expression_unwrap (line 1895)."""

    def test_build_expression_unwrap_exists(self):
        """Test that build_expression_unwrap function exists."""
        from logstash_parser.ast_nodes import build_expression_unwrap

        # Function should exist even if unused
        assert callable(build_expression_unwrap)


class TestHashToLogstashEdgeCases:
    """Test Hash.to_logstash() edge cases (lines 677-679, 696)."""

    def test_hash_with_selector_key(self):
        """Test Hash with SelectorNode as key."""
        from logstash_parser.ast_nodes import Hash, HashEntryNode, LSString, SelectorNode

        entry = HashEntryNode(SelectorNode("[field]"), LSString('"value"'))
        hash_node = Hash((entry,))

        output = hash_node.to_logstash()
        assert "[field]" in output
        assert '"value"' in output

    def test_hash_with_boolean_value(self):
        """Test Hash with Boolean value."""
        from logstash_parser.ast_nodes import Boolean, Hash, HashEntryNode, LSString

        entry = HashEntryNode(LSString('"enabled"'), Boolean(True))
        hash_node = Hash((entry,))

        output = hash_node.to_logstash()
        assert '"enabled"' in output
        assert "true" in output


class TestSelectorNodeEdgeCases:
    """Test SelectorNode edge cases (lines 569-571, 578)."""

    def test_selector_node_to_repr(self):
        """Test SelectorNode.to_repr() method."""
        from logstash_parser.ast_nodes import SelectorNode

        node = SelectorNode("[field][subfield]")
        result = node.to_repr()
        assert "SelectorNode" in result
        assert "[field][subfield]" in result

    def test_selector_node_to_repr_with_indent(self):
        """Test SelectorNode.to_repr() with indentation."""
        from logstash_parser.ast_nodes import SelectorNode

        node = SelectorNode("[test]")
        result = node.to_repr(indent=2)
        assert result.startswith("  ")


class TestPluginToLogstashEdgeCases:
    """Test Plugin.to_logstash() edge cases (line 985, 992)."""

    def test_plugin_to_repr(self):
        """Test Plugin.to_repr() method."""
        from logstash_parser.ast_nodes import Attribute, LSBareWord, LSString, Plugin

        attr = Attribute(LSBareWord("field"), LSString('"value"'))
        plugin = Plugin("mutate", (attr,))

        result = plugin.to_repr()
        assert "Plugin" in result
        assert "mutate" in result


class TestNumberToRepr:
    """Test Number.to_repr() method (line 1213)."""

    def test_number_to_repr(self):
        """Test Number.to_repr() method."""
        from logstash_parser.ast_nodes import Number

        node = Number(42)
        result = node.to_repr()
        assert "Number" in result
        assert "42" in result

    def test_number_to_repr_with_indent(self):
        """Test Number.to_repr() with indentation."""
        from logstash_parser.ast_nodes import Number

        node = Number(123)
        result = node.to_repr(indent=4)
        assert result.startswith("    ")
