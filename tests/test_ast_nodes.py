"""Tests for AST node classes."""

from logstash_parser import parse_logstash_config
from logstash_parser.ast_nodes import (
    Array,
    Attribute,
    Boolean,
    Branch,
    CompareExpression,
    Config,
    ElseCondition,
    ElseIfCondition,
    Hash,
    HashEntryNode,
    IfCondition,
    InExpression,
    LSBareWord,
    LSString,
    MethodCall,
    NegativeExpression,
    NotInExpression,
    Number,
    Plugin,
    PluginSectionNode,
    RegexExpression,
    Regexp,
    SelectorNode,
)


class TestSimpleNodes:
    """Test simple AST node types."""

    def test_lsstring_creation(self):
        """Test LSString node creation."""
        node = LSString('"hello world"')
        assert node.lexeme == '"hello world"'
        assert node.value == "hello world"

    def test_lsstring_single_quote(self):
        """Test LSString with single quotes."""
        node = LSString("'hello world'")
        assert node.lexeme == "'hello world'"
        assert node.value == "hello world"

    def test_lsstring_to_python(self):
        """Test LSString to_python conversion."""
        node = LSString('"test"')
        result = node.to_python()
        assert result == {"ls_string": '"test"'}

    def test_lsstring_to_pydantic(self):
        """Test LSString to_pydantic conversion."""
        node = LSString('"test"')
        schema = node.to_python(as_pydantic=True)
        assert schema.ls_string == '"test"'

    def test_lsbareword_creation(self):
        """Test LSBareWord node creation."""
        node = LSBareWord("mutate")
        assert node.value == "mutate"

    def test_lsbareword_to_python(self):
        """Test LSBareWord to_python conversion."""
        node = LSBareWord("grok")
        result = node.to_python()
        assert result == {"ls_bare_word": "grok"}

    def test_number_int_creation(self):
        """Test Number node creation with integer."""
        node = Number(123)
        assert node.value == 123

    def test_number_float_creation(self):
        """Test Number node creation with float."""
        node = Number(45.67)
        assert node.value == 45.67

    def test_number_to_python(self):
        """Test Number to_python conversion."""
        node = Number(100)
        result = node.to_python()
        assert result == {"number": 100}

    def test_boolean_true_creation(self):
        """Test Boolean node creation with True."""
        node = Boolean(True)
        assert node.value is True

    def test_boolean_false_creation(self):
        """Test Boolean node creation with False."""
        node = Boolean(False)
        assert node.value is False

    def test_boolean_to_python(self):
        """Test Boolean to_python conversion."""
        node = Boolean(True)
        result = node.to_python()
        assert result == {"boolean": True}

    def test_regexp_creation(self):
        """Test Regexp node creation."""
        node = Regexp("error")
        assert node.lexeme == "error"

    def test_regexp_with_slashes(self):
        """Test Regexp node with slash delimiters."""
        node = Regexp("/error/")
        assert node.lexeme == "/error/"

    def test_regexp_with_escaped_slash(self):
        """Test Regexp node with escaped slashes."""
        node = Regexp(r"/\/var\/log\/.*/")
        assert node.lexeme == r"/\/var\/log\/.*/"
        # The lexeme should preserve the escaped slashes

    def test_regexp_with_special_chars(self):
        """Test Regexp node with special regex characters."""
        test_cases = [
            r"/\d{4}/",  # digit with quantifier
            r"/[0-9]+/",  # character class
            r"/test.*pattern/",  # dot star
            r"/^start/",  # anchor start
            r"/end$/",  # anchor end
            r"/\[ERROR\]/",  # escaped brackets
            r"/\w+@\w+\.\w+/",  # email-like pattern
        ]

        for pattern in test_cases:
            node = Regexp(pattern)
            assert node.lexeme == pattern, f"Failed for pattern: {pattern}"

    def test_regexp_to_python(self):
        """Test Regexp to_python conversion."""
        node = Regexp("/error/")
        result = node.to_python()
        assert result == {"regexp": "/error/"}

    def test_regexp_to_source(self):
        """Test Regexp to_source method."""
        node = Regexp("/test/")
        assert node.to_source() == "/test/"

    def test_selector_creation(self):
        """Test SelectorNode creation."""
        node = SelectorNode("[field][subfield]")
        assert node.raw == "[field][subfield]"

    def test_selector_to_python(self):
        """Test SelectorNode to_python conversion."""
        node = SelectorNode("[field]")
        result = node.to_python()
        assert result == {"selector_node": "[field]"}


