"""Tests for from_logstash class method."""

import pytest
from pyparsing import ParseException

from logstash_parser.ast_nodes import (
    Array,
    Attribute,
    Boolean,
    BooleanExpression,
    Branch,
    CompareExpression,
    Config,
    ElseCondition,
    ElseIfCondition,
    Hash,
    HashEntryNode,
    IfCondition,
    InExpression,
    LSBareWord,
    LSString,
    NegativeExpression,
    NotInExpression,
    Number,
    Plugin,
    PluginSectionNode,
    RegexExpression,
    Regexp,
    RValue,
    SelectorNode,
)


class TestSimpleNodesFromLogstash:
    """Test simple node types parsing from Logstash text."""

    def test_lsstring_from_logstash_double_quote(self):
        """Test parsing LSString with double quotes."""
        node = LSString.from_logstash('"hello world"')
        assert isinstance(node, LSString)
        assert node.lexeme == '"hello world"'
        assert node.value == "hello world"

    def test_lsstring_from_logstash_single_quote(self):
        """Test parsing LSString with single quotes."""
        node = LSString.from_logstash("'hello world'")
        assert isinstance(node, LSString)
        assert node.lexeme == "'hello world'"
        assert node.value == "hello world"

    def test_lsbareword_from_logstash(self):
        """Test parsing LSBareWord."""
        node = LSBareWord.from_logstash("mutate")
        assert isinstance(node, LSBareWord)
        assert node.value == "mutate"

    def test_number_int_from_logstash(self):
        """Test parsing Number (integer)."""
        node = Number.from_logstash("123")
        assert isinstance(node, Number)
        assert node.value == 123

    def test_number_float_from_logstash(self):
        """Test parsing Number (float)."""
        node = Number.from_logstash("45.67")
        assert isinstance(node, Number)
        assert node.value == 45.67

    def test_number_negative_from_logstash(self):
        """Test parsing Number (negative)."""
        node = Number.from_logstash("-100")
        assert isinstance(node, Number)
        assert node.value == -100

    def test_boolean_true_from_logstash(self):
        """Test parsing Boolean (true)."""
        node = Boolean.from_logstash("true")
        assert isinstance(node, Boolean)
        assert node.value is True

    def test_boolean_false_from_logstash(self):
        """Test parsing Boolean (false)."""
        node = Boolean.from_logstash("false")
        assert isinstance(node, Boolean)
        assert node.value is False

    def test_regexp_from_logstash(self):
        """Test parsing Regexp."""
        node = Regexp.from_logstash("/pattern/")
        assert isinstance(node, Regexp)
        # Regexp parser removes the slashes, so lexeme is just the pattern
        assert node.lexeme == "pattern" or node.lexeme == "/pattern/"  # 兼容不同版本

    def test_selector_from_logstash(self):
        """Test parsing SelectorNode."""
        node = SelectorNode.from_logstash("[field]")
        assert isinstance(node, SelectorNode)
        assert node.raw == "[field]"

    def test_selector_nested_from_logstash(self):
        """Test parsing nested SelectorNode."""
        node = SelectorNode.from_logstash("[foo][bar][baz]")
        assert isinstance(node, SelectorNode)
        assert node.raw == "[foo][bar][baz]"


class TestDataStructuresFromLogstash:
    """Test data structure node types parsing from Logstash text."""

    def test_array_simple_from_logstash(self):
        """Test parsing simple Array."""
        node = Array.from_logstash("[1, 2, 3]")
        assert isinstance(node, Array)
        assert len(node.children) == 3
        assert all(isinstance(child, Number) for child in node.children)

    def test_array_strings_from_logstash(self):
        """Test parsing Array with strings."""
        node = Array.from_logstash('["a", "b", "c"]')
        assert isinstance(node, Array)
        assert len(node.children) == 3
        assert all(isinstance(child, LSString) for child in node.children)

    def test_array_mixed_from_logstash(self):
        """Test parsing Array with mixed types."""
        node = Array.from_logstash('[1, "two", 3.0]')
        assert isinstance(node, Array)
        assert len(node.children) == 3

    def test_hash_simple_from_logstash(self):
        """Test parsing simple Hash."""
        node = Hash.from_logstash('{ "key" => "value" }')
        assert isinstance(node, Hash)
        assert len(node.children) == 1

    def test_hash_multiple_entries_from_logstash(self):
        """Test parsing Hash with multiple entries."""
        node = Hash.from_logstash('{ "key1" => "value1" "key2" => "value2" }')
        assert isinstance(node, Hash)
        assert len(node.children) == 2


