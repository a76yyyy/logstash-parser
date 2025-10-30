"""Integration tests for complete workflows."""

import pytest

from logstash_parser import parse_logstash_config
from logstash_parser.ast_nodes import Config
from logstash_parser.schemas import ConfigSchema


@pytest.mark.integration
class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    def test_parse_to_python_workflow(self, full_config):
        """Test: Parse -> to_python workflow."""
        # Parse
        ast = parse_logstash_config(full_config)

        # Convert to Python
        python_dict = ast.to_python()

        # Verify structure
        assert "input" in python_dict
        assert "filter" in python_dict
        assert "output" in python_dict
        assert isinstance(python_dict["input"], list)
        assert isinstance(python_dict["filter"], list)
        assert isinstance(python_dict["output"], list)

    def test_parse_to_logstash_workflow(self, full_config):
        """Test: Parse -> to_logstash workflow."""
        # Parse
        ast = parse_logstash_config(full_config)

        # Convert to Logstash
        logstash_str = ast.to_logstash()

        # Verify output
        assert isinstance(logstash_str, str)
        assert "input" in logstash_str
        assert "filter" in logstash_str
        assert "output" in logstash_str

    def test_parse_to_pydantic_workflow(self, full_config):
        """Test: Parse -> to_pydantic workflow."""
        # Parse
        ast = parse_logstash_config(full_config)

        # Convert to Pydantic
        schema = ast.to_python(as_pydantic=True)

        # Verify schema
        assert isinstance(schema, ConfigSchema)
        assert len(schema.children) == 3

    def test_full_roundtrip_workflow(self, full_config):
        """Test: Parse -> to_logstash -> Parse -> Compare."""
        # First parse
        ast1 = parse_logstash_config(full_config)

        # Convert to Logstash
        logstash_str = ast1.to_logstash()

        # Second parse
        ast2 = parse_logstash_config(logstash_str)

        # Compare
        assert ast1.to_python() == ast2.to_python()

    def test_pydantic_json_roundtrip_workflow(self, full_config):
        """Test: Parse -> Pydantic -> JSON -> Pydantic -> AST."""
        # Parse to AST
        ast1 = parse_logstash_config(full_config)

        # AST to Pydantic
        schema1 = ast1.to_python(as_pydantic=True)

        # Pydantic to JSON
        json_str = schema1.model_dump_json()

        # JSON to Pydantic
        schema2 = ConfigSchema.model_validate_json(json_str)

        # Pydantic to AST
        ast2 = Config.from_python(schema2)

        # Compare
        assert ast1.to_python() == ast2.to_python()

    def test_modify_and_regenerate_workflow(self, simple_filter_config):
        """Test: Parse -> Modify -> to_logstash."""
        from logstash_parser.ast_nodes import Attribute, LSBareWord, LSString, Plugin

        # Parse
        ast = parse_logstash_config(simple_filter_config)

        # Modify: Add a new plugin
        filter_section = ast.children[0]
        new_plugin = Plugin(
            "mutate",
            [Attribute(LSBareWord("add_field"), LSString('"new_field"'))],
        )
        filter_section.children.append(new_plugin)

        # Regenerate
        logstash_str = ast.to_logstash()

        # Verify
        assert "mutate" in logstash_str
        assert "grok" in logstash_str


