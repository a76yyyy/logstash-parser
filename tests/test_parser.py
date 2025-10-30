"""Tests for the main parser functionality."""

import pytest

from logstash_parser import ParseError, parse_logstash_config


class TestBasicParsing:
    """Test basic parsing functionality."""

    def test_parse_simple_filter(self, simple_filter_config):
        """Test parsing a simple filter configuration."""
        ast = parse_logstash_config(simple_filter_config)
        assert ast is not None
        assert len(ast.children) == 1
        assert ast.children[0].plugin_type == "filter"

    def test_parse_simple_input(self, simple_input_config):
        """Test parsing a simple input configuration."""
        ast = parse_logstash_config(simple_input_config)
        assert ast is not None
        assert len(ast.children) == 1
        assert ast.children[0].plugin_type == "input"

    def test_parse_simple_output(self, simple_output_config):
        """Test parsing a simple output configuration."""
        ast = parse_logstash_config(simple_output_config)
        assert ast is not None
        assert len(ast.children) == 1
        assert ast.children[0].plugin_type == "output"

    def test_parse_full_config(self, full_config):
        """Test parsing a full configuration with input, filter, and output."""
        ast = parse_logstash_config(full_config)
        assert ast is not None
        assert len(ast.children) == 3

        plugin_types = {section.plugin_type for section in ast.children}
        assert plugin_types == {"input", "filter", "output"}

    def test_parse_empty_config(self):
        """Test parsing an empty configuration."""
        # Empty config should raise ParseError
        with pytest.raises(ParseError, match="Configuration text is empty"):
            parse_logstash_config("")

    def test_parse_invalid_syntax(self):
        """Test parsing invalid syntax."""
        # Completely invalid syntax that pyparsing cannot parse
        invalid_config = "this is not valid logstash syntax at all { } => @#$%"

        # Invalid syntax should raise ParseError
        with pytest.raises(ParseError):
            parse_logstash_config(invalid_config)

    def test_parse_multiple_sections_same_type(self):
        """Test parsing multiple sections of the same type."""
        config = """
        filter {
            grok {
                match => { "message" => "%{PATTERN1}" }
            }
        }

        filter {
            mutate {
                add_field => { "field" => "value" }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        assert len(ast.children) == 2
        assert all(section.plugin_type == "filter" for section in ast.children)


class TestConditionalParsing:
    """Test parsing conditional branches."""

    def test_parse_if_condition(self):
        """Test parsing if condition."""
        config = """
        filter {
            if [type] == "nginx" {
                grok {
                    match => { "message" => "%{PATTERN}" }
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        python_dict = ast.to_python()
        assert "filter" in python_dict

    def test_parse_if_else_condition(self):
        """Test parsing if-else condition."""
        config = """
        filter {
            if [type] == "nginx" {
                grok {
                    match => { "message" => "%{NGINX}" }
                }
            } else {
                mutate {
                    add_field => { "unknown" => "true" }
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_parse_if_elseif_else_condition(self, conditional_config):
        """Test parsing if-elseif-else condition."""
        ast = parse_logstash_config(conditional_config)
        assert ast is not None
        python_dict = ast.to_python()
        assert "filter" in python_dict

    def test_parse_nested_conditions(self):
        """Test parsing nested conditions."""
        config = """
        filter {
            if [type] == "nginx" {
                if [status] >= 400 {
                    mutate {
                        add_tag => ["error"]
                    }
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None


class TestExpressionParsing:
    """Test parsing expressions."""

    def test_parse_compare_expression(self):
        """Test parsing comparison expressions."""
        config = """
        filter {
            if [status] == 200 {
                mutate { add_tag => ["ok"] }
            }
            if [status] != 404 {
                mutate { add_tag => ["not_404"] }
            }
            if [status] >= 400 {
                mutate { add_tag => ["error"] }
            }
            if [status] <= 299 {
                mutate { add_tag => ["success"] }
            }
            if [status] > 500 {
                mutate { add_tag => ["server_error"] }
            }
            if [status] < 400 {
                mutate { add_tag => ["not_error"] }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_parse_boolean_expression(self, complex_expression_config):
        """Test parsing boolean expressions."""

        ast = parse_logstash_config(complex_expression_config)
        assert ast is not None

    def test_parse_regex_expression(self, regexp_config):
        """Test parsing regex expressions."""
        ast = parse_logstash_config(regexp_config)
        assert ast is not None

    def test_parse_in_expression(self):
        """Test parsing in expressions."""
        config = """
        filter {
            if [status] in [200, 201, 204] {
                mutate { add_tag => ["success"] }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_parse_not_in_expression(self):
        """Test parsing not in expressions."""
        config = """
        filter {
            if [status] not in [400, 500] {
                mutate { add_tag => ["not_error"] }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_parse_negative_expression(self):
        """Test parsing negative expressions."""
        config = """
        filter {
            if ![field] {
                mutate { add_tag => ["no_field"] }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None


class TestDataTypeParsing:
    """Test parsing different data types."""

    def test_parse_strings(self):
        """Test parsing strings."""
        config = """
        filter {
            mutate {
                add_field => {
                    "single" => 'single quoted'
                    "double" => "double quoted"
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_parse_numbers(self, number_boolean_config):
        """Test parsing numbers."""
        ast = parse_logstash_config(number_boolean_config)
        assert ast is not None
        python_dict = ast.to_python()
        assert "filter" in python_dict

    def test_parse_booleans(self, number_boolean_config):
        """Test parsing booleans."""
        ast = parse_logstash_config(number_boolean_config)
        assert ast is not None

    def test_parse_arrays(self, array_hash_config):
        """Test parsing arrays."""
        ast = parse_logstash_config(array_hash_config)
        assert ast is not None

    def test_parse_hashes(self, array_hash_config):
        """Test parsing hashes."""
        ast = parse_logstash_config(array_hash_config)
        assert ast is not None

    def test_parse_selectors(self, selector_config):
        """Test parsing field selectors."""
        ast = parse_logstash_config(selector_config)
        assert ast is not None

    def test_parse_regexp(self, regexp_config):
        """Test parsing regular expressions."""
        ast = parse_logstash_config(regexp_config)
        assert ast is not None

    def test_parse_regexp_with_escaped_slash(self):
        """Test parsing regular expressions with escaped slashes."""
        config = """
        filter {
            if [path] =~ /\/var\/log\/.*/ {
                mutate {
                    add_tag => ["system_log"]
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

        # Verify the regex is parsed correctly
        python_dict = ast.to_python()
        assert "filter" in python_dict
        filter_section = python_dict["filter"]
        assert len(filter_section) > 0

        # Check that the branch contains the regex expression
        branch = filter_section[0]
        assert branch["type"] == "branch"

    def test_parse_regexp_simple_patterns(self):
        """Test parsing various simple regex patterns."""
        test_cases = [
            ("/error/", "simple word"),
            ("/[0-9]+/", "character class"),
            ("/\\d{4}/", "escaped digit with quantifier"),
            ("/test.*pattern/", "dot star"),
            ("/^start/", "anchor start"),
            ("/end$/", "anchor end"),
        ]

        for pattern, description in test_cases:
            config = f"""
            filter {{
                if [message] =~ {pattern} {{
                    mutate {{
                        add_tag => ["matched"]
                    }}
                }}
            }}
            """
            ast = parse_logstash_config(config)
            assert ast is not None, f"Failed to parse {description}: {pattern}"

    def test_parse_regexp_in_grok_string_value(self):
        """Test that regex in grok uses string values, not regex literals."""
        # This should work - string pattern
        config1 = """
        filter {
            grok {
                match => { "message" => "%{PATTERN}" }
            }
        }
        """
        ast = parse_logstash_config(config1)
        assert ast is not None

    def test_parse_regexp_negation(self):
        """Test parsing negated regex expressions."""
        config = """
        filter {
            if [message] !~ /success/ {
                mutate {
                    add_tag => ["not_success"]
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

        python_dict = ast.to_python()
        assert "filter" in python_dict

    def test_parse_regexp_with_special_chars(self):
        """Test parsing regex with special characters."""
        config = r"""
        filter {
            if [message] =~ /\[ERROR\]/ {
                mutate {
                    add_tag => ["error"]
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None


class TestPluginParsing:
    """Test parsing plugin configurations."""

    def test_parse_plugin_with_attributes(self):
        """Test parsing plugin with attributes."""
        config = """
        filter {
            grok {
                match => { "message" => "%{PATTERN}" }
                tag_on_failure => ["_grokparsefailure"]
                overwrite => ["message"]
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_parse_multiple_plugins(self):
        """Test parsing multiple plugins."""
        config = """
        filter {
            grok {
                match => { "message" => "%{PATTERN}" }
            }
            mutate {
                add_field => { "field" => "value" }
            }
            date {
                match => [ "timestamp", "ISO8601" ]
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_parse_plugin_with_nested_hash(self):
        """Test parsing plugin with nested hash."""
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
        assert ast is not None