class TestPluginFromLogstash:
    """Test Plugin parsing from Logstash text."""

    def test_plugin_simple_from_logstash(self):
        """Test parsing simple Plugin."""
        text = """grok {
            match => { "message" => "%{PATTERN}" }
        }"""
        node = Plugin.from_logstash(text)
        assert isinstance(node, Plugin)
        assert node.plugin_name == "grok"
        assert len(node.children) == 1

    def test_plugin_multiple_attributes_from_logstash(self):
        """Test parsing Plugin with multiple attributes."""
        text = """mutate {
            add_field => { "foo" => "bar" }
            remove_field => ["temp"]
        }"""
        node = Plugin.from_logstash(text)
        assert isinstance(node, Plugin)
        assert node.plugin_name == "mutate"
        assert len(node.children) == 2


class TestAttributeFromLogstash:
    """Test Attribute parsing from Logstash text."""

    def test_attribute_simple_from_logstash(self):
        """Test parsing simple Attribute."""
        node = Attribute.from_logstash('match => { "message" => "%{PATTERN}" }')
        assert isinstance(node, Attribute)
        assert isinstance(node.name, LSBareWord)
        assert node.name.value == "match"


class TestComplexNodesFromLogstash:
    """Test complex node types parsing from Logstash text."""

    def test_compare_expression_from_logstash(self):
        """Test parsing CompareExpression."""
        node = CompareExpression.from_logstash("[status] == 200")
        assert isinstance(node, CompareExpression)
        assert node.operator == "=="

    def test_plugin_section_from_logstash(self):
        """Test parsing PluginSectionNode."""
        text = """filter {
            grok {
                match => { "message" => "%{PATTERN}" }
            }
        }"""
        node = PluginSectionNode.from_logstash(text)
        assert isinstance(node, PluginSectionNode)
        assert node.plugin_type == "filter"
        assert len(node.children) == 1

    def test_config_from_logstash(self):
        """Test parsing Config."""
        text = """filter {
            grok {
                match => { "message" => "%{PATTERN}" }
            }
        }"""
        node = Config.from_logstash(text)
        assert isinstance(node, Config)
        assert len(node.children) == 1


class TestFromLogstashErrors:
    """Test error handling in from_logstash."""

    def test_invalid_text_raises_error(self):
        """Test that invalid text raises ParseException."""
        with pytest.raises(ParseException):  # pyparsing.ParseException
            LSString.from_logstash("not a string")

    def test_partial_match_with_parse_all_true(self):
        """Test that partial match fails with parse_all=True."""
        with pytest.raises(ParseException):  # pyparsing.ParseException
            Number.from_logstash("123 extra", parse_all=True)

    def test_partial_match_with_parse_all_false(self):
        """Test that partial match succeeds with parse_all=False."""
        node = Number.from_logstash("123 extra", parse_all=False)
        assert isinstance(node, Number)
        assert node.value == 123


