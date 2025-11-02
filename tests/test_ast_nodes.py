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

    def test_plugin_section_with_mixed_content(self):
        """Test PluginSectionNode with plugins and branches."""
        plugin1 = Plugin("grok", ())

        expr = CompareExpression(SelectorNode("[type]"), "==", LSString('"nginx"'))
        plugin2 = Plugin("mutate", ())
        if_cond = IfCondition(expr, (plugin2,))
        branch = Branch(if_cond, None, None)

        plugin3 = Plugin("date", ())

        section = PluginSectionNode("filter", [plugin1, branch, plugin3])

        assert len(section.children) == 3
        assert isinstance(section.children[0], Plugin)
        assert isinstance(section.children[1], Branch)
        assert isinstance(section.children[2], Plugin)

    def test_config_with_multiple_same_type_sections(self):
        """Test Config with multiple sections of same type."""
        plugin1 = Plugin("grok", ())
        section1 = PluginSectionNode("filter", [plugin1])

        plugin2 = Plugin("mutate", ())
        section2 = PluginSectionNode("filter", [plugin2])

        plugin3 = Plugin("date", ())
        section3 = PluginSectionNode("filter", [plugin3])

        config = Config((section1, section2, section3))

        assert len(config.children) == 3
        assert all(child.plugin_type == "filter" for child in config.children)

    def test_config_with_all_section_types(self):
        """Test Config with input, filter, and output sections."""
        input_plugin = Plugin("file", ())
        input_section = PluginSectionNode("input", [input_plugin])

        filter_plugin = Plugin("grok", ())
        filter_section = PluginSectionNode("filter", [filter_plugin])

        output_plugin = Plugin("elasticsearch", ())
        output_section = PluginSectionNode("output", [output_plugin])

        config = Config((input_section, filter_section, output_section))

        assert len(config.children) == 3
        assert config.children[0].plugin_type == "input"
        assert config.children[1].plugin_type == "filter"
        assert config.children[2].plugin_type == "output"


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

    def test_hash_entry_with_method_call_value(self):
        """Test HashEntryNode with method call as value."""
        key = LSString('"key"')
        value = MethodCall("upper", (LSString('"test"'),))
        entry = HashEntryNode(key, value)

        assert entry.key == key
        assert entry.value == value

    def test_attribute_with_method_call_value(self):
        """Test Attribute with method call as value."""
        name = LSBareWord("field")
        value = MethodCall("sprintf", (LSString('"%{pattern}"'),))
        attr = Attribute(name, value)

        assert attr.name == name
        assert attr.value == value

    def test_compare_expression_with_method_call(self):
        """Test CompareExpression with method call."""
        left = SelectorNode("[field]")
        right = MethodCall("upper", (LSString('"test"'),))
        expr = CompareExpression(left, "==", right)

        assert expr.left == left
        assert expr.right == right

    def test_regex_expression_with_method_call_left(self):
        """Test RegexExpression with method call on left side."""
        left = MethodCall("lower", (SelectorNode("[field]"),))
        pattern = Regexp("/test/")
        expr = RegexExpression(left, "=~", pattern)

        assert expr.left == left
        assert expr.pattern == pattern

    def test_in_expression_with_method_call(self):
        """Test InExpression with method call."""
        value = MethodCall("upper", (SelectorNode("[field]"),))
        collection = Array((LSString('"A"'), LSString('"B"')))
        expr = InExpression(value, "in", collection)

        assert expr.value == value
        assert expr.collection == collection

    def test_not_in_expression_with_method_call(self):
        """Test NotInExpression with method call."""
        value = MethodCall("lower", (SelectorNode("[field]"),))
        collection = Array((LSString('"a"'), LSString('"b"')))
        expr = NotInExpression(value, "not in", collection)

        assert expr.value == value
        assert expr.collection == collection

    def test_negative_of_method_call(self):
        """Test negation of method call."""
        method_call = MethodCall("exists", (SelectorNode("[field]"),))
        expr = NegativeExpression("!", method_call)

        assert expr.operator == "!"
        assert expr.expression == method_call

    def test_negative_of_in_expression(self):
        """Test negation of in expression."""
        in_expr = InExpression(SelectorNode("[status]"), "in", Array((Number(200), Number(201))))
        expr = NegativeExpression("!", in_expr)

        result = expr.to_logstash()
        assert "!" in result

    def test_negative_of_regex_expression(self):
        """Test negation of regex expression."""
        regex_expr = RegexExpression(SelectorNode("[message]"), "=~", Regexp("/error/"))
        expr = NegativeExpression("!", regex_expr)

        result = expr.to_logstash()
        assert "!" in result

    def test_method_call_with_nested_array(self):
        """Test method call with nested array argument."""
        inner_arr = Array((Number(1), Number(2)))
        outer_arr = Array((inner_arr, Number(3)))
        method_call = MethodCall("process", (outer_arr,))

        assert len(method_call.children) == 1
        assert isinstance(method_call.children[0], Array)

    def test_deeply_nested_method_calls(self):
        """Test deeply nested method calls (10 levels)."""
        current = MethodCall("level10", (LSString('"innermost"'),))

        for i in range(9, 0, -1):
            current = MethodCall(f"level{i}", (current,))

        result = current.to_logstash()
        assert "level1" in result
        assert "level10" in result
        assert "innermost" in result


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

    def test_branch_with_only_if(self):
        """Test Branch with only if condition."""
        expr = CompareExpression(SelectorNode("[type]"), "==", LSString('"nginx"'))
        plugin = Plugin("mutate", ())
        if_cond = IfCondition(expr, (plugin,))

        branch = Branch(if_cond, None, None)

        assert len(branch.children) == 1
        assert isinstance(branch.children[0], IfCondition)

    def test_branch_with_if_and_else(self):
        """Test Branch with if and else."""
        expr = CompareExpression(SelectorNode("[type]"), "==", LSString('"nginx"'))
        plugin1 = Plugin("mutate", ())
        if_cond = IfCondition(expr, (plugin1,))

        plugin2 = Plugin("drop", ())
        else_cond = ElseCondition((plugin2,))

        branch = Branch(if_cond, None, else_cond)

        assert len(branch.children) == 2

    def test_branch_with_multiple_else_if(self):
        """Test Branch with multiple else-if conditions."""
        expr1 = CompareExpression(SelectorNode("[status]"), "==", Number(200))
        plugin1 = Plugin("mutate", ())
        if_cond = IfCondition(expr1, (plugin1,))

        expr2 = CompareExpression(SelectorNode("[status]"), "==", Number(404))
        plugin2 = Plugin("mutate", ())
        else_if1 = ElseIfCondition(expr2, (plugin2,))

        expr3 = CompareExpression(SelectorNode("[status]"), "==", Number(500))
        plugin3 = Plugin("mutate", ())
        else_if2 = ElseIfCondition(expr3, (plugin3,))

        plugin4 = Plugin("drop", ())
        else_cond = ElseCondition((plugin4,))

        branch = Branch(if_cond, [else_if1, else_if2], else_cond)

        assert len(branch.children) == 4


