"""Tests for to_source() method and source text reconstruction."""

from logstash_parser import parse_logstash_config
from logstash_parser.ast_nodes import (
    Array,
    Attribute,
    Boolean,
    BooleanExpression,
    Branch,
    Hash,
    HashEntryNode,
    LSBareWord,
    LSString,
    MethodCall,
    Number,
    Plugin,
    Regexp,
    SelectorNode,
)


class TestToSourceBasic:
    """Test basic to_source() functionality."""

    def test_lsstring_to_source(self):
        """Test LSString.to_source()."""
        node = LSString('"hello world"')
        assert node.to_source() == '"hello world"'

    def test_lsstring_single_quote_to_source(self):
        """Test LSString.to_source() with single quotes."""
        node = LSString("'hello'")
        assert node.to_source() == "'hello'"

    def test_lsbareword_to_source(self):
        """Test LSBareWord.to_source()."""
        node = LSBareWord("mutate")
        assert node.to_source() == "mutate"

    def test_number_int_to_source(self):
        """Test Number.to_source() with integer."""
        node = Number(123)
        assert node.to_source() == 123

    def test_number_float_to_source(self):
        """Test Number.to_source() with float."""
        node = Number(45.67)
        assert node.to_source() == 45.67

    def test_boolean_true_to_source(self):
        """Test Boolean.to_source() with True."""
        node = Boolean(True)
        assert node.to_source() == "true"

    def test_boolean_false_to_source(self):
        """Test Boolean.to_source() with False."""
        node = Boolean(False)
        assert node.to_source() == "false"

    def test_regexp_to_source(self):
        """Test Regexp.to_source()."""
        node = Regexp("/error/")
        assert node.to_source() == "/error/"

    def test_regexp_with_escapes_to_source(self):
        """Test Regexp.to_source() with escaped characters."""
        node = Regexp(r"/\/var\/log\/.*/")
        assert node.to_source() == r"/\/var\/log\/.*/"

    def test_selector_to_source(self):
        """Test SelectorNode.to_source()."""
        node = SelectorNode("[field][subfield]")
        assert node.to_source() == "[field][subfield]"


class TestToSourceArrayReconstruction:
    """Test Array.to_source() reconstruction from children."""

    def test_array_reconstruction_simple(self):
        """Test Array.to_source() reconstructs from children."""
        # Create array without source text (no s/loc parameters)
        arr = Array(
            (
                LSString('"a"'),
                LSString('"b"'),
                LSString('"c"'),
            )
        )
        source = arr.to_source()
        assert source == '["a", "b", "c"]'

    def test_array_reconstruction_mixed_types(self):
        """Test Array.to_source() with mixed types."""
        arr = Array(
            (
                LSString('"test"'),
                Number(123),
                Boolean(True),
            )
        )
        source = arr.to_source()
        assert '"test"' in source
        assert "123" in source
        assert "true" in source

    def test_array_reconstruction_empty(self):
        """Test Array.to_source() with empty array."""
        arr = Array(())
        source = arr.to_source()
        assert source == "[]"

    def test_array_reconstruction_nested(self):
        """Test Array.to_source() with nested arrays."""
        inner = Array((LSString('"x"'), LSString('"y"')))
        outer = Array((LSString('"a"'), inner))
        source = outer.to_source()
        assert '"a"' in source
        assert '"x"' in source
        assert '"y"' in source


class TestToSourceWithNumbers:
    """Test to_source() with various number formats."""

    def test_positive_integer(self):
        """Test positive integer to_source."""
        node = Number(42)
        assert node.to_source() == 42

    def test_negative_integer(self):
        """Test negative integer to_source."""
        node = Number(-100)
        assert node.to_source() == -100

    def test_zero(self):
        """Test zero to_source."""
        node = Number(0)
        assert node.to_source() == 0

    def test_positive_float(self):
        """Test positive float to_source."""
        node = Number(3.14)
        assert node.to_source() == 3.14

    def test_negative_float(self):
        """Test negative float to_source."""
        node = Number(-2.5)
        assert node.to_source() == -2.5

    def test_very_large_number(self):
        """Test very large number to_source."""
        node = Number(999999999)
        assert node.to_source() == 999999999

    def test_very_small_float(self):
        """Test very small float to_source."""
        node = Number(0.0001)
        assert node.to_source() == 0.0001