class TestFromLogstashRoundtrip:
    """Test roundtrip: from_logstash -> to_logstash."""

    def test_lsstring_roundtrip(self):
        """Test LSString roundtrip."""
        original = '"hello world"'
        node = LSString.from_logstash(original)
        result = node.to_logstash()
        assert result == original

    def test_number_roundtrip(self):
        """Test Number roundtrip."""
        original = "123"
        node = Number.from_logstash(original)
        result = node.to_logstash()
        assert result == 123

    def test_boolean_roundtrip(self):
        """Test Boolean roundtrip."""
        original = "true"
        node = Boolean.from_logstash(original)
        result = node.to_logstash()
        assert result == "true"

    def test_array_roundtrip(self):
        """Test Array roundtrip."""
        original = "[1, 2, 3]"
        node = Array.from_logstash(original)
        result = node.to_logstash()
        # Normalize whitespace for comparison
        assert result.replace(" ", "") == original.replace(" ", "")

    def test_plugin_roundtrip(self):
        """Test Plugin roundtrip."""
        original = """grok {
  match => { "message" => "%{PATTERN}" }
}"""
        node = Plugin.from_logstash(original)
        result = node.to_logstash()
        # Both should parse to the same AST
        node2 = Plugin.from_logstash(result)
        assert node.plugin_name == node2.plugin_name
        assert len(node.children) == len(node2.children)


class TestExpressionNodesFromLogstash:
    """Test expression node types parsing from Logstash text."""

    def test_compare_expression_equal(self):
        """Test parsing CompareExpression with == operator."""
        node = CompareExpression.from_logstash("[status] == 200")
        assert isinstance(node, CompareExpression)
        assert node.operator == "=="
        # Children are wrapped in RValue
        assert isinstance(node.left, RValue)
        assert isinstance(node.left.value, SelectorNode)
        assert isinstance(node.right, RValue)
        assert isinstance(node.right.value, Number)

    def test_compare_expression_not_equal(self):
        """Test parsing CompareExpression with != operator."""
        node = CompareExpression.from_logstash('[type] != "error"')
        assert isinstance(node, CompareExpression)
        assert node.operator == "!="

    def test_compare_expression_greater_than(self):
        """Test parsing CompareExpression with > operator."""
        node = CompareExpression.from_logstash("[count] > 100")
        assert isinstance(node, CompareExpression)
        assert node.operator == ">"

    def test_compare_expression_less_than(self):
        """Test parsing CompareExpression with < operator."""
        node = CompareExpression.from_logstash("[count] < 50")
        assert isinstance(node, CompareExpression)
        assert node.operator == "<"

    def test_regex_expression_match(self):
        """Test parsing RegexExpression with =~ operator."""
        node = RegexExpression.from_logstash("[message] =~ /error/")
        assert isinstance(node, RegexExpression)
        assert node.operator == "=~"
        # RegexExpression wraps left in RValue
        assert isinstance(node.left, RValue)
        assert isinstance(node.left.value, SelectorNode)
        assert isinstance(node.pattern, Regexp)

    def test_regex_expression_not_match(self):
        """Test parsing RegexExpression with !~ operator."""
        node = RegexExpression.from_logstash("[message] !~ /debug/")
        assert isinstance(node, RegexExpression)
        assert node.operator == "!~"

    def test_in_expression(self):
        """Test parsing InExpression."""
        node = InExpression.from_logstash("[status] in [200, 201, 204]")
        assert isinstance(node, InExpression)
        assert node.operator == "in"
        # InExpression wraps value and collection in RValue
        assert isinstance(node.value, RValue)
        assert isinstance(node.value.value, SelectorNode)
        assert isinstance(node.collection, RValue)
        assert isinstance(node.collection.value, Array)

    def test_not_in_expression(self):
        """Test parsing NotInExpression."""
        node = NotInExpression.from_logstash("[status] not in [400, 500]")
        assert isinstance(node, NotInExpression)
        # After grammar fix, operator is stored as "not in" (combined token)
        assert node.operator == "not in"

    def test_negative_expression(self):
        """Test parsing NegativeExpression."""
        node = NegativeExpression.from_logstash("![field]")
        assert isinstance(node, NegativeExpression)
        assert node.operator == "!"
        assert isinstance(node.expression, SelectorNode)

    def test_boolean_expression_and(self):
        """Test parsing BooleanExpression with and operator."""
        node = BooleanExpression.from_logstash('[status] == 200 and [type] == "nginx"')
        assert isinstance(node, BooleanExpression)
        assert node.operator == "and"
        # BooleanExpression now directly contains expression types (no wrapper)
        assert isinstance(node.left, CompareExpression)
        assert isinstance(node.right, CompareExpression)

    def test_boolean_expression_or(self):
        """Test parsing BooleanExpression with or operator."""
        node = BooleanExpression.from_logstash("[status] == 404 or [status] == 500")
        assert isinstance(node, BooleanExpression)
        assert node.operator == "or"

    def test_expression_parentheses(self):
        """Test parsing expression with parentheses."""
        # Parentheses in expressions are now handled by the grammar directly
        # The result is the inner expression type without wrapper
        node = BooleanExpression.from_logstash("([status] == 200)")
        # With parentheses, it should still parse as the inner expression
        assert isinstance(node, CompareExpression)

    def test_rvalue_string(self):
        """Test parsing RValue with string."""
        node = RValue.from_logstash('"test"')
        assert isinstance(node, RValue)
        assert isinstance(node.value, LSString)

    def test_rvalue_number(self):
        """Test parsing RValue with number."""
        node = RValue.from_logstash("123")
        assert isinstance(node, RValue)
        assert isinstance(node.value, Number)

    def test_rvalue_selector(self):
        """Test parsing RValue with selector."""
        node = RValue.from_logstash("[field]")
        assert isinstance(node, RValue)
        assert isinstance(node.value, SelectorNode)

    def test_rvalue_array(self):
        """Test parsing RValue with array."""
        node = RValue.from_logstash("[1, 2, 3]")
        assert isinstance(node, RValue)
        assert isinstance(node.value, Array)