class TestRValueNode:
    """Test RValue node functionality."""

    def test_rvalue_with_string(self):
        """Test RValue wrapping a string."""
        from logstash_parser.ast_nodes import RValue

        string_node = LSString('"test"')
        rvalue = RValue(string_node)

        assert rvalue.value == string_node
        assert len(rvalue.children) == 1
        assert rvalue.children[0] == string_node

    def test_rvalue_with_number(self):
        """Test RValue wrapping a number."""
        from logstash_parser.ast_nodes import RValue

        number_node = Number(123)
        rvalue = RValue(number_node)

        assert rvalue.value == number_node

    def test_rvalue_with_selector(self):
        """Test RValue wrapping a selector."""
        from logstash_parser.ast_nodes import RValue

        selector_node = SelectorNode("[field]")
        rvalue = RValue(selector_node)

        assert rvalue.value == selector_node

    def test_rvalue_with_array(self):
        """Test RValue wrapping an array."""
        from logstash_parser.ast_nodes import RValue

        array_node = Array((Number(1), Number(2)))
        rvalue = RValue(array_node)

        assert rvalue.value == array_node

    def test_rvalue_with_method_call(self):
        """Test RValue wrapping a method call."""
        from logstash_parser.ast_nodes import RValue

        method_call = MethodCall("test", (LSString('"arg"'),))
        rvalue = RValue(method_call)

        assert rvalue.value == method_call

    def test_rvalue_to_logstash(self):
        """Test RValue.to_logstash()."""
        from logstash_parser.ast_nodes import RValue

        string_node = LSString('"test"')
        rvalue = RValue(string_node)

        result = rvalue.to_logstash()
        assert result == '"test"'

    def test_rvalue_to_source(self):
        """Test RValue.to_source()."""
        from logstash_parser.ast_nodes import RValue

        number_node = Number(42)
        rvalue = RValue(number_node)

        result = rvalue.to_source()
        assert result == 42

    def test_rvalue_repr(self):
        """Test RValue.__repr__()."""
        from logstash_parser.ast_nodes import RValue

        selector_node = SelectorNode("[field]")
        rvalue = RValue(selector_node)

        repr_str = repr(rvalue)
        # RValue.__repr__ returns the wrapped value's repr
        assert "[field]" in repr_str or "SelectorNode" in repr_str


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

    def test_get_snake_case_key_lsstring(self):
        """Test _get_snake_case_key for LSString."""
        node = LSString('"test"')
        key = node._get_snake_case_key()
        assert key == "lsstring"

    def test_get_snake_case_key_compare_expression(self):
        """Test _get_snake_case_key for CompareExpression."""
        left = SelectorNode("[field]")
        right = Number(100)
        node = CompareExpression(left, "==", right)
        key = node._get_snake_case_key()
        assert key == "compare_expression"

    def test_get_snake_case_key_plugin_section(self):
        """Test _get_snake_case_key for PluginSectionNode."""
        plugin = Plugin("mutate", ())
        node = PluginSectionNode("filter", [plugin])
        key = node._get_snake_case_key()
        assert key == "plugin_section_node"

    def test_get_snake_case_key_method_call(self):
        """Test _get_snake_case_key for MethodCall."""
        node = MethodCall("test", ())
        key = node._get_snake_case_key()
        assert key == "method_call"

    def test_traverse_with_non_astnode_children(self):
        """Test traverse with mixed children types."""
        from logstash_parser.ast_nodes import ASTNode

        node = ASTNode()
        node.children = (LSString('"test"'),)
        # Should not raise error
        node.traverse()

    def test_set_expression_context_simple_node(self):
        """Test setting expression context on simple node."""
        node = LSString('"test"')
        assert node.in_expression_context is False

        node.set_expression_context(True)
        assert node.in_expression_context is True

    def test_set_expression_context_propagates(self):
        """Test that expression context propagates to children."""
        left = SelectorNode("[field]")
        right = Number(100)
        node = CompareExpression(left, "==", right)

        assert node.in_expression_context is True
        assert left.in_expression_context is True
        assert right.in_expression_context is True

        node.set_expression_context(False)
        assert node.in_expression_context is False
        assert left.in_expression_context is False
        assert right.in_expression_context is False

    def test_set_expression_context_nested(self):
        """Test expression context on deeply nested structure."""
        from logstash_parser.ast_nodes import BooleanExpression

        inner_left = SelectorNode("[a]")
        inner_right = Number(1)
        inner_expr = CompareExpression(inner_left, "==", inner_right)

        outer_left = inner_expr
        outer_right = SelectorNode("[b]")
        outer_expr = BooleanExpression(outer_left, "and", outer_right)

        outer_expr.set_expression_context(True)

        assert outer_expr.in_expression_context is True
        assert inner_expr.in_expression_context is True
        assert inner_left.in_expression_context is True
        assert inner_right.in_expression_context is True
        assert outer_right.in_expression_context is True

    def test_set_expression_context_with_non_astnode_children(self):
        """Test set_expression_context with mixed children."""
        from logstash_parser.ast_nodes import ASTNode

        node = ASTNode()
        node.children = (LSString('"test"'),)
        # Should not raise error
        node.set_expression_context(True)

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

    def test_boolean_to_repr(self):
        """Test Boolean.to_repr()."""
        node = Boolean(True)
        repr_str = node.to_repr()
        assert "Boolean" in repr_str
        assert "True" in repr_str

    def test_boolean_to_repr_with_indent(self):
        """Test Boolean.to_repr() with indentation."""
        node = Boolean(False)
        repr_str = node.to_repr(indent=4)
        assert repr_str.startswith("    ")
        assert "Boolean" in repr_str

    def test_selector_to_repr(self):
        """Test SelectorNode.to_repr()."""
        node = SelectorNode("[field]")
        repr_str = node.to_repr()
        assert "SelectorNode" in repr_str
        assert "[field]" in repr_str

    def test_selector_to_repr_with_indent(self):
        """Test SelectorNode.to_repr() with indentation."""
        node = SelectorNode("[field]")
        repr_str = node.to_repr(indent=2)
        assert repr_str.startswith("  ")