class TestToSourceWithStrings:
    """Test to_source() with various string formats."""

    def test_empty_string(self):
        """Test empty string to_source."""
        node = LSString('""')
        assert node.to_source() == '""'

    def test_string_with_spaces(self):
        """Test string with spaces to_source."""
        node = LSString('"hello world"')
        assert node.to_source() == '"hello world"'

    def test_string_with_special_chars(self):
        """Test string with special characters to_source."""
        node = LSString('"test@#$%"')
        assert node.to_source() == '"test@#$%"'

    def test_string_with_newline(self):
        """Test string with newline to_source."""
        node = LSString('"line1\\nline2"')
        assert node.to_source() == '"line1\\nline2"'

    def test_string_with_tab(self):
        """Test string with tab to_source."""
        node = LSString('"col1\\tcol2"')
        assert node.to_source() == '"col1\\tcol2"'

    def test_string_with_quotes(self):
        """Test string with escaped quotes to_source."""
        node = LSString('"say \\"hello\\""')
        assert node.to_source() == '"say \\"hello\\""'

    def test_single_quoted_string(self):
        """Test single quoted string to_source."""
        node = LSString("'single'")
        assert node.to_source() == "'single'"


class TestToSourceEdgeCases:
    """Test to_source() edge cases."""

    def test_bareword_with_hyphen(self):
        """Test bareword with hyphen to_source."""
        node = LSBareWord("my-plugin-name")
        assert node.to_source() == "my-plugin-name"

    def test_bareword_with_underscore(self):
        """Test bareword with underscore to_source."""
        node = LSBareWord("my_field_name")
        assert node.to_source() == "my_field_name"

    def test_bareword_starting_with_number(self):
        """Test bareword starting with number to_source."""
        node = LSBareWord("123field")
        assert node.to_source() == "123field"

    def test_selector_simple(self):
        """Test simple selector to_source."""
        node = SelectorNode("[field]")
        assert node.to_source() == "[field]"

    def test_selector_nested(self):
        """Test nested selector to_source."""
        node = SelectorNode("[field][subfield][nested]")
        assert node.to_source() == "[field][subfield][nested]"

    def test_regexp_simple_pattern(self):
        """Test simple regexp pattern to_source."""
        node = Regexp("/test/")
        assert node.to_source() == "/test/"

    def test_regexp_complex_pattern(self):
        """Test complex regexp pattern to_source."""
        node = Regexp(r"/^[A-Z][a-z]+\d{2,4}$/")
        assert node.to_source() == r"/^[A-Z][a-z]+\d{2,4}$/"

    def test_array_with_single_element(self):
        """Test array with single element to_source."""
        arr = Array((LSString('"only"'),))
        source = arr.to_source()
        assert source == '["only"]'


class TestBooleanExpressionToSource:
    """Test BooleanExpression.to_source()."""

    def test_boolean_expression_and(self):
        """Test BooleanExpression with 'and' operator."""
        from logstash_parser import parse_logstash_config

        config = """
        filter {
            if [field1] and [field2] {
                mutate { }
            }
        }
        """
        ast = parse_logstash_config(config)
        # Get the if condition from Branch
        branch = ast.children[0].children[0]  # Branch
        assert isinstance(branch, Branch)
        if_condition = branch.children[0]  # IfCondition
        expr = if_condition.expr  # BooleanExpression
        assert isinstance(expr, BooleanExpression)

        # Test to_source() - 必须能直接调用
        source = expr.to_source()
        assert "and" in source
        assert "[field1]" in source
        assert "[field2]" in source

    def test_boolean_expression_or(self):
        """Test BooleanExpression with 'or' operator."""
        from logstash_parser import parse_logstash_config

        config = """
        filter {
            if [status] == 200 or [status] == 201 {
                mutate { }
            }
        }
        """
        ast = parse_logstash_config(config)
        branch = ast.children[0].children[0]  # Branch
        assert isinstance(branch, Branch)
        if_condition = branch.children[0]  # IfCondition
        expr = if_condition.expr  # BooleanExpression
        assert isinstance(expr, BooleanExpression)

        # Test to_source() - 必须能直接调用
        source = expr.to_source()
        assert "or" in source
        assert "200" in source
        assert "201" in source

    def test_boolean_expression_complex(self):
        """Test complex nested BooleanExpression."""
        from logstash_parser import parse_logstash_config

        config = """
        filter {
            if ([status] >= 200 and [status] < 300) or [status] == 304 {
                mutate { }
            }
        }
        """
        ast = parse_logstash_config(config)
        branch = ast.children[0].children[0]  # Branch
        assert isinstance(branch, Branch)
        if_condition = branch.children[0]  # IfCondition
        expr = if_condition.expr  # BooleanExpression
        assert isinstance(expr, BooleanExpression)

        # Test to_source() - 必须能直接调用
        source = expr.to_source()
        assert "and" in source or "or" in source
        assert "200" in source or "300" in source