class TestConditionalNodesFromLogstash:
    """Test conditional node types parsing from Logstash text."""

    def test_if_condition_simple(self):
        """Test parsing simple IfCondition."""
        text = """if [type] == "nginx" {
            mutate { add_tag => ["nginx"] }
        }"""
        node = IfCondition.from_logstash(text)
        assert isinstance(node, IfCondition)
        # IfCondition expr is now directly the expression type (no wrapper)
        assert isinstance(node.expr, CompareExpression)
        assert len(node.children) == 1
        assert isinstance(node.children[0], Plugin)

    def test_if_condition_with_boolean_expression(self):
        """Test parsing IfCondition with boolean expression."""
        text = """if [status] >= 200 and [status] < 300 {
            mutate { add_tag => ["success"] }
        }"""
        node = IfCondition.from_logstash(text)
        assert isinstance(node, IfCondition)
        assert isinstance(node.expr, BooleanExpression)

    def test_else_if_condition(self):
        """Test parsing ElseIfCondition."""
        text = """else if [status] >= 400 {
            mutate { add_tag => ["error"] }
        }"""
        node = ElseIfCondition.from_logstash(text)
        assert isinstance(node, ElseIfCondition)
        # ElseIfCondition expr is now directly the expression type (no wrapper)
        assert isinstance(node.expr, CompareExpression)
        assert len(node.children) == 1

    def test_else_condition(self):
        """Test parsing ElseCondition."""
        text = """else {
            mutate { add_tag => ["other"] }
        }"""
        node = ElseCondition.from_logstash(text)
        assert isinstance(node, ElseCondition)
        assert len(node.children) == 1
        assert isinstance(node.children[0], Plugin)

    def test_branch_if_only(self):
        """Test parsing Branch with only if."""
        text = """if [type] == "nginx" {
            mutate { add_tag => ["nginx"] }
        }"""
        node = Branch.from_logstash(text)
        assert isinstance(node, Branch)
        assert len(node.children) == 1
        assert isinstance(node.children[0], IfCondition)

    def test_branch_if_else(self):
        """Test parsing Branch with if-else."""
        text = """if [type] == "nginx" {
            mutate { add_tag => ["nginx"] }
        } else {
            mutate { add_tag => ["other"] }
        }"""
        node = Branch.from_logstash(text)
        assert isinstance(node, Branch)
        assert len(node.children) == 2
        assert isinstance(node.children[0], IfCondition)
        assert isinstance(node.children[1], ElseCondition)

    def test_branch_if_elseif_else(self):
        """Test parsing Branch with if-elseif-else."""
        text = """if [status] < 300 {
            mutate { add_tag => ["success"] }
        } else if [status] < 500 {
            mutate { add_tag => ["client_error"] }
        } else {
            mutate { add_tag => ["server_error"] }
        }"""
        node = Branch.from_logstash(text)
        assert isinstance(node, Branch)
        assert len(node.children) == 3
        assert isinstance(node.children[0], IfCondition)
        assert isinstance(node.children[1], ElseIfCondition)
        assert isinstance(node.children[2], ElseCondition)

    def test_branch_multiple_elseif(self):
        """Test parsing Branch with multiple else-if."""
        text = """if [status] == 200 {
            mutate { add_tag => ["ok"] }
        } else if [status] == 404 {
            mutate { add_tag => ["not_found"] }
        } else if [status] == 500 {
            mutate { add_tag => ["error"] }
        } else {
            mutate { add_tag => ["other"] }
        }"""
        node = Branch.from_logstash(text)
        assert isinstance(node, Branch)
        assert len(node.children) == 4


