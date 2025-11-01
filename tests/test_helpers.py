"""Helper functions and utilities for tests."""

from typing import Any

from logstash_parser import parse_logstash_config


def assert_roundtrip_equal(config: str) -> None:
    """Assert that config can be parsed, converted to Logstash, and parsed again with same result.

    Args:
        config: Logstash configuration string

    Raises:
        AssertionError: If roundtrip produces different result
    """
    ast1 = parse_logstash_config(config)
    logstash_str = ast1.to_logstash()
    ast2 = parse_logstash_config(logstash_str)
    assert ast1.to_python() == ast2.to_python(), "Roundtrip produced different result"


def assert_pydantic_roundtrip_equal(config: str) -> None:
    """Assert that config can be converted through Pydantic and back with same result.

    Args:
        config: Logstash configuration string

    Raises:
        AssertionError: If Pydantic roundtrip produces different result
    """
    from logstash_parser.ast_nodes import Config
    from logstash_parser.schemas import ConfigSchema

    ast1 = parse_logstash_config(config)
    schema1 = ast1.to_python(as_pydantic=True)
    json_str = schema1.model_dump_json()
    schema2 = ConfigSchema.model_validate_json(json_str)
    ast2 = Config.from_python(schema2)
    assert ast1.to_python() == ast2.to_python(), "Pydantic roundtrip produced different result"


def get_plugin_names(python_dict: dict[str, Any], section_type: str) -> list[str]:
    """Extract plugin names from a Python dict representation.

    Args:
        python_dict: Python dict from ast.to_python()
        section_type: Section type (input, filter, output)

    Returns:
        List of plugin names in the section
    """
    if "config" not in python_dict:
        return []

    plugin_names: list[str] = []

    # Find the section with matching plugin_type
    for section in python_dict["config"]:
        if not isinstance(section, dict) or "plugin_section" not in section:
            continue

        plugin_section = section["plugin_section"]
        if plugin_section.get("plugin_type") != section_type:
            continue

        # Extract plugin names from children
        for child in plugin_section.get("children", []):
            if isinstance(child, dict) and "plugin" in child:
                plugin_name = child["plugin"].get("plugin_name")
                if plugin_name:
                    plugin_names.append(plugin_name)

    return plugin_names


def count_plugins(python_dict: dict[str, Any], section_type: str) -> int:
    """Count number of plugins in a section.

    Args:
        python_dict: Python dict from ast.to_python()
        section_type: Section type (input, filter, output)

    Returns:
        Number of plugins in the section
    """
    if "config" not in python_dict:
        return 0

    # Find the section with matching plugin_type
    for section in python_dict["config"]:
        if not isinstance(section, dict) or "plugin_section" not in section:
            continue

        plugin_section = section["plugin_section"]
        if plugin_section.get("plugin_type") != section_type:
            continue

        return len(plugin_section.get("children", []))

    return 0


def has_conditional(python_dict: dict[str, Any], section_type: str = "filter") -> bool:
    """Check if a section has conditional branches.

    Args:
        python_dict: Python dict from ast.to_python()
        section_type: Section type to check

    Returns:
        True if section has conditionals
    """
    if "config" not in python_dict:
        return False

    # Find the section with matching plugin_type
    for section in python_dict["config"]:
        if not isinstance(section, dict) or "plugin_section" not in section:
            continue

        plugin_section = section["plugin_section"]
        if plugin_section.get("plugin_type") != section_type:
            continue

        # Check if any child is a branch
        for child in plugin_section.get("children", []):
            if isinstance(child, dict) and "branch" in child:
                return True

    return False


def create_simple_config(plugin_type: str, plugin_name: str, attributes: dict[str, Any]) -> str:
    """Create a simple Logstash config for testing.

    Args:
        plugin_type: Type of plugin section (input, filter, output)
        plugin_name: Name of the plugin
        attributes: Dictionary of attributes

    Returns:
        Logstash configuration string
    """
    attr_lines = []
    for key, value in attributes.items():
        if isinstance(value, str):
            attr_lines.append(f'    {key} => "{value}"')
        elif isinstance(value, (int, float)):
            attr_lines.append(f"    {key} => {value}")
        elif isinstance(value, bool):
            attr_lines.append(f"    {key} => {str(value).lower()}")
        elif isinstance(value, dict):
            # Simple hash
            hash_items = [f'"{k}" => "{v}"' for k, v in value.items()]
            attr_lines.append(f"    {key} => {{ {', '.join(hash_items)} }}")
        elif isinstance(value, list):
            # Simple array
            array_items = [f'"{item}"' if isinstance(item, str) else str(item) for item in value]
            attr_lines.append(f"    {key} => [{', '.join(array_items)}]")

    attrs = "\n".join(attr_lines)
    return f"""
{plugin_type} {{
  {plugin_name} {{
{attrs}
  }}
}}
"""


class ConfigBuilder:
    """Builder class for creating test configurations."""

    def __init__(self):
        self.sections = {"input": [], "filter": [], "output": []}

    def add_input(self, plugin_name: str, **attributes) -> "ConfigBuilder":
        """Add an input plugin."""
        self.sections["input"].append((plugin_name, attributes))
        return self

    def add_filter(self, plugin_name: str, **attributes) -> "ConfigBuilder":
        """Add a filter plugin."""
        self.sections["filter"].append((plugin_name, attributes))
        return self

    def add_output(self, plugin_name: str, **attributes) -> "ConfigBuilder":
        """Add an output plugin."""
        self.sections["output"].append((plugin_name, attributes))
        return self

    def build(self) -> str:
        """Build the configuration string."""
        config_parts = []

        for section_type, plugins in self.sections.items():
            if not plugins:
                continue

            plugin_configs = []
            for plugin_name, attributes in plugins:
                attr_lines = []
                for key, value in attributes.items():
                    if isinstance(value, str):
                        attr_lines.append(f'    {key} => "{value}"')
                    elif isinstance(value, (int, float)):
                        attr_lines.append(f"    {key} => {value}")
                    elif isinstance(value, bool):
                        attr_lines.append(f"    {key} => {str(value).lower()}")

                attrs = "\n".join(attr_lines)
                plugin_configs.append(
                    f"""  {plugin_name} {{
{attrs}
  }}"""
                )

            section_config = f"""{section_type} {{
{chr(10).join(plugin_configs)}
}}"""
            config_parts.append(section_config)

        return "\n\n".join(config_parts)


# Test the helpers
def test_config_builder():
    """Test ConfigBuilder helper."""
    builder = ConfigBuilder()
    config = (
        builder.add_input("beats", port=5044, host="0.0.0.0")
        .add_filter("mutate", add_field="test")
        .add_output("elasticsearch", hosts="localhost:9200")
        .build()
    )

    assert "input" in config
    assert "filter" in config
    assert "output" in config
    assert "beats" in config
    assert "mutate" in config
    assert "elasticsearch" in config


def test_assert_roundtrip():
    """Test assert_roundtrip_equal helper."""
    config = """
    filter {
        mutate {
            add_field => { "field" => "value" }
        }
    }
    """
    # Should not raise
    assert_roundtrip_equal(config)


def test_get_plugin_names():
    """Test get_plugin_names helper."""
    from logstash_parser import parse_logstash_config

    config = """
    filter {
        grok {
            match => { "message" => "%{PATTERN}" }
        }
        mutate {
            add_field => { "field" => "value" }
        }
    }
    """
    ast = parse_logstash_config(config)
    python_dict = ast.to_python()

    names = get_plugin_names(python_dict, "filter")
    assert "grok" in names
    assert "mutate" in names
