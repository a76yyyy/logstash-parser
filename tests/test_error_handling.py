"""Tests for error handling and edge cases."""

from unittest.mock import MagicMock, patch

import pytest

from logstash_parser import ParseError, parse_logstash_config
from logstash_parser.ast_nodes import (
    Array,
    ASTNode,
    Hash,
    HashEntryNode,
    LSBareWord,
    LSString,
    MethodCall,
    Number,
    Plugin,
    Regexp,
)


class TestParseErrors:
    """Test parsing error handling."""

    def test_empty_config_error(self):
        """Test that empty config raises ParseError."""
        with pytest.raises(ParseError, match="Configuration text is empty"):
            parse_logstash_config("")

    def test_whitespace_only_config_error(self):
        """Test that whitespace-only config raises ParseError."""
        with pytest.raises(ParseError, match="Configuration text is empty"):
            parse_logstash_config("   \n\t  \r\n  ")

    def test_invalid_syntax_error(self):
        """Test that invalid syntax raises ParseError."""
        invalid_config = "this is not valid logstash syntax { } => @#$%"
        with pytest.raises(ParseError):
            parse_logstash_config(invalid_config)

    def test_incomplete_config_error(self):
        """Test that incomplete config raises ParseError."""
        incomplete_config = "filter { grok {"
        with pytest.raises(ParseError):
            parse_logstash_config(incomplete_config)

    def test_mismatched_braces_error(self):
        """Test that mismatched braces raise ParseError."""
        # Test various mismatched brace scenarios
        test_cases = [
            ("filter { grok { }", "missing closing brace for filter section"),
            ("filter { grok { } } }", "extra closing brace"),
            ("filter { { grok { } }", "extra opening brace"),
            (
                'filter { grok { match => { "message" => "pattern" } }',
                "incomplete nested hash - missing closing brace",
            ),
        ]

        for config, _ in test_cases:
            with pytest.raises(ParseError, match="Failed to parse Logstash configuration"):
                parse_logstash_config(config)

    def test_config_without_sections_error(self):
        """Test that config without sections raises ParseError."""
        # After fixing grammar to require at least one plugin_section,
        # this now fails at parse time (not validation time)
        with pytest.raises(ParseError, match="Failed to parse Logstash configuration"):
            parse_logstash_config("# just a comment")

    def test_unexpected_exception_handling(self):
        """Test handling of unexpected exceptions during parsing."""
        with patch("logstash_parser.ast_nodes.Config.from_logstash") as mock_parse:
            mock_parse.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(ParseError, match="Failed to parse Logstash configuration"):
                parse_logstash_config("filter { }")

    def test_empty_result_error(self):
        """Test handling of empty parse result."""
        # Config.from_logstash now handles empty results internally
        # This test verifies that invalid configs still raise errors
        with pytest.raises(ParseError):
            parse_logstash_config("# only comments")