class TestHashEntryFromLogstash:
    """Test HashEntryNode parsing from Logstash text."""

    def test_hash_entry_string_key(self):
        """Test parsing HashEntryNode with string key."""
        node = HashEntryNode.from_logstash('"key" => "value"')
        assert isinstance(node, HashEntryNode)
        assert isinstance(node.key, LSString)
        assert isinstance(node.value, LSString)

    def test_hash_entry_bareword_key(self):
        """Test parsing HashEntryNode with bareword key."""
        node = HashEntryNode.from_logstash('key => "value"')
        assert isinstance(node, HashEntryNode)
        assert isinstance(node.key, LSBareWord)

    def test_hash_entry_number_key(self):
        """Test parsing HashEntryNode with number key."""
        node = HashEntryNode.from_logstash('123 => "value"')
        assert isinstance(node, HashEntryNode)
        assert isinstance(node.key, Number)

    def test_hash_entry_array_value(self):
        """Test parsing HashEntryNode with array value."""
        node = HashEntryNode.from_logstash('"tags" => ["tag1", "tag2"]')
        assert isinstance(node, HashEntryNode)
        assert isinstance(node.value, Array)

    def test_hash_entry_hash_value(self):
        """Test parsing HashEntryNode with hash value."""
        node = HashEntryNode.from_logstash('"nested" => { "key" => "value" }')
        assert isinstance(node, HashEntryNode)
        assert isinstance(node.value, Hash)


class TestPluginSectionFromLogstash:
    """Test PluginSectionNode parsing from Logstash text."""

    def test_plugin_section_input(self):
        """Test parsing input PluginSectionNode."""
        text = """input {
            file {
                path => "/var/log/test.log"
            }
        }"""
        node = PluginSectionNode.from_logstash(text)
        assert isinstance(node, PluginSectionNode)
        assert node.plugin_type == "input"
        assert len(node.children) == 1
        assert isinstance(node.children[0], Plugin)

    def test_plugin_section_filter(self):
        """Test parsing filter PluginSectionNode."""
        text = """filter {
            grok {
                match => { "message" => "%{PATTERN}" }
            }
        }"""
        node = PluginSectionNode.from_logstash(text)
        assert isinstance(node, PluginSectionNode)
        assert node.plugin_type == "filter"

    def test_plugin_section_output(self):
        """Test parsing output PluginSectionNode."""
        text = """output {
            elasticsearch {
                hosts => ["localhost:9200"]
            }
        }"""
        node = PluginSectionNode.from_logstash(text)
        assert isinstance(node, PluginSectionNode)
        assert node.plugin_type == "output"

    def test_plugin_section_multiple_plugins(self):
        """Test parsing PluginSectionNode with multiple plugins."""
        text = """filter {
            grok {
                match => { "message" => "%{PATTERN}" }
            }
            mutate {
                add_field => { "processed" => "true" }
            }
        }"""
        node = PluginSectionNode.from_logstash(text)
        assert isinstance(node, PluginSectionNode)
        assert len(node.children) == 2
        assert all(isinstance(child, Plugin) for child in node.children)

    def test_plugin_section_with_branch(self):
        """Test parsing PluginSectionNode with conditional branch."""
        text = """filter {
            if [type] == "nginx" {
                grok {
                    match => { "message" => "%{PATTERN}" }
                }
            }
        }"""
        node = PluginSectionNode.from_logstash(text)
        assert isinstance(node, PluginSectionNode)
        assert len(node.children) == 1
        assert isinstance(node.children[0], Branch)


