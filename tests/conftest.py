"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def simple_filter_config():
    """Simple filter configuration for testing."""
    return """
filter {
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
}
"""


@pytest.fixture
def simple_input_config():
    """Simple input configuration for testing."""
    return """
input {
  beats {
    port => 5044
    host => "0.0.0.0"
  }
}
"""


@pytest.fixture
def simple_output_config():
    """Simple output configuration for testing."""
    return """
output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }
}
"""


@pytest.fixture
def full_config():
    """Full configuration with input, filter, and output."""
    return """
input {
  file {
    path => "/var/log/nginx/access.log"
    type => "nginx"
  }
}

filter {
  if [type] == "nginx" {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
    date {
      match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "nginx-%{+YYYY.MM.dd}"
  }
}
"""


@pytest.fixture
def conditional_config():
    """Configuration with conditional branches."""
    return """
filter {
  if [type] == "nginx" {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
  } else if [type] == "syslog" {
    grok {
      match => { "message" => "%{SYSLOGLINE}" }
    }
  } else {
    mutate {
      add_field => { "unknown_type" => "true" }
    }
  }
}
"""


@pytest.fixture
def complex_expression_config():
    """Configuration with complex expressions."""
    return """
filter {
  if [status] == 200 and [method] == "GET" {
    mutate {
      add_tag => ["success"]
    }
  }

  if [status] >= 400 or [error] {
    mutate {
      add_tag => ["error"]
    }
  }

  if [status] in [200, 201, 204] {
    mutate {
      add_tag => ["success_status"]
    }
  }
}
"""


@pytest.fixture
def array_hash_config():
    """Configuration with arrays and hashes."""
    return """
filter {
  mutate {
    add_field => {
      "field1" => "value1"
      "field2" => "value2"
      "nested" => {
        "inner" => "value"
      }
    }
    add_tag => ["tag1", "tag2", "tag3"]
    copy => {
      "source" => "destination"
    }
  }
}
"""


@pytest.fixture
def number_boolean_config():
    """Configuration with numbers and booleans."""
    return """
filter {
  mutate {
    add_field => {
      "int_field" => 123
      "float_field" => 45.67
      "bool_true" => true
      "bool_false" => false
    }
  }
}
"""


@pytest.fixture
def selector_config():
    """Configuration with field selectors."""
    return """
filter {
  if [field][subfield][nested] == "value" {
    mutate {
      copy => { "[source][field]" => "[dest][field]" }
    }
  }
}
"""


@pytest.fixture
def regexp_config():
    """Configuration with regular expressions."""
    return r"""
filter {
  if [message] =~ /error/ {
    mutate {
      add_tag => ["error"]
    }
  }

  if [message] !~ /success/ {
    mutate {
      add_tag => ["not_success"]
    }
  }

  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601}" }
  }
}
"""


@pytest.fixture(scope="session")
def comprehensive_config_file():
    """Path to comprehensive test configuration file.

    Uses session scope to avoid reading the file multiple times.
    """
    fixtures_dir = Path(__file__).parent / "fixtures"
    config_file = fixtures_dir / "comprehensive_test.conf"
    assert config_file.exists(), f"Comprehensive config file not found: {config_file}"
    return config_file


@pytest.fixture
def comprehensive_config(comprehensive_config_file: Path):
    """Comprehensive test configuration content.

    Uses function scope to ensure each test gets a fresh read.
    This prevents state leakage between tests.
    """
    return comprehensive_config_file.read_text()
