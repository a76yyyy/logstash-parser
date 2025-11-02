"""Tests for the main parser functionality."""

import pytest

from logstash_parser import ParseError, parse_logstash_config
from logstash_parser.ast_nodes import Attribute, Config, LSBareWord, LSString, Plugin


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
        assert "config" in python_dict

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
        assert "config" in python_dict

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
        assert "config" in python_dict

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
        config = r"""
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
        assert "config" in python_dict
        assert len(python_dict["config"]) > 0

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
        assert "config" in python_dict

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


class TestNameParsing:
    """Test that 'name' grammar rule handles various formats correctly.

    This test class verifies that the 'name' grammar rule correctly handles:
    1. Bare words with hyphens (e.g., 'my-plugin-name')
    2. Bare words without hyphens (e.g., 'myPluginName')
    3. Quoted strings (e.g., '"my plugin name"')
    4. Names starting with numbers (e.g., '123-plugin')

    The key difference between 'bare_word' and 'name' in the grammar:
    - bare_word: [A-Za-z_][A-Za-z0-9_]+ (no hyphens, must start with letter/underscore)
    - name: [A-Za-z0-9_-]+ | string (allows hyphens, can start with number, or be a string)
    """

    def test_plugin_name_with_hyphen(self):
        """Test plugin name containing hyphens."""
        config = """
        filter {
            my-custom-plugin {
                field => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]

        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "my-custom-plugin"

    def test_plugin_name_without_hyphen(self):
        """Test plugin name without hyphens (traditional bare word)."""
        config = """
        filter {
            mutate {
                add_field => { "foo" => "bar" }
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]

        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "mutate"

    def test_plugin_name_starting_with_number(self):
        """Test plugin name starting with a number (allowed in 'name' but not 'bare_word')."""
        config = """
        filter {
            123plugin {
                field => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]

        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "123plugin"

    def test_plugin_name_with_multiple_hyphens(self):
        """Test plugin name with multiple consecutive hyphens."""
        config = """
        filter {
            my--double--hyphen {
                field => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]

        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "my--double--hyphen"

    def test_attribute_name_with_hyphen(self):
        """Test attribute name containing hyphens."""
        config = """
        filter {
            mutate {
                my-custom-field => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        attribute = plugin.children[0]

        assert isinstance(attribute, Attribute)
        assert isinstance(attribute.name, LSBareWord)
        assert attribute.name.value == "my-custom-field"

    def test_attribute_name_without_hyphen(self):
        """Test attribute name without hyphens."""
        config = """
        filter {
            mutate {
                add_field => { "foo" => "bar" }
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        attribute = plugin.children[0]

        assert isinstance(attribute, Attribute)
        assert isinstance(attribute.name, LSBareWord)
        assert attribute.name.value == "add_field"

    def test_attribute_name_as_quoted_string(self):
        """Test attribute name as a quoted string."""
        config = """
        filter {
            mutate {
                "my field with spaces" => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        attribute = plugin.children[0]

        assert isinstance(attribute, Attribute)
        assert isinstance(attribute.name, LSString)
        assert attribute.name.value == "my field with spaces"

    def test_attribute_name_single_quoted_string(self):
        """Test attribute name as a single-quoted string."""
        config = """
        filter {
            mutate {
                'my-field' => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        attribute = plugin.children[0]

        assert isinstance(attribute, Attribute)
        assert isinstance(attribute.name, LSString)
        assert attribute.name.lexeme == "'my-field'"

    def test_mixed_names_in_config(self):
        """Test configuration with mixed name formats."""
        config = """
        filter {
            my-plugin-1 {
                field_one => "value1"
                field-two => "value2"
                "field three" => "value3"
                123field => "value4"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)

        # Check plugin name
        assert plugin.plugin_name == "my-plugin-1"

        # Check attribute names
        assert len(plugin.children) == 4

        # field_one (underscore)
        assert isinstance(plugin.children[0].name, LSBareWord)
        assert plugin.children[0].name.value == "field_one"

        # field-two (hyphen)
        assert isinstance(plugin.children[1].name, LSBareWord)
        assert plugin.children[1].name.value == "field-two"

        # "field three" (quoted string)
        assert isinstance(plugin.children[2].name, LSString)
        assert plugin.children[2].name.value == "field three"

        # 123field (starts with number)
        assert isinstance(plugin.children[3].name, LSBareWord)
        assert plugin.children[3].name.value == "123field"

    def test_name_with_only_hyphens(self):
        """Test name consisting only of hyphens."""
        config = """
        filter {
            mutate {
                --- => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        attribute = plugin.children[0]

        assert isinstance(attribute, Attribute)
        assert isinstance(attribute.name, LSBareWord)
        assert attribute.name.value == "---"

    def test_name_with_underscores_and_hyphens(self):
        """Test name with both underscores and hyphens."""
        config = """
        filter {
            my_plugin-name {
                my_field-name => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)

        assert plugin.plugin_name == "my_plugin-name"
        assert plugin.children[0].name.value == "my_field-name"

    def test_roundtrip_with_hyphenated_names(self):
        """Test that hyphenated names survive roundtrip conversion."""
        config = """filter {
  my-custom-plugin {
    field-one => "value1"
    field_two => "value2"
  }
}
"""
        ast = parse_logstash_config(config)

        # Convert to Python dict and back
        python_dict = ast.to_python(as_pydantic=False)
        ast_reconstructed = Config.from_python(python_dict)

        # Check plugin name preserved
        plugin = ast_reconstructed.children[0].children[0]
        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "my-custom-plugin"

        # Check attribute names preserved
        assert plugin.children[0].name.value == "field-one"
        assert plugin.children[1].name.value == "field_two"

        # Convert back to Logstash format
        logstash_output = ast_reconstructed.to_logstash()
        assert "my-custom-plugin" in logstash_output
        assert "field-one" in logstash_output
        assert "field_two" in logstash_output


class TestNameVsBareWordDifference:
    """Test the specific differences between 'name' and 'bare_word' grammar rules."""

    def test_bare_word_pattern_in_name_context(self):
        """Test that traditional bare_word patterns work in name context."""
        # bare_word pattern: starts with letter/underscore, contains letter/number/underscore
        config = """
        filter {
            _myPlugin123 {
                _myField => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)

        assert plugin.plugin_name == "_myPlugin123"
        assert plugin.children[0].name.value == "_myField"

    def test_name_allows_leading_number(self):
        """Test that 'name' allows leading numbers (unlike bare_word)."""
        config = """
        filter {
            9plugin {
                9field => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)

        # This works because 'name' allows [A-Za-z0-9_-]+
        assert plugin.plugin_name == "9plugin"
        assert plugin.children[0].name.value == "9field"

    def test_name_allows_hyphens(self):
        """Test that 'name' allows hyphens (unlike bare_word)."""
        config = """
        filter {
            plugin-with-hyphens {
                field-with-hyphens => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)

        # This works because 'name' allows hyphens
        assert plugin.plugin_name == "plugin-with-hyphens"
        assert plugin.children[0].name.value == "field-with-hyphens"

    def test_name_allows_quoted_strings(self):
        """Test that 'name' allows quoted strings (unlike bare_word)."""
        config = """
        filter {
            mutate {
                "field with spaces and special chars !@#" => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)
        attribute = plugin.children[0]

        # This works because 'name' can be a string
        assert isinstance(attribute.name, LSString)
        assert attribute.name.value == "field with spaces and special chars !@#"


class TestNameParsingEdgeCases:
    """Test edge cases for name parsing."""

    def test_name_with_all_allowed_chars(self):
        """Test name with all allowed characters: letters, numbers, underscores, hyphens."""
        config = """
        filter {
            Aa0_- {
                Zz9_- => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)

        assert plugin.plugin_name == "Aa0_-"
        assert plugin.children[0].name.value == "Zz9_-"

    def test_very_long_hyphenated_name(self):
        """Test very long name with many hyphens."""
        long_name = "my-very-long-plugin-name-with-many-hyphens-and-segments"
        config = f"""
        filter {{
            {long_name} {{
                field => "value"
            }}
        }}
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)

        assert plugin.plugin_name == long_name

    def test_name_case_sensitivity(self):
        """Test that names are case-sensitive."""
        config = """
        filter {
            MyPlugin {
                MyField => "value1"
                myfield => "value2"
                MYFIELD => "value3"
            }
        }
        """
        ast = parse_logstash_config(config)
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)

        assert plugin.plugin_name == "MyPlugin"
        assert plugin.children[0].name.value == "MyField"
        assert plugin.children[1].name.value == "myfield"
        assert plugin.children[2].name.value == "MYFIELD"


class TestGrammarRuleFixes:
    """Test grammar rule fixes to match grammar.treetop specification.

    These tests verify the fixes made to align Python implementation with
    the Treetop grammar specification:
    1. bareword requires at least 2 characters
    2. config requires at least one plugin_section
    3. not_in_operator handles whitespace correctly
    """

    def test_bareword_minimum_two_characters(self):
        """Test that bareword requires at least 2 characters.

        According to grammar.treetop:
        rule bareword
          [A-Za-z_] [A-Za-z0-9_]+
        end

        This means: first char [A-Za-z_], then at least one more char [A-Za-z0-9_]
        """
        # 2 characters should work
        config = """
        filter {
            ab {
                cd => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "ab"

        # Longer barewords should work
        config2 = """
        filter {
            mutate {
                add_field => "value"
            }
        }
        """
        ast2 = parse_logstash_config(config2)
        assert ast2 is not None

    def test_bareword_with_underscore_minimum_length(self):
        """Test bareword starting with underscore requires 2+ chars."""
        config = """
        filter {
            _a {
                _b => "value"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        plugin = ast.children[0].children[0]
        assert isinstance(plugin, Plugin)
        assert plugin.plugin_name == "_a"

    def test_config_requires_at_least_one_section(self):
        """Test that config requires at least one plugin_section.

        According to grammar.treetop:
        rule config
          cs plugin_section cs (cs plugin_section)* cs
        end

        This means at least one plugin_section is required.
        """
        # Empty config should fail
        with pytest.raises(ParseError):
            parse_logstash_config("")

        # Only comments should fail
        with pytest.raises(ParseError):
            parse_logstash_config("# just a comment")

        # Only whitespace should fail
        with pytest.raises(ParseError):
            parse_logstash_config("   \n\t  ")

        # At least one section should work
        config = """
        filter {
            mutate { }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        assert len(ast.children) >= 1

    def test_not_in_operator_with_single_space(self):
        """Test 'not in' operator with single space (standard case)."""
        config = """
        filter {
            if [status] not in [400, 500] {
                mutate {
                    add_tag => ["not_error"]
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

        # Verify the expression was parsed correctly
        python_dict = ast.to_python()
        assert "config" in python_dict

    def test_not_in_operator_with_multiple_spaces(self):
        """Test 'not in' operator with multiple spaces.

        According to grammar.treetop:
        rule not_in_operator
          "not " cs "in"
        end

        Where cs = (comment / whitespace)*
        This means multiple spaces/tabs/newlines are allowed between 'not' and 'in'.
        """
        # Multiple spaces
        config = """
        filter {
            if [status] not  in [400, 500] {
                mutate {
                    add_tag => ["not_error"]
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

        # Verify the expression was parsed correctly
        python_dict = ast.to_python()
        assert "config" in python_dict

    def test_not_in_operator_with_tab(self):
        """Test 'not in' operator with tab character."""
        config = """
        filter {
            if [status] not\tin [400, 500] {
                mutate {
                    add_tag => ["not_error"]
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_not_in_operator_with_newline_and_spaces(self):
        """Test 'not in' operator with newline and spaces."""
        config = """
        filter {
            if [status] not
                in [400, 500] {
                mutate {
                    add_tag => ["not_error"]
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_not_in_operator_with_comment(self):
        """Test 'not in' operator with comment between 'not' and 'in'."""
        config = """
        filter {
            if [status] not # comment
                in [400, 500] {
                mutate {
                    add_tag => ["not_error"]
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_all_plugin_types_work(self):
        """Test that all three plugin types (input/filter/output) work correctly.

        This verifies the fix that removed duplicate 'filter' from plugin_type rule.
        """
        # Test input
        config_input = """
        input {
            stdin { }
        }
        """
        ast = parse_logstash_config(config_input)
        assert ast is not None
        assert ast.children[0].plugin_type == "input"

        # Test filter
        config_filter = """
        filter {
            mutate { }
        }
        """
        ast = parse_logstash_config(config_filter)
        assert ast is not None
        assert ast.children[0].plugin_type == "filter"

        # Test output
        config_output = """
        output {
            stdout { }
        }
        """
        ast = parse_logstash_config(config_output)
        assert ast is not None
        assert ast.children[0].plugin_type == "output"

    def test_multiple_sections_same_type(self):
        """Test multiple sections of the same type (verifies no duplicate handling issues)."""
        config = """
        filter {
            grok {
                match => { "message" => "%{PATTERN1}" }
            }
        }

        filter {
            mutate {
                add_field => { "processed" => "true" }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None
        assert len(ast.children) == 2
        assert all(section.plugin_type == "filter" for section in ast.children)

    def test_bareword_in_different_contexts(self):
        """Test that bareword minimum length applies in all contexts."""
        # Plugin name
        config1 = """
        filter {
            ab {
                field => "value"
            }
        }
        """
        ast1 = parse_logstash_config(config1)
        assert ast1 is not None

        # Attribute name (as bareword)
        config2 = """
        filter {
            mutate {
                ab => "value"
            }
        }
        """
        ast2 = parse_logstash_config(config2)
        assert ast2 is not None

        # Hash key (as bareword)
        config3 = """
        filter {
            mutate {
                add_field => { ab => "value" }
            }
        }
        """
        ast3 = parse_logstash_config(config3)
        assert ast3 is not None


class TestComplexExpressionParsing:
    """Test complex expression parsing scenarios."""

    def test_nested_boolean_with_parentheses(self):
        """Test nested boolean expressions with parentheses."""
        config = """filter {
    if (([a] and [b]) or ([c] and [d])) and [e] {
        mutate { }
    }
}"""
        ast = parse_logstash_config(config)
        assert ast is not None

        # Roundtrip test
        regenerated = ast.to_logstash()
        ast2 = parse_logstash_config(regenerated)
        assert ast.to_python() == ast2.to_python()

    def test_multiple_levels_of_nesting(self):
        """Test multiple levels of boolean expression nesting."""
        config = """filter {
    if ((([a] or [b]) and [c]) or [d]) and [e] {
        mutate { }
    }
}"""
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_xor_with_parentheses(self):
        """Test xor operator with parentheses."""
        config = """filter {
    if ([a] xor ([b] or [c])) and [d] {
        mutate { }
    }
}"""
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_nand_with_nested_expressions(self):
        """Test nand operator with nested expressions."""
        config = """filter {
    if [a] nand ([b] and [c]) {
        mutate { }
    }
}"""
        ast = parse_logstash_config(config)
        assert ast is not None
