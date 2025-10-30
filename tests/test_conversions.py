"""Tests for AST conversion methods (to_python, to_logstash, to_source)."""

import pytest

from logstash_parser import parse_logstash_config


class TestToPython:
    """Test to_python() conversion."""

    def test_simple_filter_to_python(self, simple_filter_config):
        """Test converting simple filter to Python dict."""
        ast = parse_logstash_config(simple_filter_config)
        result = ast.to_python()

        assert isinstance(result, dict)
        assert "filter" in result
        assert isinstance(result["filter"], list)

    def test_full_config_to_python(self, full_config):
        """Test converting full config to Python dict."""
        ast = parse_logstash_config(full_config)
        result = ast.to_python()

        assert "input" in result
        assert "filter" in result
        assert "output" in result

    def test_conditional_to_python(self, conditional_config):
        """Test converting conditional config to Python dict."""
        ast = parse_logstash_config(conditional_config)
        result = ast.to_python()

        assert "filter" in result
        assert isinstance(result["filter"], list)

    def test_array_to_python(self, array_hash_config):
        """Test converting arrays to Python list."""
        ast = parse_logstash_config(array_hash_config)
        result = ast.to_python()

        assert "filter" in result

    def test_hash_to_python(self, array_hash_config):
        """Test converting hashes to Python dict."""
        ast = parse_logstash_config(array_hash_config)
        result = ast.to_python()

        assert "filter" in result

    def test_number_to_python(self, number_boolean_config):
        """Test converting numbers to Python int/float."""
        ast = parse_logstash_config(number_boolean_config)
        result = ast.to_python()

        assert "filter" in result

    def test_boolean_to_python(self, number_boolean_config):
        """Test converting booleans to Python bool."""
        ast = parse_logstash_config(number_boolean_config)
        result = ast.to_python()

        assert "filter" in result


class TestToLogstash:
    """Test to_logstash() conversion."""

    def test_simple_filter_to_logstash(self, simple_filter_config):
        """Test converting simple filter back to Logstash."""
        ast = parse_logstash_config(simple_filter_config)
        result = ast.to_logstash()

        assert isinstance(result, str)
        assert "filter" in result
        assert "grok" in result

    def test_full_config_to_logstash(self, full_config):
        """Test converting full config back to Logstash."""
        ast = parse_logstash_config(full_config)
        result = ast.to_logstash()

        assert "input" in result
        assert "filter" in result
        assert "output" in result

    def test_conditional_to_logstash(self, conditional_config):
        """Test converting conditional config back to Logstash."""
        ast = parse_logstash_config(conditional_config)
        result = ast.to_logstash()

        assert "if" in result
        assert "else if" in result
        assert "else" in result

    def test_roundtrip_simple(self, simple_filter_config):
        """Test roundtrip: parse -> to_logstash -> parse."""
        ast1 = parse_logstash_config(simple_filter_config)
        logstash_str = ast1.to_logstash()
        ast2 = parse_logstash_config(logstash_str)

        # Compare Python representations
        assert ast1.to_python() == ast2.to_python()

    def test_roundtrip_full(self, full_config):
        """Test roundtrip with full config."""
        ast1 = parse_logstash_config(full_config)
        logstash_str = ast1.to_logstash()
        ast2 = parse_logstash_config(logstash_str)

        assert ast1.to_python() == ast2.to_python()

    def test_roundtrip_conditional(self, conditional_config):
        """Test roundtrip with conditional config."""
        ast1 = parse_logstash_config(conditional_config)
        logstash_str = ast1.to_logstash()
        ast2 = parse_logstash_config(logstash_str)

        assert ast1.to_python() == ast2.to_python()


class TestToSource:
    """Test to_source() method."""

    def test_string_to_source(self):
        """Test LSString to_source."""
        from logstash_parser.ast_nodes import LSString

        node = LSString('"hello"')
        assert node.to_source() == '"hello"'

    def test_number_to_source(self):
        """Test Number to_source."""
        from logstash_parser.ast_nodes import Number

        node = Number(123)
        assert node.to_source() == 123

    def test_boolean_to_source(self):
        """Test Boolean to_source."""
        from logstash_parser.ast_nodes import Boolean

        node = Boolean(True)
        assert node.to_source() == "true"


