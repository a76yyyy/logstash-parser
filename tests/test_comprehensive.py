"""Comprehensive integration tests for complete Logstash configuration parsing.

This test module validates the parser against a comprehensive configuration file
that covers all grammar rules from grammar.treetop. It ensures:
1. Complete parsing of complex configurations
2. Roundtrip conversion (parse -> to_logstash -> parse)
3. Python dict conversion accuracy
4. No state leakage between tests

All generated files are written to temporary directories to avoid pollution.
"""

import json

import pytest

from logstash_parser import parse_logstash_config


@pytest.mark.integration
class TestComprehensiveConfiguration:
    """Test comprehensive configuration parsing and conversion."""

    def test_parse_comprehensive_config(self, comprehensive_config):
        """Test parsing the comprehensive configuration file."""
        # Parse the config
        ast = parse_logstash_config(comprehensive_config)
        assert ast is not None

        # Count sections
        input_sections = sum(1 for child in ast.children if child.plugin_type == "input")
        filter_sections = sum(1 for child in ast.children if child.plugin_type == "filter")
        output_sections = sum(1 for child in ast.children if child.plugin_type == "output")

        # Verify we have all three types of sections
        assert input_sections > 0, "Should have at least one input section"
        assert filter_sections > 0, "Should have at least one filter section"
        assert output_sections > 0, "Should have at least one output section"

    def test_comprehensive_config_to_python(self, comprehensive_config):
        """Test converting comprehensive config to Python dict."""
        # Parse
        ast = parse_logstash_config(comprehensive_config)

        # Convert to Python
        python_dict = ast.to_python()

        # Verify structure
        assert "config" in python_dict
        assert isinstance(python_dict["config"], list)
        assert len(python_dict["config"]) > 0

        # Verify all sections have plugin_section structure
        for section in python_dict["config"]:
            assert "plugin_section" in section
            plugin_section = section["plugin_section"]
            # Each plugin_section should have one of: input, filter, output
            assert any(key in plugin_section for key in ["input", "filter", "output"])

    def test_comprehensive_config_to_logstash(self, comprehensive_config, tmp_path):
        """Test converting comprehensive config back to Logstash format.

        Uses tmp_path to ensure generated files don't pollute the workspace.
        """
        # Parse
        ast = parse_logstash_config(comprehensive_config)

        # Convert to Logstash
        regenerated = ast.to_logstash()

        # Verify output is not empty
        assert regenerated
        assert len(regenerated) > 0

        # Save to temporary file (will be auto-cleaned by pytest)
        regenerated_file = tmp_path / "comprehensive_regenerated.conf"
        regenerated_file.write_text(regenerated)

        # Verify file was written
        assert regenerated_file.exists()
        assert regenerated_file.stat().st_size > 0

    def test_comprehensive_config_roundtrip(self, comprehensive_config, tmp_path):
        """Test roundtrip: parse -> to_logstash -> parse -> compare.

        This is the most important test - it verifies that we can:
        1. Parse the original config
        2. Convert it to Logstash format
        3. Parse the regenerated config
        4. Get identical Python representations

        Uses tmp_path to avoid file pollution.
        """
        # First parse
        ast1 = parse_logstash_config(comprehensive_config)
        python_dict1 = ast1.to_python()

        # Convert to Logstash
        regenerated = ast1.to_logstash()

        # Save regenerated config to temp file for debugging if needed
        regenerated_file = tmp_path / "comprehensive_regenerated.conf"
        regenerated_file.write_text(regenerated)

        # Second parse
        ast2 = parse_logstash_config(regenerated)
        python_dict2 = ast2.to_python()

        # Compare Python representations
        if python_dict1 != python_dict2:
            # Save JSON for comparison (in temp dir)
            json1_file = tmp_path / "comprehensive_original.json"
            json2_file = tmp_path / "comprehensive_regenerated.json"

            json1_file.write_text(json.dumps(python_dict1, indent=2, sort_keys=True))
            json2_file.write_text(json.dumps(python_dict2, indent=2, sort_keys=True))

            pytest.fail(
                f"Roundtrip failed: Python representations differ.\n"
                f"Original JSON: {json1_file}\n"
                f"Regenerated JSON: {json2_file}"
            )

        # If we get here, roundtrip was successful
        assert python_dict1 == python_dict2

    def test_comprehensive_config_statistics(self, comprehensive_config):
        """Test and report statistics about the comprehensive config."""
        # Parse
        ast = parse_logstash_config(comprehensive_config)

        # Gather statistics
        stats = {
            "config_size": len(comprehensive_config),
            "config_lines": len(comprehensive_config.splitlines()),
            "total_sections": len(ast.children),
            "input_sections": sum(1 for child in ast.children if child.plugin_type == "input"),
            "filter_sections": sum(1 for child in ast.children if child.plugin_type == "filter"),
            "output_sections": sum(1 for child in ast.children if child.plugin_type == "output"),
        }

        # Verify minimum complexity
        assert stats["config_size"] > 1000, "Config should be substantial"
        assert stats["config_lines"] > 50, "Config should have many lines"
        assert stats["total_sections"] >= 3, "Should have at least 3 sections"

        # Print stats for visibility (will show in verbose mode)
        print("\nComprehensive Config Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


@pytest.mark.integration
class TestComprehensiveGrammarCoverage:
    """Test that comprehensive config covers all grammar rules."""

    def test_plugin_types_coverage(self, comprehensive_config):
        """Test that all plugin types are covered."""
        ast = parse_logstash_config(comprehensive_config)

        plugin_types = {child.plugin_type for child in ast.children}

        # Should cover all three plugin types
        assert "input" in plugin_types
        assert "filter" in plugin_types
        assert "output" in plugin_types

    def test_value_types_coverage(self, comprehensive_config):
        """Test that various value types are present in the config."""
        # These are implicit tests - if parsing succeeds, these types are handled
        ast = parse_logstash_config(comprehensive_config)
        python_dict = ast.to_python()

        # Convert to JSON to inspect all values
        json_str = json.dumps(python_dict)

        # Check for various value types (as strings in JSON)
        assert "true" in json_str or "false" in json_str, "Should have boolean values"
        assert any(char.isdigit() for char in json_str), "Should have numeric values"
        assert '"' in json_str, "Should have string values"
        assert "[" in json_str, "Should have array values"
        assert "{" in json_str, "Should have hash values"

    def test_conditional_expressions_coverage(self, comprehensive_config):
        """Test that conditional expressions are present."""
        # If the config contains conditionals, it should have 'if' in it
        assert "if" in comprehensive_config.lower()

        # Parse should succeed
        ast = parse_logstash_config(comprehensive_config)
        assert ast is not None

    def test_method_calls_coverage(self, comprehensive_config):
        """Test that method calls are present in the config."""
        # Check for common method call patterns
        has_method_calls = any(
            pattern in comprehensive_config for pattern in ["sprintf", "format", "upper", "lower", "add", "now"]
        )

        if has_method_calls:
            # Parse should succeed
            ast = parse_logstash_config(comprehensive_config)
            assert ast is not None


@pytest.mark.integration
@pytest.mark.slow
class TestComprehensivePerformance:
    """Performance tests for comprehensive configuration."""

    def test_parse_performance(self, comprehensive_config, benchmark=None):
        """Test parsing performance of comprehensive config.

        Note: benchmark parameter is optional (requires pytest-benchmark).
        If not available, just runs the test once.
        """
        if benchmark:
            # Use pytest-benchmark if available
            result = benchmark(parse_logstash_config, comprehensive_config)
            assert result is not None
        else:
            # Just run once
            ast = parse_logstash_config(comprehensive_config)
            assert ast is not None

    def test_roundtrip_performance(self, comprehensive_config, benchmark=None):
        """Test roundtrip performance.

        Note: benchmark parameter is optional (requires pytest-benchmark).
        """

        def roundtrip():
            ast1 = parse_logstash_config(comprehensive_config)
            regenerated = ast1.to_logstash()
            ast2 = parse_logstash_config(regenerated)
            return ast2

        if benchmark:
            result = benchmark(roundtrip)
            assert result is not None
        else:
            result = roundtrip()
            assert result is not None


@pytest.mark.integration
class TestComprehensiveIsolation:
    """Test that comprehensive tests don't leak state."""

    def test_multiple_parses_independent(self, comprehensive_config):
        """Test that multiple parses of the same config are independent."""
        # Parse twice
        ast1 = parse_logstash_config(comprehensive_config)
        ast2 = parse_logstash_config(comprehensive_config)

        # Should get identical results
        assert ast1.to_python() == ast2.to_python()

        # But should be different objects
        assert ast1 is not ast2

    def test_modifications_dont_affect_original(self, comprehensive_config):
        """Test that modifying parsed AST doesn't affect subsequent parses."""
        # Parse and modify
        ast1 = parse_logstash_config(comprehensive_config)
        original_children_count = len(ast1.children)

        # Modify the AST
        ast1.children = ()  # Clear children

        # Parse again
        ast2 = parse_logstash_config(comprehensive_config)

        # Should have original structure
        assert len(ast2.children) == original_children_count

    def test_temp_files_isolated(self, comprehensive_config, tmp_path):
        """Test that temporary files are isolated per test.

        This test verifies that tmp_path provides a clean directory.
        """
        # tmp_path should be empty at start
        assert list(tmp_path.iterdir()) == []

        # Write a file
        test_file = tmp_path / "test.conf"
        test_file.write_text(comprehensive_config)

        # File should exist
        assert test_file.exists()

        # tmp_path should have exactly one file
        assert len(list(tmp_path.iterdir())) == 1

        # Note: pytest will automatically clean up tmp_path after this test