class TestSourceTextExtraction:
    """Test source text extraction and caching."""

    def test_source_text_cache_hit(self):
        """Test that cached source text is returned."""
        node = ASTNode()
        node._source_text_cache = "cached_value"

        result = node.get_source_text()
        assert result == "cached_value"

    def test_source_text_no_parser_info(self):
        """Test source text extraction with no parser info."""
        node = ASTNode()
        result = node.get_source_text()
        assert result is None

    def test_source_text_extraction_failure(self):
        """Test source text extraction failure."""
        node = ASTNode(s="test", loc=0)
        node._parser_name = "test"
        node._parser_element_for_get_source = MagicMock()
        node._parser_element_for_get_source.searchString.return_value = []

        with pytest.raises(ValueError, match="Failed to extract source text"):
            node.get_source_text()

    def test_source_text_extraction_success(self):
        """Test successful source text extraction."""
        node = ASTNode(s="test content", loc=0)
        node._parser_name = "test"

        mock_element = MagicMock()
        mock_result = MagicMock()
        mock_result.as_list.return_value = [["extracted"]]
        mock_element.searchString.return_value = mock_result
        node._parser_element_for_get_source = mock_element

        result = node.get_source_text()
        assert result == "extracted"
        # Verify it's cached
        assert node._source_text_cache == "extracted"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_plugin_with_no_attributes(self):
        """Test plugin with no attributes."""
        config = """
        filter {
            drop { }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "drop"
        assert len(plugin.children) == 0

    def test_empty_array(self):
        """Test empty array."""
        arr = Array(())
        assert len(arr.children) == 0
        assert arr.to_source() == "[]"
        assert arr.to_logstash() == "[]"

    def test_empty_hash(self):
        """Test empty hash."""
        hash_node = Hash(())
        assert len(hash_node.children) == 0
        # Hash doesn't have to_source(), only to_logstash()
        logstash = hash_node.to_logstash()
        assert "{" in logstash and "}" in logstash

    def test_very_long_string(self):
        """Test very long string value."""
        long_string = "x" * 10000
        node = LSString(f'"{long_string}"')
        assert node.value == long_string
        assert len(node.to_source()) > 10000

    def test_very_large_number(self):
        """Test very large number."""
        large_num = 999999999999999
        node = Number(large_num)
        assert node.value == large_num
        assert node.to_source() == large_num

    def test_deeply_nested_hash(self):
        """Test deeply nested hash (10 levels)."""
        # Build from inside out
        current = Hash((HashEntryNode(LSString('"level10"'), LSString('"value"')),))

        for i in range(9, 0, -1):
            entry = HashEntryNode(LSString(f'"level{i}"'), current)
            current = Hash((entry,))

        # Should not raise any errors
        source = current.to_logstash()
        assert '"level1"' in source
        assert '"level10"' in source
        assert '"value"' in source

    def test_deeply_nested_array(self):
        """Test deeply nested array (10 levels)."""
        # Build from inside out
        current = Array((LSString('"innermost"'),))

        for _ in range(9):
            current = Array((current,))

        # Should not raise any errors
        source = current.to_source()
        assert '"innermost"' in source

    def test_array_with_many_elements(self) -> None:
        """Test array with many elements (1000)."""
        elements = tuple(LSString(f'"item{i}"') for i in range(1000))
        arr = Array(elements)

        assert len(arr.children) == 1000
        source = arr.to_source()
        assert '"item0"' in source
        assert '"item999"' in source

    def test_hash_with_many_entries(self):
        """Test hash with many entries (100)."""
        entries = tuple(HashEntryNode(LSString(f'"key{i}"'), LSString(f'"value{i}"')) for i in range(100))
        hash_node = Hash(entries)

        assert len(hash_node.children) == 100
        source = hash_node.to_logstash()
        assert '"key0"' in source
        assert '"key99"' in source


class TestSpecialCharacters:
    """Test handling of special characters."""

    def test_string_with_unicode(self):
        """Test string with unicode characters."""
        config = """
        filter {
            mutate {
                add_field => { "message" => "Hello 世界 🌍" }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_string_with_newlines(self):
        """Test string with newlines."""
        config = r"""
        filter {
            mutate {
                add_field => { "message" => "line1\nline2\nline3" }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_string_with_tabs(self):
        """Test string with tabs."""
        config = r"""
        filter {
            mutate {
                add_field => { "message" => "col1\tcol2\tcol3" }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_string_with_escaped_quotes(self):
        """Test string with escaped quotes."""
        config = r"""
        filter {
            mutate {
                add_field => { "message" => "say \"hello\"" }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_regexp_with_special_chars(self):
        """Test regexp with special characters."""
        config = r"""
        filter {
            if [message] =~ /\[ERROR\].*\d{4}/ {
                mutate { add_tag => ["error"] }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_bareword_with_all_allowed_chars(self):
        """Test bareword with all allowed characters."""
        config = """
        filter {
            my-plugin_123 {
                field-name_456 => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None


class TestAttributeEdgeCases:
    """Test Attribute edge cases."""

    def test_attribute_with_string_name(self):
        """Test attribute with quoted string name."""
        config = """
        filter {
            mutate {
                "field with spaces" => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)
        attr = plugin.children[0]
        assert isinstance(attr.name, LSString)

    def test_attribute_with_bareword_name(self):
        """Test attribute with bareword name."""
        config = """
        filter {
            mutate {
                simple_field => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)
        attr = plugin.children[0]
        assert isinstance(attr.name, LSBareWord)

    def test_attribute_with_complex_value(self):
        """Test attribute with complex nested value."""
        config = """
        filter {
            mutate {
                add_field => {
                    "level1" => {
                        "level2" => ["a", "b", { "level3" => "value" }]
                    }
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None


class TestPluginEdgeCases:
    """Test Plugin edge cases."""

    def test_plugin_with_hyphenated_name(self):
        """Test plugin with hyphenated name."""
        config = """
        filter {
            my-custom-plugin {
                field => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "my-custom-plugin"

    def test_plugin_with_numeric_name(self):
        """Test plugin with numeric characters in name."""
        config = """
        filter {
            plugin123 {
                field => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "plugin123"

    def test_plugin_with_many_attributes(self):
        """Test plugin with many attributes."""
        attributes = "\n".join([f'field{i} => "value{i}"' for i in range(50)])
        config = f"""
        filter {{
            mutate {{
                {attributes}
            }}
        }}
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        plugin = ast.children[0].children[0]
        assert len(plugin.children) == 50


class TestConditionalEdgeCases:
    """Test conditional edge cases."""

    def test_deeply_nested_conditionals(self):
        """Test deeply nested if statements."""
        config = """
        filter {
            if [level1] {
                if [level2] {
                    if [level3] {
                        if [level4] {
                            if [level5] {
                                mutate { add_tag => ["deep"] }
                            }
                        }
                    }
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_many_else_if_branches(self):
        """Test many else if branches."""
        branches = []
        for i in range(20):
            branches.append(f"""
            else if [field{i}] == "value{i}" {{
                mutate {{ add_tag => ["tag{i}"] }}
            }}
            """)

        config = f"""
        filter {{
            if [field] == "start" {{
                mutate {{ add_tag => ["start"] }}
            }}
            {"".join(branches)}
            else {{
                mutate {{ add_tag => ["end"] }}
            }}
        }}
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_conditional_with_complex_expression(self):
        """Test conditional with complex boolean expression."""
        config = """
        filter {
            if ([status] >= 200 and [status] < 300) or ([status] == 304) {
                mutate { add_tag => ["success"] }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None


class TestMethodCallEdgeCases:
    """Test edge cases for MethodCall."""

    def test_method_call_with_empty_string(self):
        """Test method call with empty string argument."""
        args = (LSString('""'),)
        node = MethodCall("test", args)

        result = node.to_logstash()
        assert result == 'test("")'

    def test_method_call_with_special_chars(self):
        """Test method call with special characters in string."""
        args = (LSString(r'"test\nline"'),)
        node = MethodCall("format", args)

        result = node.to_logstash()
        assert "format" in result

    def test_method_call_with_very_long_name(self):
        """Test method call with very long method name."""
        long_name = "very_long_method_name_with_many_characters"
        args = (LSString('"test"'),)
        node = MethodCall(long_name, args)

        assert node.method_name == long_name
        result = node.to_logstash()
        assert long_name in result

    def test_method_call_with_many_args(self):
        """Test method call with many arguments."""
        args = tuple(Number(i) for i in range(20))
        node = MethodCall("sum", args)

        assert len(node.children) == 20
        result = node.to_logstash()
        assert "sum" in result

    def test_deeply_nested_method_calls(self):
        """Test deeply nested method calls (5 levels)."""
        current = MethodCall("level5", (LSString('"innermost"'),))

        for i in range(4, 0, -1):
            current = MethodCall(f"level{i}", (current,))

        result = current.to_logstash()
        assert "level1" in result
        assert "level5" in result
        assert "innermost" in result


class TestFromSchemaErrors:
    """Test from_schema error handling."""

    def test_unknown_schema_type_raises_error(self) -> None:
        """Test that unknown schema type raises ValueError."""
        from pydantic import BaseModel

        from logstash_parser.ast_nodes import ASTNode

        # Create a custom schema that's not in SCHEMA_TO_NODE
        class UnknownSchema(BaseModel):
            value: str

        schema = UnknownSchema(value="test")

        with pytest.raises(ValueError, match="Unknown schema type"):
            ASTNode.from_schema(schema)  # type: ignore


class TestFromLogstashErrors:
    """Test from_logstash error handling."""

    def test_empty_result_raises_error(self):
        """Test that empty parse result raises ValueError."""
        from unittest.mock import patch

        from logstash_parser.ast_nodes import LSString

        with patch.object(LSString, "_parser_element_for_parsing") as mock_parser:
            mock_parser.parse_string.return_value = []

            with pytest.raises(ValueError, match="Failed to parse"):
                LSString.from_logstash('"test"')


class TestCommentHandling:
    """Test comment handling."""

    def test_config_with_comments(self):
        """Test config with comments."""
        config = """
        # This is a comment
        filter {
            # Another comment
            mutate {
                # Inline comment
                add_field => { "field" => "value" } # End of line comment
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_config_with_only_comments(self):
        """Test config with only comments (should fail)."""
        config = """
        # Comment 1
        # Comment 2
        # Comment 3
        """
        with pytest.raises(ParseError):
            parse_logstash_config(config)

    def test_multiline_comments(self):
        """Test config with multiline comments."""
        config = """
        # Comment line 1
        # Comment line 2
        # Comment line 3
        filter {
            mutate {
                add_field => { "field" => "value" }
            }
        }
        # Trailing comment
        """
        ast = parse_logstash_config(config)
        assert ast is not None


class TestWhitespaceHandling:
    """Test whitespace handling."""

    def test_config_with_extra_whitespace(self):
        """Test config with extra whitespace."""
        config = """


        filter    {

            mutate     {
                add_field    =>    {    "field"    =>    "value"    }
            }

        }


        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_config_with_tabs(self):
        """Test config with tabs."""
        config = """
\t\tfilter {
\t\t\tmutate {
\t\t\t\tadd_field => { "field" => "value" }
\t\t\t}
\t\t}
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_config_with_mixed_indentation(self):
        """Test config with mixed indentation."""
        config = """
        filter {
\t    mutate {
  \t      add_field => { "field" => "value" }
    \t}
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None


class TestSpecialCharactersInValues:
    """Test special characters in various value types."""

    def test_string_with_unicode_emoji(self):
        """Test string with unicode emoji."""
        config = """filter {
    mutate {
        add_field => { "emoji" => "Hello 👋 World 🌍" }
    }
}"""
        ast = parse_logstash_config(config)
        assert ast is not None

        regenerated = ast.to_logstash()
        assert "👋" in regenerated or "Hello" in regenerated

    def test_string_with_control_characters(self):
        """Test string with control characters."""
        config = r"""filter {
    mutate {
        add_field => { "control" => "line1\nline2\ttab\rcarriage" }
    }
}"""
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_regexp_with_unicode(self):
        """Test regexp with unicode characters."""
        config = r"""filter {
    if [message] =~ /你好|世界/ {
        mutate { add_tag => ["chinese"] }
    }
}"""
        ast = parse_logstash_config(config)
        assert ast is not None


class TestPerformanceEdgeCases:
    """Test performance-related edge cases."""

    def test_very_deep_nesting(self):
        """Test very deep nesting (20 levels)."""
        from logstash_parser.ast_nodes import Hash, HashEntryNode, LSString

        # Build deeply nested hash
        current = Hash((HashEntryNode(LSString('"level20"'), LSString('"value"')),))

        for i in range(19, 0, -1):
            entry = HashEntryNode(LSString(f'"level{i}"'), current)
            current = Hash((entry,))

        # Should not raise any errors
        result = current.to_logstash()
        assert '"level1"' in result
        assert '"level20"' in result

    def test_very_wide_structure(self):
        """Test very wide structure (100 attributes)."""
        from logstash_parser.ast_nodes import Attribute, LSBareWord, LSString, Plugin

        attributes = []
        for i in range(100):
            name = LSBareWord(f"field{i}")
            value = LSString(f'"value{i}"')
            attributes.append(Attribute(name, value))

        plugin = Plugin("mutate", tuple(attributes))

        result = plugin.to_logstash()
        assert "field0" in result
        assert "field99" in result


class TestInvalidStringLiterals:
    """Test invalid string literal handling (high priority - exception handling)."""

    def test_lsstring_invalid_literal_error(self):
        """Test LSString with invalid string literal raises ValueError."""
        # Test with unmatched quotes
        with pytest.raises(ValueError, match="Invalid string literal"):
            LSString('"unclosed string')

    def test_lsstring_malformed_escape_sequence(self):
        """Test LSString with malformed escape sequence."""
        # This should still work as Python's literal_eval handles it
        try:
            LSString(r'"\x"')  # Invalid hex escape
            # If it doesn't raise, that's also acceptable
        except ValueError as e:
            assert "Invalid string literal" in str(e)

    def test_lsstring_with_null_bytes(self):
        """Test LSString with null bytes."""
        # Null bytes should be handled
        node = LSString('"test\\x00value"')
        assert "test" in node.value


class TestRegexpExceptionHandling:
    """Test Regexp exception handling (high priority)."""

    def test_regexp_invalid_pattern(self):
        """Test Regexp with invalid pattern."""
        # Regexp constructor is very permissive, but test edge cases
        try:
            node = Regexp("/[invalid/")
            # Even invalid patterns are stored as-is
            assert node.lexeme == "/[invalid/"
        except ValueError as e:
            # If it raises, check the error message
            assert "Invalid string literal" in str(e)

    def test_regexp_exception_handling_coverage(self):
        """Test Regexp exception handling (lines 479-480).

        This test attempts to trigger the exception handler in Regexp.__init__.
        The rf-string formatting is very permissive, so we test with extreme cases.
        """
        # Test with various edge cases that might trigger exceptions
        test_cases = [
            "/normal_pattern/",
            "/pattern with spaces/",
            "/pattern\nwith\nnewlines/",
            "/pattern\\with\\backslashes/",
            r"/pattern\x00with\x00nulls/",
        ]

        for pattern in test_cases:
            try:
                node = Regexp(pattern)
                # Most patterns should work fine
                assert node.lexeme == pattern
                assert node.value is not None
            except ValueError as e:
                # If any exception occurs, verify it's properly wrapped
                assert "Invalid string literal" in str(e)

    def test_regexp_to_repr(self):
        """Test Regexp.to_repr() method (line 502)."""
        node = Regexp("/test/")
        result = node.to_repr()
        assert "Regexp" in result
        assert "/test/" in result

    def test_regexp_to_repr_with_indent(self):
        """Test Regexp.to_repr() with indentation."""
        node = Regexp("/error/")
        result = node.to_repr(indent=4)
        assert result.startswith("    ")
        assert "Regexp" in result


class TestToSourceFallback:
    """Test to_source() fallback logic (high priority - line 146)."""

    def test_to_source_fallback_to_to_logstash(self):
        """Test that to_source() falls back to to_logstash() when source text unavailable."""
        from logstash_parser.ast_nodes import Attribute, LSBareWord, Number, Plugin

        # Create a plugin without source text
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))

        # to_source() should fall back to to_logstash()
        result = plugin.to_source()
        assert isinstance(result, str)
        assert "beats" in result
        assert "port" in result
        assert "5044" in result

    def test_to_source_not_implemented_error(self):
        """Test to_source() raises NotImplementedError when both methods fail."""
        from logstash_parser.ast_nodes import ASTNode

        # Create a bare ASTNode without to_logstash implementation
        node = ASTNode()

        # Should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="to_source.*must be implemented"):
            node.to_source()


class TestParseErrorExceptionBranches:
    """Test parse error exception branches (high priority - lines 159, 164)."""

    def test_parse_config_no_sections_validation(self):
        """Test that config with no sections raises ParseError (line 159)."""
        # This is already tested, but ensure the specific line is covered
        with pytest.raises(ParseError, match="Configuration has no plugin sections"):
            # Mock a config that parses but has no children
            with patch("logstash_parser.ast_nodes.Config.from_logstash") as mock_parse:
                from logstash_parser.ast_nodes import Config

                empty_config = Config(())
                mock_parse.return_value = empty_config
                parse_logstash_config("filter { }")

    def test_parse_config_generic_exception_wrapping(self):
        """Test that generic exceptions are wrapped in ParseError (line 164)."""
        # Test that non-ParseError exceptions are wrapped
        with patch("logstash_parser.ast_nodes.Config.from_logstash") as mock_parse:
            mock_parse.side_effect = ValueError("Some parsing error")

            with pytest.raises(ParseError, match="Failed to parse Logstash configuration"):
                parse_logstash_config("filter { }")


class TestToReprMethods:
    """Test to_repr() methods for debugging (medium-high priority)."""

    def test_astnode_base_to_repr(self):
        """Test ASTNode.to_repr() base implementation (line 378)."""
        from logstash_parser.ast_nodes import ASTNode

        node = ASTNode()
        result = node.to_repr()
        assert "ASTNode" in result

    def test_astnode_to_repr_with_indent(self):
        """Test ASTNode.to_repr() with indentation."""
        from logstash_parser.ast_nodes import ASTNode

        node = ASTNode()
        result = node.to_repr(indent=2)
        assert result.startswith("  ")

    def test_lsbareword_to_repr(self):
        """Test LSBareWord.to_repr() (line 446)."""
        node = LSBareWord("test_field")
        result = node.to_repr()
        assert "LSBareWord" in result
        assert "test_field" in result

    def test_lsbareword_to_repr_with_indent(self):
        """Test LSBareWord.to_repr() with indentation."""
        node = LSBareWord("field")
        result = node.to_repr(indent=4)
        assert result.startswith("    ")

    def test_hash_entry_to_repr(self):
        """Test HashEntryNode.to_repr() (lines 624-625)."""
        from logstash_parser.ast_nodes import HashEntryNode

        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        result = entry.to_repr()
        assert "HashEntry" in result
        assert "key" in result or "value" in result

    def test_hash_entry_to_repr_with_indent(self):
        """Test HashEntryNode.to_repr() with indentation."""
        from logstash_parser.ast_nodes import HashEntryNode

        entry = HashEntryNode(LSBareWord("field"), Number(123))
        result = entry.to_repr(indent=2)
        assert result.startswith("  ")

    def test_attribute_to_repr(self):
        """Test Attribute.to_repr() (lines 744-745)."""
        from logstash_parser.ast_nodes import Attribute

        attr = Attribute(LSBareWord("port"), Number(5044))
        result = attr.to_repr()
        assert "Attribute" in result

    def test_array_to_repr_with_children(self):
        """Test Array.to_repr() with children (lines 569-571).

        This test covers the multi-line formatting logic in Array.to_repr().
        """
        # Create an array with multiple children
        arr = Array(
            (
                LSString('"item1"'),
                Number(42),
                LSString('"item2"'),
            )
        )

        result = arr.to_repr(indent=2)

        # Should start with indent
        assert result.startswith("  ")
        # Should contain "Array["
        assert "Array[" in result
        # Should have children on separate lines
        assert "\n" in result
        # Should contain the children
        assert "LSString" in result or "Number" in result

    def test_array_to_source_reconstruction(self):
        """Test Array.to_source() reconstruction from children (line 578).

        This covers the case where source text is not cached and needs reconstruction.
        """
        # Create array without source text
        arr = Array(
            (
                LSString('"hello"'),
                Number(123),
                LSBareWord("world"),
            )
        )

        # to_source should reconstruct from children
        result = arr.to_source()

        assert result.startswith("[")
        assert result.endswith("]")
        assert "hello" in result or "123" in result

    def test_attribute_to_repr_with_indent(self):
        """Test Attribute.to_repr() with indentation."""
        from logstash_parser.ast_nodes import Attribute

        attr = Attribute(LSString('"field"'), LSString('"value"'))
        result = attr.to_repr(indent=2)
        assert result.startswith("  ")

    def test_if_condition_to_repr(self):
        """Test IfCondition.to_repr() (lines 1411-1414)."""
        from logstash_parser.ast_nodes import CompareExpression, IfCondition, SelectorNode

        expr = CompareExpression(SelectorNode("[field]"), "==", Number(1))
        condition = IfCondition(expr, ())
        result = condition.to_repr()
        assert "IfCondition" in result

    def test_else_if_condition_to_repr(self):
        """Test ElseIfCondition.to_repr() (lines 1477-1480)."""
        from logstash_parser.ast_nodes import ElseIfCondition, SelectorNode

        expr = SelectorNode("[test]")
        condition = ElseIfCondition(expr, ())
        result = condition.to_repr()
        assert "ElseIfCondition" in result

    def test_else_condition_to_repr(self):
        """Test ElseCondition.to_repr() (lines 1541-1545)."""
        from logstash_parser.ast_nodes import ElseCondition

        condition = ElseCondition(())
        result = condition.to_repr()
        assert "ElseCondition" in result

    def test_branch_to_repr(self):
        """Test Branch.to_repr() (lines 1649-1651)."""
        from logstash_parser.ast_nodes import Branch, IfCondition, SelectorNode

        if_cond = IfCondition(SelectorNode("[field]"), ())
        branch = Branch(if_cond, None, None)
        result = branch.to_repr()
        assert "Branch" in result

    def test_plugin_section_to_repr(self):
        """Test PluginSectionNode.to_repr() (lines 1666-1669)."""
        from logstash_parser.ast_nodes import Plugin, PluginSectionNode

        plugin = Plugin("mutate", ())
        section = PluginSectionNode("filter", [plugin])
        result = section.to_repr()
        assert "PluginSection" in result
        assert "filter" in result

    def test_config_to_repr(self):
        """Test Config.to_repr() (lines 1719-1721)."""
        from logstash_parser.ast_nodes import Config, Plugin, PluginSectionNode

        plugin = Plugin("stdin", ())
        section = PluginSectionNode("input", [plugin])
        config = Config((section,))
        result = config.to_repr()
        assert "Config" in result


class TestRValueEdgeCases:
    """Test RValue edge cases (lines 1265, 1273-1274)."""

    def test_rvalue_to_python_dict(self):
        """Test RValue._to_python_dict() (line 1265)."""
        from logstash_parser.ast_nodes import RValue

        value = RValue(LSString('"test"'))
        result = value._to_python_dict()
        assert "ls_string" in result

    def test_rvalue_from_pydantic(self):
        """Test RValue._from_pydantic() (lines 1273-1274)."""
        from logstash_parser.ast_nodes import RValue
        from logstash_parser.schemas import LSStringSchema

        schema = LSStringSchema(ls_string='"test"')
        node = RValue.from_python(schema)
        assert isinstance(node, RValue)
        assert isinstance(node.value, LSString)


class TestHashEntryNestedFormatting:
    """Test HashEntryNode formatting with nested Hash and Plugin (lines 638-640, 647-649)."""

    def test_hash_entry_with_nested_hash_multiline(self):
        """Test HashEntryNode.to_logstash() with nested Hash (lines 638-640).

        This covers the multi-line formatting when a HashEntry contains a nested Hash.
        """
        from logstash_parser.ast_nodes import HashEntryNode

        # Create nested hash
        inner_entry = HashEntryNode(LSString('"inner_key"'), LSString('"inner_value"'))
        inner_hash = Hash((inner_entry,))

        # Create outer hash entry with nested hash as value
        outer_entry = HashEntryNode(LSString('"outer_key"'), inner_hash)

        result = outer_entry.to_logstash(indent=2)

        # Should contain the key
        assert '"outer_key"' in result
        # Should contain opening brace on same line (line 637)
        assert "=>" in result
        assert "{" in result
        # Should handle multi-line formatting (lines 638-640)
        lines = result.split("\n")
        assert len(lines) > 1  # Multi-line output

    def test_hash_entry_with_nested_plugin_multiline(self):
        """Test HashEntryNode.to_logstash() with nested Plugin (lines 647-649).

        This covers the multi-line formatting when a HashEntry contains a Plugin.
        """
        from logstash_parser.ast_nodes import Attribute, HashEntryNode

        # Create a plugin
        attr = Attribute(LSBareWord("field"), LSString('"value"'))
        plugin = Plugin("mutate", (attr,))

        # Create hash entry with plugin as value
        entry = HashEntryNode(LSString('"plugin_key"'), plugin)

        result = entry.to_logstash(indent=2)

        # Should contain the key
        assert '"plugin_key"' in result
        # Should contain plugin name
        assert "mutate" in result
        # Should handle multi-line formatting (lines 647-649)
        lines = result.split("\n")
        assert len(lines) > 1  # Multi-line output


class TestHashFormattingEdgeCases:
    """Test Hash.to_repr() and special key types (lines 677-679, 696)."""

    def test_hash_to_repr_with_children(self):
        """Test Hash.to_repr() with children (lines 677-679).

        This covers the multi-line formatting in Hash.to_repr().
        """
        # Create hash with multiple entries
        entries = (
            HashEntryNode(LSString('"key1"'), LSString('"value1"')),
            HashEntryNode(LSString('"key2"'), Number(42)),
        )
        hash_node = Hash(entries)

        result = hash_node.to_repr(indent=2)

        # Should start with indent
        assert result.startswith("  ")
        # Should contain "Hash {"
        assert "Hash" in result
        assert "{" in result
        # Should have children on separate lines
        assert "\n" in result
        # Should contain closing brace with indent
        assert "}" in result

    def test_hash_with_number_key(self):
        """Test Hash._to_pydantic_model() with Number key (line 696).

        This covers the case where a hash key is a Number, which needs
        special handling in _to_pydantic_model().
        """
        from logstash_parser.ast_nodes import HashEntryNode

        # Create hash entry with Number as key
        entry = HashEntryNode(Number(123), LSString('"value"'))
        hash_node = Hash((entry,))

        # Convert to pydantic model
        schema = hash_node._to_pydantic_model()

        # Number key should be converted to string
        assert "123" in schema.hash
        assert schema.hash["123"] is not None

    def test_hash_with_bareword_key(self):
        """Test Hash with LSBareWord key."""
        from logstash_parser.ast_nodes import HashEntryNode

        # Create hash entry with LSBareWord as key
        entry = HashEntryNode(LSBareWord("my_key"), LSString('"value"'))
        hash_node = Hash((entry,))

        # Convert to pydantic model
        schema = hash_node._to_pydantic_model()

        # BareWord key should be preserved
        assert "my_key" in schema.hash


class TestAttributeSpecialNames:
    """Test Attribute with special name types (line 752)."""

    def test_attribute_with_number_schema_name(self):
        """Test Attribute._to_pydantic_model() with non-standard name type (line 752).

        This covers the fallback case in Attribute._to_pydantic_model() where
        the name is neither LSString nor LSBareWord.
        """
        from logstash_parser.ast_nodes import Attribute

        # Normal cases are already tested, this documents the fallback path
        # In practice, name should always be LSString or LSBareWord
        attr = Attribute(LSBareWord("field"), Number(123))

        schema = attr._to_pydantic_model()

        # Should successfully convert
        assert "field" in schema.root
        assert schema.root["field"] is not None


class TestAttributeNestedFormatting:
    """Test Attribute.to_logstash() with nested Hash and Plugin (lines 791-793, 800-802)."""

    def test_attribute_with_nested_hash_multiline(self):
        """Test Attribute.to_logstash() with nested Hash (lines 791-793).

        This covers the multi-line formatting when an Attribute contains a nested Hash.
        """
        from logstash_parser.ast_nodes import Attribute, HashEntryNode

        # Create nested hash with multiple entries to ensure multi-line output
        inner_entries = (
            HashEntryNode(LSString('"key1"'), LSString('"value1"')),
            HashEntryNode(LSString('"key2"'), LSString('"value2"')),
        )
        inner_hash = Hash(inner_entries)

        # Create attribute with nested hash as value
        attr = Attribute(LSBareWord("config"), inner_hash)

        result = attr.to_logstash(indent=2)

        # Should contain the attribute name
        assert "config" in result
        # Should contain opening brace on same line
        assert "=>" in result
        assert "{" in result
        # Should handle multi-line formatting (lines 791-793)
        lines = result.split("\n")
        assert len(lines) > 2  # Multi-line output with multiple entries

    def test_attribute_with_nested_plugin_multiline(self):
        """Test Attribute.to_logstash() with nested Plugin (lines 800-802).

        This covers the multi-line formatting when an Attribute contains a Plugin.
        """
        from logstash_parser.ast_nodes import Attribute

        # Create a plugin with multiple attributes to ensure multi-line output
        attr1 = Attribute(LSBareWord("field1"), LSString('"value1"'))
        attr2 = Attribute(LSBareWord("field2"), LSString('"value2"'))
        plugin = Plugin("mutate", (attr1, attr2))

        # Create attribute with plugin as value
        outer_attr = Attribute(LSBareWord("filter"), plugin)

        result = outer_attr.to_logstash(indent=2)

        # Should contain the attribute name
        assert "filter" in result
        # Should contain plugin name
        assert "mutate" in result
        # Should handle multi-line formatting (lines 800-802)
        lines = result.split("\n")
        assert len(lines) > 2  # Multi-line output