class TestDataStructureNodes:
    """Test data structure AST nodes."""

    def test_array_creation(self) -> None:
        """Test Array node creation."""
        elements = LSString('"a"'), LSString('"b"'), LSString('"c"')
        node = Array(elements)
        assert len(node.children) == 3

    def test_array_to_python(self) -> None:
        """Test Array to_python conversion."""
        elements = LSString('"a"'), LSString('"b"')
        node = Array(elements)
        result = node.to_python()
        assert "array" in result
        assert len(result["array"]) == 2

    def test_hash_entry_creation(self):
        """Test HashEntryNode creation."""
        key = LSString('"key"')
        value = LSString('"value"')
        node = HashEntryNode(key, value)
        assert node.key == key
        assert node.value == value

    def test_hash_creation(self):
        """Test Hash node creation."""
        entry1 = HashEntryNode(LSString('"key1"'), LSString('"value1"'))
        entry2 = HashEntryNode(LSString('"key2"'), LSString('"value2"'))
        node = Hash((entry1, entry2))
        assert len(node.children) == 2

    def test_hash_to_python(self):
        """Test Hash to_python conversion."""
        entry1 = HashEntryNode(LSString('"key1"'), LSString('"value1"'))
        entry2 = HashEntryNode(LSString('"key2"'), LSString('"value2"'))
        node = Hash((entry1, entry2))
        result = node.to_python()
        assert "hash" in result
        assert len(result["hash"]) == 2

    def test_attribute_creation(self):
        """Test Attribute node creation."""
        name = LSBareWord("match")
        value = Hash((HashEntryNode(LSString('"message"'), LSString('"%{PATTERN}"')),))
        node = Attribute(name, value)
        assert node.name == name
        assert node.value == value

    def test_attribute_to_python(self):
        """Test Attribute to_python conversion."""
        name = LSBareWord("port")
        value = Number(5044)
        node = Attribute(name, value)
        result = node.to_python()
        # AttributeSchema is a RootModel, so it returns the dict directly
        assert "port" in result


