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
    Number,
    Plugin,
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