class TestConfigFromLogstash:
    """Test Config parsing from Logstash text."""

    def test_config_single_section(self):
        """Test parsing Config with single section."""
        text = """filter {
            mutate {
                add_field => { "foo" => "bar" }
            }
        }"""
        node = Config.from_logstash(text)
        assert isinstance(node, Config)
        assert len(node.children) == 1
        assert isinstance(node.children[0], PluginSectionNode)

    def test_config_multiple_sections(self):
        """Test parsing Config with multiple sections."""
        text = """input {
            file {
                path => "/var/log/test.log"
            }
        }

        filter {
            grok {
                match => { "message" => "%{PATTERN}" }
            }
        }

        output {
            elasticsearch {
                hosts => ["localhost:9200"]
            }
        }"""
        node = Config.from_logstash(text)
        assert isinstance(node, Config)
        assert len(node.children) == 3
        assert all(isinstance(child, PluginSectionNode) for child in node.children)

    def test_config_same_section_type_multiple_times(self):
        """Test parsing Config with same section type multiple times."""
        text = """filter {
            grok {
                match => { "message" => "%{PATTERN1}" }
            }
        }

        filter {
            mutate {
                add_field => { "processed" => "true" }
            }
        }"""
        node = Config.from_logstash(text)
        assert isinstance(node, Config)
        assert len(node.children) == 2
        assert all(child.plugin_type == "filter" for child in node.children)


class TestComplexScenarios:
    """Test complex parsing scenarios."""

    def test_nested_conditionals(self):
        """Test parsing nested conditional branches."""
        text = """filter {
            if [type] == "nginx" {
                if [status] >= 400 {
                    mutate { add_tag => ["error"] }
                }
            }
        }"""
        node = PluginSectionNode.from_logstash(text)
        assert isinstance(node, PluginSectionNode)
        # Outer branch
        assert isinstance(node.children[0], Branch)
        outer_if = node.children[0].children[0]
        assert isinstance(outer_if, IfCondition)
        # Inner branch
        assert isinstance(outer_if.children[0], Branch)

    def test_complex_boolean_expression(self):
        """Test parsing complex boolean expression."""
        text = "[status] >= 200 and [status] < 300 or [status] == 304"
        node = BooleanExpression.from_logstash(text)
        assert isinstance(node, BooleanExpression)
        # Should parse as: (200 <= status < 300) or (status == 304)
        assert node.operator in ["and", "or"]

    def test_array_with_mixed_types(self):
        """Test parsing array with various types."""
        text = '[1, "string", true, [nested], { "key" => "value" }]'
        node = Array.from_logstash(text)
        assert isinstance(node, Array)
        assert len(node.children) == 5
        assert isinstance(node.children[0], Number)
        assert isinstance(node.children[1], LSString)
        assert isinstance(node.children[2], Boolean)
        assert isinstance(node.children[3], Array)
        assert isinstance(node.children[4], Hash)

    def test_hash_with_nested_structures(self):
        """Test parsing hash with nested arrays and hashes."""
        text = """{
            "simple" => "value"
            "array" => [1, 2, 3]
            "nested" => { "inner" => "value" }
        }"""
        node = Hash.from_logstash(text)
        assert isinstance(node, Hash)
        assert len(node.children) == 3

    def test_plugin_with_all_value_types(self):
        """Test parsing plugin with all value types."""
        text = """mutate {
            add_field => { "string" => "value" }
            add_tag => ["tag1", "tag2"]
            remove_field => ["temp"]
            replace => { "field" => "%{[source]}" }
        }"""
        node = Plugin.from_logstash(text)
        assert isinstance(node, Plugin)
        assert node.plugin_name == "mutate"
        assert len(node.children) == 4


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_array(self):
        """Test parsing empty array."""
        node = Array.from_logstash("[]")
        assert isinstance(node, Array)
        assert len(node.children) == 0

    def test_empty_hash(self):
        """Test parsing empty hash."""
        node = Hash.from_logstash("{}")
        assert isinstance(node, Hash)
        assert len(node.children) == 0

    def test_string_with_escapes(self):
        """Test parsing string with escape sequences."""
        node = LSString.from_logstash(r'"line1\nline2\ttab"')
        assert isinstance(node, LSString)
        assert "\\n" in node.lexeme or "\n" in node.value

    def test_selector_with_special_chars(self):
        """Test parsing selector with special characters."""
        node = SelectorNode.from_logstash("[field-name]")
        assert isinstance(node, SelectorNode)
        assert node.raw == "[field-name]"

    def test_bareword_with_underscore(self):
        """Test parsing bareword with underscore."""
        node = LSBareWord.from_logstash("my_field")
        assert isinstance(node, LSBareWord)
        assert node.value == "my_field"

    def test_plugin_name_with_hyphen(self):
        """Test parsing plugin with hyphen in name."""
        text = """my-custom-plugin {
            field => "value"
        }"""
        node = Plugin.from_logstash(text)
        assert isinstance(node, Plugin)
        assert node.plugin_name == "my-custom-plugin"

    def test_very_large_number(self):
        """Test parsing very large number."""
        node = Number.from_logstash("9999999999")
        assert isinstance(node, Number)
        assert node.value == 9999999999

    def test_very_small_float(self):
        """Test parsing very small float."""
        node = Number.from_logstash("0.000001")
        assert isinstance(node, Number)
        assert node.value == 0.000001