class TestPluginNodes:
    """Test plugin-related AST nodes."""

    def test_plugin_creation(self):
        """Test Plugin node creation."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        node = Plugin("beats", (attr,))
        assert node.plugin_name == "beats"
        assert len(node.children) == 1

    def test_plugin_to_python(self):
        """Test Plugin to_python conversion."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        node = Plugin("beats", (attr,))
        result = node.to_python()
        assert "plugin" in result
        assert result["plugin"]["plugin_name"] == "beats"

    def test_plugin_section_creation(self):
        """Test PluginSectionNode creation."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))
        node = PluginSectionNode("input", [plugin])
        assert node.plugin_type == "input"
        assert len(node.children) == 1

    def test_config_creation(self):
        """Test Config node creation."""
        attr = Attribute(LSBareWord("port"), Number(5044))
        plugin = Plugin("beats", (attr,))
        section = PluginSectionNode("input", [plugin])
        node = Config((section,))
        assert len(node.children) == 1


class TestExpressionNodes:
    """Test expression AST nodes."""

    def test_compare_expression_creation(self):
        """Test CompareExpression node creation."""
        left = SelectorNode("[status]")
        right = Number(200)
        node = CompareExpression(left, "==", right)
        assert node.left == left
        assert node.operator == "=="
        assert node.right == right

    def test_compare_expression_to_python(self):
        """Test CompareExpression to_python conversion."""
        left = SelectorNode("[status]")
        right = Number(200)
        node = CompareExpression(left, "==", right)
        result = node.to_python()
        assert "compare_expression" in result
        assert result["compare_expression"]["operator"] == "=="

    def test_regex_expression_creation(self):
        """Test RegexExpression node creation."""
        left = SelectorNode("[message]")
        pattern = Regexp("error")
        node = RegexExpression(left, "=~", pattern)
        assert node.left == left
        assert node.operator == "=~"
        assert node.pattern == pattern

    def test_in_expression_creation(self):
        """Test InExpression node creation."""
        value = SelectorNode("[status]")
        collection = Array((Number(200), Number(201)))
        node = InExpression(value, "in", collection)
        assert node.value == value
        assert node.operator == "in"
        assert node.collection == collection

    def test_not_in_expression_creation(self):
        """Test NotInExpression node creation."""
        value = SelectorNode("[status]")
        collection = Array((Number(400), Number(500)))
        node = NotInExpression(value, "not in", collection)
        assert node.value == value
        assert node.operator == "not in"

    def test_negative_expression_creation(self):
        """Test NegativeExpression node creation."""
        expr = SelectorNode("[field]")
        node = NegativeExpression("!", expr)
        assert node.operator == "!"
        assert node.expression == expr

    def test_method_call_creation_with_string_args(self):
        """Test MethodCall with string arguments."""
        args = (LSString('"arg1"'), LSString('"arg2"'))
        node = MethodCall("sprintf", args)

        assert node.method_name == "sprintf"
        assert len(node.children) == 2
        assert all(isinstance(arg, LSString) for arg in node.children)

    def test_method_call_creation_with_number_args(self):
        """Test MethodCall with number arguments."""
        args = (Number(1), Number(2), Number(3))
        node = MethodCall("add", args)

        assert node.method_name == "add"
        assert len(node.children) == 3
        assert all(isinstance(arg, Number) for arg in node.children)

    def test_method_call_creation_with_mixed_args(self):
        """Test MethodCall with mixed argument types."""
        args = (
            LSString('"format"'),
            Number(42),
            SelectorNode("[field]"),
        )
        node = MethodCall("format", args)

        assert node.method_name == "format"
        assert len(node.children) == 3
        assert isinstance(node.children[0], LSString)
        assert isinstance(node.children[1], Number)
        assert isinstance(node.children[2], SelectorNode)

    def test_method_call_creation_no_args(self):
        """Test MethodCall with no arguments."""
        node = MethodCall("now", ())

        assert node.method_name == "now"
        assert len(node.children) == 0

    def test_method_call_creation_with_array_arg(self):
        """Test MethodCall with array argument."""
        arr = Array((LSString('"a"'), LSString('"b"')))
        args = (arr,)
        node = MethodCall("join", args)

        assert node.method_name == "join"
        assert len(node.children) == 1
        assert isinstance(node.children[0], Array)

    def test_method_call_creation_with_regexp_arg(self):
        """Test MethodCall with regexp argument."""
        pattern = Regexp("/test/")
        args = (LSString('"text"'), pattern)
        node = MethodCall("match", args)

        assert node.method_name == "match"
        assert len(node.children) == 2
        assert isinstance(node.children[1], Regexp)


class TestConditionalNodes:
    """Test conditional branch AST nodes."""

    def test_if_condition_creation(self):
        """Test IfCondition node creation."""

        expr = CompareExpression(SelectorNode("[type]"), "==", LSString('"nginx"'))
        attr = Attribute(LSBareWord("add_tag"), Array((LSString('"nginx"'),)))
        plugin = Plugin("mutate", (attr,))
        node = IfCondition(expr, (plugin,))
        assert node.expr == expr
        assert len(node.children) == 1

    def test_else_if_condition_creation(self):
        """Test ElseIfCondition node creation."""

        expr = CompareExpression(SelectorNode("[type]"), "==", LSString('"syslog"'))
        attr = Attribute(LSBareWord("add_tag"), Array((LSString('"syslog"'),)))
        plugin = Plugin("mutate", (attr,))
        node = ElseIfCondition(expr, (plugin,))
        assert node.expr == expr
        assert len(node.children) == 1

    def test_else_condition_creation(self):
        """Test ElseCondition node creation."""
        attr = Attribute(LSBareWord("add_tag"), Array((LSString('"unknown"'),)))
        plugin = Plugin("mutate", (attr,))
        node = ElseCondition((plugin,))
        assert len(node.children) == 1

    def test_branch_creation(self):
        """Test Branch node creation."""

        if_expr = CompareExpression(SelectorNode("[type]"), "==", LSString('"nginx"'))
        if_plugin = Plugin("mutate", (Attribute(LSBareWord("add_tag"), Array((LSString('"nginx"'),))),))
        if_cond = IfCondition(if_expr, (if_plugin,))

        else_plugin = Plugin("mutate", (Attribute(LSBareWord("add_tag"), Array((LSString('"unknown"'),))),))
        else_cond = ElseCondition((else_plugin,))

        node = Branch(if_cond, None, else_cond)
        assert len(node.children) == 2


class TestNodeMethods:
    """Test common node methods."""

    def test_node_traverse(self):
        """Test node traverse method."""
        config = """
        filter {
            mutate {
                add_field => { "field" => "value" }
            }
        }
        """
        ast = parse_logstash_config(config)
        # Should not raise any errors
        ast.traverse()

    def test_node_to_repr(self):
        """Test node to_repr method."""
        node = LSString('"test"')
        repr_str = node.to_repr()
        assert "LSString" in repr_str

    def test_node_uid_unique(self):
        """Test that node UIDs are unique."""
        node1 = LSString('"test1"')
        node2 = LSString('"test2"')
        assert node1.uid != node2.uid

    def test_method_call_repr(self):
        """Test MethodCall __repr__."""
        args = (LSString('"test"'),)
        node = MethodCall("upper", args)

        repr_str = repr(node)
        assert "MethodCall" in repr_str
        assert "upper" in repr_str

    def test_method_call_to_repr(self):
        """Test MethodCall to_repr."""
        args = (LSString('"test"'), Number(42))
        node = MethodCall("format", args)

        repr_str = node.to_repr()
        assert "MethodCall" in repr_str
        assert "format" in repr_str

    def test_method_call_to_repr_with_indent(self):
        """Test MethodCall to_repr with indentation."""
        args = (LSString('"test"'),)
        node = MethodCall("upper", args)

        repr_str = node.to_repr(indent=4)
        assert repr_str.startswith("    ")