class TestToSourceWithParsedNodes:
    """Test to_source() returns original text for parsed nodes."""

    def test_hash_from_parsed_config(self):
        """Test Hash.to_source() returns original text when parsed."""
        from logstash_parser import parse_logstash_config

        config = """
        filter {
            mutate {
                add_field => { "key1" => "value1" "key2" => 100 }
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]  # Plugin
        assert isinstance(plugin, Plugin)
        attr = plugin.children[0]  # Attribute
        hash_node = attr.value  # Hash

        # Parsed node should return original source text
        source = hash_node.to_source()
        assert isinstance(source, str)
        assert "key1" in source
        assert "value1" in source

    def test_attribute_from_parsed_config(self):
        """Test Attribute.to_source() returns original text when parsed."""
        from logstash_parser import parse_logstash_config

        config = """
        filter {
            mutate {
                add_field => { "test" => "value" }
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]  # Plugin
        attr = plugin.children[0]  # Attribute

        # Parsed node should return original source text
        source = attr.to_source()
        assert isinstance(source, str)
        assert "add_field" in source
        assert "=>" in source

    def test_plugin_from_parsed_config(self):
        """Test Plugin.to_source() returns original text when parsed."""
        from logstash_parser import parse_logstash_config

        config = """
        filter {
            mutate {
                add_field => { "test" => "value" }
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]  # Plugin

        # Parsed node should return original source text
        source = plugin.to_source()
        assert isinstance(source, str)
        assert "mutate" in source
        assert "add_field" in source


class TestToSourceFallback:
    """Test to_source() fallback to to_logstash() for manually created nodes."""

    def test_hash_fallback_to_logstash(self):
        """Test Hash.to_source() falls back to to_logstash() when no source text."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))

        # Manually created node has no source text, should fallback to to_logstash()
        source = hash_node.to_source()
        assert isinstance(source, str)
        assert '"key"' in source
        assert '"value"' in source
        assert "=>" in source

    def test_attribute_fallback_to_logstash(self):
        """Test Attribute.to_source() falls back to to_logstash() when no source text."""
        attr = Attribute(LSBareWord("port"), Number(5044))

        # Manually created node has no source text, should fallback to to_logstash()
        source = attr.to_source()
        assert isinstance(source, str)
        assert "port" in source
        assert "5044" in source
        assert "=>" in source

    def test_plugin_fallback_to_logstash(self):
        """Test Plugin.to_source() falls back to to_logstash() when no source text."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))

        # Manually created node has no source text, should fallback to to_logstash()
        source = plugin.to_source()
        assert isinstance(source, str)
        assert "beats" in source
        assert "port" in source
        assert "5044" in source

    def test_method_call_to_source_fallback(self):
        """Test method call to_source falls back to to_logstash."""
        args = (LSString('"test"'),)
        node = MethodCall("upper", args)

        result = node.to_source()
        assert result == 'upper("test")'

    def test_method_call_to_source_from_condition(self):
        """Test method call to_source from parsed condition."""
        config = """filter {
    if [x] == upper([field]) {
        mutate { }
    }
}"""
        ast = parse_logstash_config(config)

        # Get the method call from condition
        branch = ast.children[0].children[0]
        if_cond = branch.children[0]
        # The expression contains the method_call
        source = if_cond.to_source()
        assert isinstance(source, str)