class TestParseAllParameter:
    """Test parse_all parameter behavior."""

    def test_parse_all_true_strict(self):
        """Test parse_all=True requires exact match."""
        with pytest.raises(ParseException):
            Number.from_logstash("123 extra text", parse_all=True)

    def test_parse_all_false_partial(self):
        """Test parse_all=False allows partial match."""
        node = Number.from_logstash("123 extra text", parse_all=False)
        assert isinstance(node, Number)
        assert node.value == 123

    def test_parse_all_default_is_true(self):
        """Test default parse_all is True."""
        with pytest.raises(ParseException):
            LSString.from_logstash('"hello" world')


class TestAllNodesHaveParsers:
    """Test that all node types have parser elements defined."""

    def test_all_simple_nodes_have_parsers(self):
        """Test all simple node types can be parsed."""
        nodes = [
            (LSString, '"test"'),
            (LSBareWord, "test"),
            (Number, "123"),
            (Boolean, "true"),
            (Regexp, "/pattern/"),
            (SelectorNode, "[field]"),
        ]
        for node_class, text in nodes:
            node = node_class.from_logstash(text)
            assert isinstance(node, node_class)

    def test_all_expression_nodes_have_parsers(self):
        """Test all expression node types can be parsed."""
        nodes = [
            (CompareExpression, "[x] == 1"),
            (RegexExpression, "[x] =~ /a/"),
            (InExpression, "[x] in [1]"),
            (NotInExpression, "[x] not in [1]"),
            (NegativeExpression, "![x]"),
            (BooleanExpression, "[x] == 1 and [y] == 2"),
        ]
        for node_class, text in nodes:
            node = node_class.from_logstash(text)
            assert isinstance(node, node_class)

    def test_all_structural_nodes_have_parsers(self):
        """Test all structural node types can be parsed."""
        nodes = [
            (Array, "[1, 2]"),
            (Hash, '{ "k" => "v" }'),
            (HashEntryNode, '"k" => "v"'),
            (Attribute, 'field => "value"'),
            (Plugin, 'mutate { add_tag => ["x"] }'),
        ]
        for node_class, text in nodes:
            node = node_class.from_logstash(text)
            assert isinstance(node, node_class)
