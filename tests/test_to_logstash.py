"""Tests for to_logstash() method and Logstash config generation."""

from logstash_parser.ast_nodes import (
    Array,
    Attribute,
    Boolean,
    Hash,
    HashEntryNode,
    LSBareWord,
    LSString,
    Number,
    Plugin,
)


class TestToLogstashBasic:
    """Test basic to_logstash() functionality."""

    def test_hash_simple(self):
        """Test Hash.to_logstash() with simple entries."""
        entry1 = HashEntryNode(LSString('"key1"'), LSString('"value1"'))
        entry2 = HashEntryNode(LSString('"key2"'), Number(100))
        hash_node = Hash((entry1, entry2))

        output = hash_node.to_logstash()
        assert '"key1"' in output
        assert '"value1"' in output
        assert '"key2"' in output
        assert "100" in output
        assert "=>" in output
        assert "{" in output
        assert "}" in output

    def test_hash_empty(self):
        """Test Hash.to_logstash() with empty hash."""
        hash_node = Hash(())
        output = hash_node.to_logstash()
        assert "{" in output
        assert "}" in output

    def test_hash_single_entry(self):
        """Test Hash.to_logstash() with single entry."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash()
        assert '"key"' in output
        assert '"value"' in output
        assert "=>" in output

    def test_attribute_simple(self):
        """Test Attribute.to_logstash() with simple value."""
        name = LSBareWord("port")
        value = Number(5044)
        attr = Attribute(name, value)

        output = attr.to_logstash()
        assert "port" in output
        assert "5044" in output
        assert "=>" in output

    def test_attribute_with_hash(self):
        """Test Attribute.to_logstash() with hash value."""
        name = LSBareWord("match")
        entry = HashEntryNode(LSString('"message"'), LSString('"%{PATTERN}"'))
        value = Hash((entry,))
        attr = Attribute(name, value)

        output = attr.to_logstash()
        assert "match" in output
        assert '"message"' in output
        assert '"%{PATTERN}"' in output

    def test_plugin_simple(self):
        """Test Plugin.to_logstash() with simple attributes."""
        attr1 = Attribute(LSBareWord("port"), Number(5044))
        attr2 = Attribute(LSBareWord("host"), LSString('"0.0.0.0"'))
        plugin = Plugin("beats", (attr1, attr2))

        output = plugin.to_logstash()
        assert "beats" in output
        assert "port" in output
        assert "5044" in output
        assert "host" in output
        assert '"0.0.0.0"' in output
        assert "{" in output
        assert "}" in output


class TestToLogstashNested:
    """Test to_logstash() with nested structures."""

    def test_hash_nested(self):
        """Test Hash.to_logstash() with nested hash."""
        inner_entry = HashEntryNode(LSString('"inner"'), LSString('"value"'))
        inner_hash = Hash((inner_entry,))
        outer_entry = HashEntryNode(LSString('"outer"'), inner_hash)
        outer_hash = Hash((outer_entry,))

        output = outer_hash.to_logstash()
        assert '"outer"' in output
        assert '"inner"' in output
        assert '"value"' in output

    def test_hash_deeply_nested(self):
        """Test deeply nested hash structure."""
        # level3
        level3_entry = HashEntryNode(LSString('"level3"'), LSString('"value"'))
        level3_hash = Hash((level3_entry,))

        # level2
        level2_entry = HashEntryNode(LSString('"level2"'), level3_hash)
        level2_hash = Hash((level2_entry,))

        # level1
        level1_entry = HashEntryNode(LSString('"level1"'), level2_hash)
        level1_hash = Hash((level1_entry,))

        output = level1_hash.to_logstash()
        assert '"level1"' in output
        assert '"level2"' in output
        assert '"level3"' in output
        assert '"value"' in output

    def test_array_of_hashes(self):
        """Test array containing hashes."""
        hash1 = Hash((HashEntryNode(LSString('"k1"'), LSString('"v1"')),))
        hash2 = Hash((HashEntryNode(LSString('"k2"'), LSString('"v2"')),))
        arr = Array((hash1, hash2))

        output = arr.to_logstash()
        assert '"k1"' in output
        assert '"v1"' in output
        assert '"k2"' in output
        assert '"v2"' in output

    def test_hash_of_arrays(self):
        """Test hash containing arrays."""
        arr1 = Array((LSString('"a"'), LSString('"b"')))
        arr2 = Array((Number(1), Number(2)))
        entry1 = HashEntryNode(LSString('"array1"'), arr1)
        entry2 = HashEntryNode(LSString('"array2"'), arr2)
        hash_node = Hash((entry1, entry2))

        output = hash_node.to_logstash()
        assert '"array1"' in output
        assert '"a"' in output
        assert '"b"' in output
        assert '"array2"' in output

    def test_mixed_nested_structures(self):
        """Test mixed nested structures."""
        # Create: { "key" => ["a", { "inner" => "value" }] }
        inner_hash = Hash((HashEntryNode(LSString('"inner"'), LSString('"value"')),))
        arr = Array((LSString('"a"'), inner_hash))
        entry = HashEntryNode(LSString('"key"'), arr)
        hash_node = Hash((entry,))

        output = hash_node.to_logstash()
        assert '"key"' in output
        assert '"a"' in output
        assert '"inner"' in output
        assert '"value"' in output


class TestToLogstashFormatting:
    """Test to_logstash() formatting (indentation, newlines)."""

    def test_hash_has_newlines(self):
        """Test Hash.to_logstash() includes newlines."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash()
        assert "\n" in output

    def test_hash_indentation(self):
        """Test Hash.to_logstash() with custom indentation."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash(indent=2)
        # Should have indentation
        lines = output.split("\n")
        assert any(line.startswith("  ") for line in lines if line.strip())

    def test_plugin_has_newlines(self):
        """Test Plugin.to_logstash() includes newlines."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))
        output = plugin.to_logstash()
        assert "\n" in output

    def test_plugin_indentation(self):
        """Test Plugin.to_logstash() with custom indentation."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))
        output = plugin.to_logstash(indent=2)
        # Should have indentation
        lines = output.split("\n")
        assert any(line.startswith("  ") for line in lines if line.strip())


class TestToLogstashConsistency:
    """Test to_logstash() consistency and idempotency."""

    def test_array_consistency(self):
        """Test Array.to_logstash() is consistent."""
        arr = Array((LSString('"a"'), Number(1), Boolean(True)))
        output1 = arr.to_logstash()
        output2 = arr.to_logstash()

        # Multiple calls should produce the same output
        assert output1 == output2
        assert '"a"' in output1
        assert "1" in output1
        assert "true" in output1

    def test_hash_consistency(self):
        """Test Hash.to_logstash() is consistent."""
        entry = HashEntryNode(LSString('"key"'), LSString('"value"'))
        hash_node = Hash((entry,))
        output1 = hash_node.to_logstash()
        output2 = hash_node.to_logstash()

        # Multiple calls should produce the same output
        assert output1 == output2
        assert '"key"' in output1
        assert '"value"' in output1

    def test_attribute_consistency(self):
        """Test Attribute.to_logstash() is consistent."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        output1 = attr.to_logstash()
        output2 = attr.to_logstash()

        # Multiple calls should produce the same output
        assert output1 == output2
        assert "port" in output1
        assert "5044" in output1

    def test_plugin_consistency(self):
        """Test Plugin.to_logstash() is consistent."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))
        output1 = plugin.to_logstash()
        output2 = plugin.to_logstash()

        # Multiple calls should produce the same output
        assert output1 == output2
        assert "beats" in output1
        assert "port" in output1


class TestToLogstashEdgeCases:
    """Test to_logstash() edge cases."""

    def test_empty_plugin(self):
        """Test Plugin.to_logstash() with no attributes."""
        plugin = Plugin("stdin", ())
        output = plugin.to_logstash()
        assert "stdin" in output
        assert "{" in output
        assert "}" in output

    def test_attribute_with_array(self):
        """Test Attribute.to_logstash() with array value."""
        name = LSBareWord("tags")
        value = Array((LSString('"tag1"'), LSString('"tag2"')))
        attr = Attribute(name, value)

        output = attr.to_logstash()
        assert "tags" in output
        assert '"tag1"' in output
        assert '"tag2"' in output

    def test_hash_with_number_key(self):
        """Test Hash.to_logstash() with number as key."""
        entry = HashEntryNode(Number(200), LSString('"OK"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash()
        assert "200" in output
        assert '"OK"' in output

    def test_hash_with_bareword_key(self):
        """Test Hash.to_logstash() with bareword as key."""
        entry = HashEntryNode(LSBareWord("field"), LSString('"value"'))
        hash_node = Hash((entry,))
        output = hash_node.to_logstash()
        assert "field" in output
        assert '"value"' in output