@pytest.mark.integration
class TestRealWorldConfigs:
    """Test with real-world-like configurations."""

    def test_nginx_access_log_config(self):
        """Test parsing nginx access log configuration."""
        config = """
        input {
            file {
                path => "/var/log/nginx/access.log"
                start_position => "beginning"
                sincedb_path => "/dev/null"
            }
        }

        filter {
            grok {
                match => { "message" => "%{COMBINEDAPACHELOG}" }
            }

            date {
                match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
                target => "@timestamp"
            }

            geoip {
                source => "clientip"
            }

            useragent {
                source => "agent"
                target => "useragent"
            }
        }

        output {
            elasticsearch {
                hosts => ["localhost:9200"]
                index => "nginx-access-%{+YYYY.MM.dd}"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

        # Verify roundtrip
        logstash_str = ast.to_logstash()
        ast2 = parse_logstash_config(logstash_str)
        assert ast.to_python() == ast2.to_python()

    def test_syslog_config(self):
        """Test parsing syslog configuration."""
        config = """
        input {
            syslog {
                port => 514
                type => "syslog"
            }
        }

        filter {
            if [type] == "syslog" {
                grok {
                    match => { "message" => "%{SYSLOGLINE}" }
                }

                date {
                    match => [ "timestamp", "MMM  d HH:mm:ss", "MMM dd HH:mm:ss" ]
                }

                if [program] == "sudo" {
                    mutate {
                        add_tag => ["sudo"]
                    }
                }
            }
        }

        output {
            elasticsearch {
                hosts => ["localhost:9200"]
                index => "syslog-%{+YYYY.MM.dd}"
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_multi_pipeline_config(self):
        """Test parsing multi-pipeline configuration."""
        config = """
        input {
            beats {
                port => 5044
                type => "beats"
            }

            tcp {
                port => 5000
                type => "tcp"
            }
        }

        filter {
            if [type] == "beats" {
                json {
                    source => "message"
                }
            } else if [type] == "tcp" {
                grok {
                    match => { "message" => "%{GREEDYDATA}" }
                }
            }

            mutate {
                remove_field => ["@version"]
            }
        }

        output {
            if [type] == "beats" {
                elasticsearch {
                    hosts => ["localhost:9200"]
                    index => "beats-%{+YYYY.MM.dd}"
                }
            } else {
                elasticsearch {
                    hosts => ["localhost:9200"]
                    index => "tcp-%{+YYYY.MM.dd}"
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_complex_filtering_config(self):
        """Test parsing complex filtering configuration."""
        config = """
        filter {
            if [status] >= 200 and [status] < 300 {
                mutate {
                    add_tag => ["success"]
                }
            } else if [status] >= 300 and [status] < 400 {
                mutate {
                    add_tag => ["redirect"]
                }
            } else if [status] >= 400 and [status] < 500 {
                mutate {
                    add_tag => ["client_error"]
                }
            } else if [status] >= 500 {
                mutate {
                    add_tag => ["server_error"]
                }
            }

            if [message] =~ /error/ or [message] =~ /exception/ {
                mutate {
                    add_tag => ["has_error"]
                }
            }

            if [status] in [200, 201, 204] {
                mutate {
                    add_field => { "success_type" => "standard" }
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_regexp_with_escaped_slashes_workflow(self):
        """Test complete workflow with regex containing escaped slashes."""
        config = r"""
        filter {
            if [path] =~ /\/var\/log\/.*\.log/ {
                mutate {
                    add_field => { "log_type" => "system" }
                }
            }

            if [url] =~ /https?:\/\/.*/ {
                mutate {
                    add_tag => ["has_url"]
                }
            }
        }
        """

        # Parse
        ast = parse_logstash_config(config)
        assert ast is not None

        # Convert to Python
        python_dict = ast.to_python()
        assert "filter" in python_dict
        assert len(python_dict["filter"]) == 2

        # Convert to Logstash
        logstash_str = ast.to_logstash()
        assert "filter" in logstash_str
        # Note: to_logstash() may not preserve exact regex format
        # Just verify it contains the filter section

    def test_regexp_patterns_variety(self):
        """Test various regex patterns in a single config."""
        config = r"""
        filter {
            # Simple pattern
            if [message] =~ /error/ {
                mutate { add_tag => ["error"] }
            }

            # Character class
            if [status] =~ /[45][0-9]{2}/ {
                mutate { add_tag => ["error_status"] }
            }

            # Escaped special chars
            if [message] =~ /\[ERROR\]/ {
                mutate { add_tag => ["bracketed_error"] }
            }

            # Anchors
            if [message] =~ /^ERROR:/ {
                mutate { add_tag => ["starts_with_error"] }
            }

            # Negation
            if [message] !~ /success/ {
                mutate { add_tag => ["not_success"] }
            }
        }
        """

        ast = parse_logstash_config(config)
        assert ast is not None

        python_dict = ast.to_python()
        assert "filter" in python_dict
        # Should have 5 branches
        assert len(python_dict["filter"]) == 5


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_invalid_config_error(self):
        """Test that invalid config raises appropriate error."""
        from logstash_parser import ParseError

        # Completely invalid syntax
        invalid_config = "this is not valid logstash syntax at all { } => @#$%"

        # Invalid syntax should raise ParseError
        with pytest.raises(ParseError):
            parse_logstash_config(invalid_config)

    def test_empty_config_error(self):
        """Test that empty config raises appropriate error."""
        from logstash_parser import ParseError

        # Empty config should raise ParseError
        with pytest.raises(ParseError, match="Configuration text is empty"):
            parse_logstash_config("")

        # Whitespace-only config should also raise ParseError
        with pytest.raises(ParseError, match="Configuration text is empty"):
            parse_logstash_config("   \n\t  ")

    def test_malformed_json_schema_error(self):
        """Test that malformed JSON raises validation error."""
        from pydantic import ValidationError

        malformed_json = '{"node_type": "Config", "children": "not_a_list"}'
        with pytest.raises(ValidationError):
            ConfigSchema.model_validate_json(malformed_json)


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Test performance with large configurations."""

    def test_large_config_parsing(self):
        """Test parsing a large configuration."""
        # Generate a large config with many plugins
        plugins = []
        for i in range(100):
            plugins.append(
                f"""
            mutate {{
                add_field => {{ "field_{i}" => "value_{i}" }}
            }}
            """
            )

        config = f"""
        filter {{
            {"".join(plugins)}
        }}
        """

        ast = parse_logstash_config(config)
        assert ast is not None
        assert len(ast.children[0].children) == 100

    def test_deeply_nested_conditions(self):
        """Test parsing deeply nested conditions."""
        config = """
        filter {
            if [level1] == "a" {
                if [level2] == "b" {
                    if [level3] == "c" {
                        if [level4] == "d" {
                            if [level5] == "e" {
                                mutate {
                                    add_tag => ["deeply_nested"]
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        ast = parse_logstash_config(config)
        assert ast is not None

    def test_many_conditions(self):
        """Test parsing many conditions."""
        conditions = []
        for i in range(50):
            conditions.append(
                f"""
            if [field_{i}] == "value_{i}" {{
                mutate {{
                    add_tag => ["tag_{i}"]
                }}
            }}
            """
            )

        config = f"""
        filter {{
            {"".join(conditions)}
        }}
        """

        ast = parse_logstash_config(config)
        assert ast is not None