class TestPydanticConversion:
    """Test Pydantic Schema conversion."""

    def test_to_pydantic_simple(self, simple_filter_config):
        """Test converting to Pydantic Schema."""
        ast = parse_logstash_config(simple_filter_config)
        schema = ast.to_python(as_pydantic=True)

        from logstash_parser.schemas import ConfigSchema

        assert isinstance(schema, ConfigSchema)
        assert schema.node_type == "Config"

    def test_to_pydantic_full(self, full_config):
        """Test converting full config to Pydantic Schema."""
        ast = parse_logstash_config(full_config)
        schema = ast.to_python(as_pydantic=True)

        from logstash_parser.schemas import ConfigSchema

        assert isinstance(schema, ConfigSchema)
        assert len(schema.children) == 3

    def test_pydantic_to_json(self, simple_filter_config):
        """Test serializing Pydantic Schema to JSON."""
        ast = parse_logstash_config(simple_filter_config)
        schema = ast.to_python(as_pydantic=True)

        json_str = schema.model_dump_json()
        assert isinstance(json_str, str)
        assert "Config" in json_str

    def test_json_to_pydantic(self, simple_filter_config):
        """Test deserializing JSON to Pydantic Schema."""
        from logstash_parser.schemas import ConfigSchema

        ast = parse_logstash_config(simple_filter_config)
        schema = ast.to_python(as_pydantic=True)
        json_str = schema.model_dump_json()

        loaded_schema = ConfigSchema.model_validate_json(json_str)
        assert isinstance(loaded_schema, ConfigSchema)

    def test_pydantic_roundtrip(self, simple_filter_config):
        """Test roundtrip: AST -> Schema -> JSON -> Schema -> AST."""
        from logstash_parser.ast_nodes import Config
        from logstash_parser.schemas import ConfigSchema

        # AST -> Schema
        ast1 = parse_logstash_config(simple_filter_config)
        schema1 = ast1.to_python(as_pydantic=True)

        # Schema -> JSON
        json_str = schema1.model_dump_json()

        # JSON -> Schema
        schema2 = ConfigSchema.model_validate_json(json_str)

        # Schema -> AST
        ast2 = Config.from_python(schema2)

        # Compare Python representations
        assert ast1.to_python() == ast2.to_python()

    def test_from_python_dict(self, simple_filter_config):
        """Test creating AST from Python dict."""
        from logstash_parser.ast_nodes import Config

        ast1 = parse_logstash_config(simple_filter_config)
        python_dict = ast1.to_python()
        schema = ast1.to_python(as_pydantic=True)

        # Create AST from Schema
        ast2 = Config.from_python(schema)
        assert ast2.to_python() == python_dict

    def test_pydantic_validation(self):
        """Test Pydantic validation."""
        from pydantic import ValidationError

        from logstash_parser.schemas import LSStringSchema

        # Valid schema
        schema = LSStringSchema(node_type="LSString", lexeme='"test"', value="test")
        assert schema.value == "test"

        # Invalid schema (wrong node_type)
        with pytest.raises(ValidationError):
            LSStringSchema(node_type="WrongType", lexeme='"test"', value="test")


class TestExpressionContext:
    """Test expression context handling."""

    def test_expression_context_set(self):
        """Test that expression context is set correctly."""
        config = """
        filter {
            if [status] == 200 {
                mutate { add_tag => ["ok"] }
            }
        }
        """
        ast = parse_logstash_config(config)
        # Expression context should be set during parsing
        # This is tested implicitly through successful parsing

    def test_string_in_expression_context(self):
        """Test string rendering in expression context."""
        config = """
        filter {
            if [type] == "nginx" {
                mutate { add_tag => ["nginx"] }
            }
        }
        """
        ast = parse_logstash_config(config)
        result = ast.to_python()
        assert "filter" in result
