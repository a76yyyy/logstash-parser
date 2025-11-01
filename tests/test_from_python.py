"""Tests for creating AST nodes from Python/Pydantic schemas."""

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
    NegativeExpression,
    NotInExpression,
    Number,
    Plugin,
    PluginSectionNode,
    RegexExpression,
    Regexp,
    SelectorNode,
)
from logstash_parser.schemas import (
    ArraySchema,
    AttributeSchema,
    BooleanSchema,
    BranchSchema,
    CompareExpressionData,
    CompareExpressionSchema,
    ConfigSchema,
    ElseConditionSchema,
    ElseIfConditionData,
    ElseIfConditionSchema,
    HashSchema,
    IfConditionData,
    IfConditionSchema,
    InExpressionData,
    InExpressionSchema,
    LSBareWordSchema,
    LSStringSchema,
    NegativeExpressionData,
    NegativeExpressionSchema,
    NotInExpressionData,
    NotInExpressionSchema,
    NumberSchema,
    PluginData,
    PluginSchema,
    PluginSectionData,
    PluginSectionSchema,
    RegexExpressionData,
    RegexExpressionSchema,
    RegexpSchema,
    SelectorNodeSchema,
)


class TestSimpleNodesFromPython:
    """Test creating simple AST nodes from Python/Pydantic."""

    def test_lsstring_from_pydantic(self):
        """Test LSString.from_python() with Pydantic schema."""
        schema = LSStringSchema(ls_string='"test"')
        node = LSString.from_python(schema)
        assert isinstance(node, LSString)
        assert node.lexeme == '"test"'
        assert node.value == "test"

    def test_lsstring_from_dict(self):
        """Test LSString.from_python() with dict."""
        data = {"ls_string": '"hello"'}
        node = LSString.from_python(data)
        assert isinstance(node, LSString)
        assert node.lexeme == '"hello"'
        assert node.value == "hello"

    def test_lsbareword_from_pydantic(self):
        """Test LSBareWord.from_python() with Pydantic schema."""
        schema = LSBareWordSchema(ls_bare_word="mutate")
        node = LSBareWord.from_python(schema)
        assert isinstance(node, LSBareWord)
        assert node.value == "mutate"

    def test_lsbareword_from_dict(self):
        """Test LSBareWord.from_python() with dict."""
        data = {"ls_bare_word": "grok"}
        node = LSBareWord.from_python(data)
        assert isinstance(node, LSBareWord)
        assert node.value == "grok"

    def test_number_from_pydantic_int(self):
        """Test Number.from_python() with integer."""
        schema = NumberSchema(number=123)
        node = Number.from_python(schema)
        assert isinstance(node, Number)
        assert node.value == 123

    def test_number_from_pydantic_float(self):
        """Test Number.from_python() with float."""
        schema = NumberSchema(number=45.67)
        node = Number.from_python(schema)
        assert isinstance(node, Number)
        assert node.value == 45.67

    def test_number_from_dict(self):
        """Test Number.from_python() with dict."""
        data = {"number": 999}
        node = Number.from_python(data)
        assert isinstance(node, Number)
        assert node.value == 999

    def test_boolean_from_pydantic_true(self):
        """Test Boolean.from_python() with True."""
        schema = BooleanSchema(boolean=True)
        node = Boolean.from_python(schema)
        assert isinstance(node, Boolean)
        assert node.value is True

    def test_boolean_from_pydantic_false(self):
        """Test Boolean.from_python() with False."""
        schema = BooleanSchema(boolean=False)
        node = Boolean.from_python(schema)
        assert isinstance(node, Boolean)
        assert node.value is False

    def test_boolean_from_dict(self):
        """Test Boolean.from_python() with dict."""
        data = {"boolean": True}
        node = Boolean.from_python(data)
        assert isinstance(node, Boolean)
        assert node.value is True

    def test_regexp_from_pydantic(self):
        """Test Regexp.from_python() with Pydantic schema."""
        schema = RegexpSchema(regexp="/error/")
        node = Regexp.from_python(schema)
        assert isinstance(node, Regexp)
        assert node.lexeme == "/error/"

    def test_regexp_from_dict(self):
        """Test Regexp.from_python() with dict."""
        data = {"regexp": "/test/"}
        node = Regexp.from_python(data)
        assert isinstance(node, Regexp)
        assert node.lexeme == "/test/"

    def test_selector_from_pydantic(self):
        """Test SelectorNode.from_python() with Pydantic schema."""
        schema = SelectorNodeSchema(selector_node="[field]")
        node = SelectorNode.from_python(schema)
        assert isinstance(node, SelectorNode)
        assert node.raw == "[field]"

    def test_selector_from_dict(self):
        """Test SelectorNode.from_python() with dict."""
        data = {"selector_node": "[status]"}
        node = SelectorNode.from_python(data)
        assert isinstance(node, SelectorNode)
        assert node.raw == "[status]"


class TestDataStructureNodesFromPython:
    """Test creating data structure AST nodes from Python/Pydantic."""

    def test_array_from_pydantic(self):
        """Test Array.from_python() with Pydantic schema."""
        schema = ArraySchema(
            array=[
                LSStringSchema(ls_string='"a"'),
                LSStringSchema(ls_string='"b"'),
                NumberSchema(number=123),
            ]
        )
        node = Array.from_python(schema)
        assert isinstance(node, Array)
        assert len(node.children) == 3
        assert isinstance(node.children[0], LSString)
        assert isinstance(node.children[1], LSString)
        assert isinstance(node.children[2], Number)

    def test_array_from_dict(self):
        """Test Array.from_python() with dict."""
        data = {
            "array": [
                {"ls_string": '"x"'},
                {"number": 456},
            ]
        }
        node = Array.from_python(data)
        assert isinstance(node, Array)
        assert len(node.children) == 2

    def test_hash_from_pydantic(self):
        """Test Hash.from_python() with Pydantic schema."""
        schema = HashSchema(
            hash={
                '"key1"': LSStringSchema(ls_string='"value1"'),
                '"key2"': NumberSchema(number=100),
            }
        )
        node = Hash.from_python(schema)
        assert isinstance(node, Hash)
        assert len(node.children) == 2
        assert all(isinstance(child, HashEntryNode) for child in node.children)

    def test_hash_from_dict(self):
        """Test Hash.from_python() with dict."""
        data = {
            "hash": {
                '"field"': {"ls_string": '"value"'},
            }
        }
        node = Hash.from_python(data)
        assert isinstance(node, Hash)
        assert len(node.children) == 1

    def test_attribute_from_pydantic(self):
        """Test Attribute.from_python() with Pydantic schema."""
        schema = AttributeSchema(
            {
                "port": NumberSchema(number=5044),
            }
        )
        node = Attribute.from_python(schema)
        assert isinstance(node, Attribute)
        assert isinstance(node.name, LSBareWord)
        assert node.name.value == "port"
        assert isinstance(node.value, Number)
        assert node.value.value == 5044

    def test_attribute_from_dict(self):
        """Test Attribute.from_python() with dict."""
        data = {
            "host": {"ls_string": '"0.0.0.0"'},
        }
        node = Attribute.from_python(data)
        assert isinstance(node, Attribute)
        assert node.name.value == "host"


class TestPluginNodesFromPython:
    """Test creating plugin AST nodes from Python/Pydantic."""

    def test_plugin_from_pydantic(self):
        """Test Plugin.from_python() with Pydantic schema."""
        schema = PluginSchema(
            plugin=PluginData(
                plugin_name="beats",
                attributes=[
                    AttributeSchema({"port": NumberSchema(number=5044)}),
                    AttributeSchema({"host": LSStringSchema(ls_string='"0.0.0.0"')}),
                ],
            )
        )
        node = Plugin.from_python(schema)
        assert isinstance(node, Plugin)
        assert node.plugin_name == "beats"
        assert len(node.children) == 2

    def test_plugin_from_dict(self):
        """Test Plugin.from_python() with dict."""
        data = {
            "plugin": {
                "plugin_name": "mutate",
                "attributes": [
                    {"add_tag": {"array": [{"ls_string": '"test"'}]}},
                ],
            }
        }
        node = Plugin.from_python(data)
        assert isinstance(node, Plugin)
        assert node.plugin_name == "mutate"
        assert len(node.children) == 1

    def test_plugin_section_from_pydantic(self):
        """Test PluginSectionNode.from_python() with Pydantic schema."""
        schema = PluginSectionSchema(
            plugin_section=PluginSectionData(
                plugin_type="input",
                children=[
                    PluginSchema(
                        plugin=PluginData(
                            plugin_name="file",
                            attributes=[
                                AttributeSchema({"path": LSStringSchema(ls_string='"/var/log/test.log"')}),
                            ],
                        )
                    )
                ],
            )
        )
        node = PluginSectionNode.from_python(schema)
        assert isinstance(node, PluginSectionNode)
        assert node.plugin_type == "input"
        assert len(node.children) == 1

    def test_plugin_section_from_dict(self):
        """Test PluginSectionNode.from_python() with dict."""
        data = {
            "plugin_section": {
                "plugin_type": "filter",
                "children": [
                    {
                        "plugin": {
                            "plugin_name": "grok",
                            "attributes": [],
                        }
                    }
                ],
            }
        }
        node = PluginSectionNode.from_python(data)
        assert isinstance(node, PluginSectionNode)
        assert node.plugin_type == "filter"

    def test_config_from_pydantic(self):
        """Test Config.from_python() with Pydantic schema."""
        schema = ConfigSchema(
            config=[
                PluginSectionSchema(
                    plugin_section=PluginSectionData(
                        plugin_type="input",
                        children=[
                            PluginSchema(
                                plugin=PluginData(
                                    plugin_name="stdin",
                                    attributes=[],
                                )
                            )
                        ],
                    )
                )
            ]
        )
        node = Config.from_python(schema)
        assert isinstance(node, Config)
        assert len(node.children) == 1

    def test_config_from_dict(self):
        """Test Config.from_python() with dict."""
        data = {
            "config": [
                {
                    "plugin_section": {
                        "plugin_type": "output",
                        "children": [
                            {
                                "plugin": {
                                    "plugin_name": "stdout",
                                    "attributes": [],
                                }
                            }
                        ],
                    }
                }
            ]
        }
        node = Config.from_python(data)
        assert isinstance(node, Config)
        assert len(node.children) == 1


class TestExpressionNodesFromPython:
    """Test creating expression AST nodes from Python/Pydantic."""

    def test_compare_expression_from_pydantic(self):
        """Test CompareExpression.from_python() with Pydantic schema."""
        schema = CompareExpressionSchema(
            compare_expression=CompareExpressionData(
                left=SelectorNodeSchema(selector_node="[status]"),
                operator="==",
                right=NumberSchema(number=200),
            )
        )
        node = CompareExpression.from_python(schema)
        assert isinstance(node, CompareExpression)
        assert node.operator == "=="
        assert isinstance(node.left, SelectorNode)
        assert isinstance(node.right, Number)

    def test_compare_expression_from_dict(self):
        """Test CompareExpression.from_python() with dict."""
        data = {
            "compare_expression": {
                "left": {"selector_node": "[field]"},
                "operator": "!=",
                "right": {"ls_string": '"value"'},
            }
        }
        node = CompareExpression.from_python(data)
        assert isinstance(node, CompareExpression)
        assert node.operator == "!="

    def test_regex_expression_from_pydantic(self):
        """Test RegexExpression.from_python() with Pydantic schema."""
        schema = RegexExpressionSchema(
            regex_expression=RegexExpressionData(
                left=SelectorNodeSchema(selector_node="[message]"),
                operator="=~",
                pattern=RegexpSchema(regexp="/error/"),
            )
        )
        node = RegexExpression.from_python(schema)
        assert isinstance(node, RegexExpression)
        assert node.operator == "=~"
        assert isinstance(node.pattern, Regexp)

    def test_regex_expression_from_dict(self):
        """Test RegexExpression.from_python() with dict."""
        data = {
            "regex_expression": {
                "left": {"selector_node": "[log]"},
                "operator": "!~",
                "pattern": {"regexp": "/success/"},
            }
        }
        node = RegexExpression.from_python(data)
        assert isinstance(node, RegexExpression)
        assert node.operator == "!~"

    def test_in_expression_from_pydantic(self):
        """Test InExpression.from_python() with Pydantic schema."""
        schema = InExpressionSchema(
            in_expression=InExpressionData(
                value=SelectorNodeSchema(selector_node="[status]"),
                operator="in",
                collection=ArraySchema(
                    array=[
                        NumberSchema(number=200),
                        NumberSchema(number=201),
                    ]
                ),
            )
        )
        node = InExpression.from_python(schema)
        assert isinstance(node, InExpression)
        assert node.operator == "in"

    def test_in_expression_from_dict(self):
        """Test InExpression.from_python() with dict."""
        data = {
            "in_expression": {
                "value": {"selector_node": "[code]"},
                "operator": "in",
                "collection": {"array": [{"number": 404}, {"number": 500}]},
            }
        }
        node = InExpression.from_python(data)
        assert isinstance(node, InExpression)

    def test_not_in_expression_from_pydantic(self):
        """Test NotInExpression.from_python() with Pydantic schema."""
        schema = NotInExpressionSchema(
            not_in_expression=NotInExpressionData(
                value=SelectorNodeSchema(selector_node="[type]"),
                operator="not in",
                collection=ArraySchema(
                    array=[
                        LSStringSchema(ls_string='"error"'),
                    ]
                ),
            )
        )
        node = NotInExpression.from_python(schema)
        assert isinstance(node, NotInExpression)
        assert node.operator == "not in"

    def test_not_in_expression_from_dict(self):
        """Test NotInExpression.from_python() with dict."""
        data = {
            "not_in_expression": {
                "value": {"selector_node": "[level]"},
                "operator": "not in",
                "collection": {"array": [{"ls_string": '"debug"'}]},
            }
        }
        node = NotInExpression.from_python(data)
        assert isinstance(node, NotInExpression)

    def test_negative_expression_from_pydantic(self):
        """Test NegativeExpression.from_python() with Pydantic schema."""
        schema = NegativeExpressionSchema(
            negative_expression=NegativeExpressionData(
                operator="!",
                expression=SelectorNodeSchema(selector_node="[field]"),
            )
        )
        node = NegativeExpression.from_python(schema)
        assert isinstance(node, NegativeExpression)
        assert node.operator == "!"

    def test_negative_expression_from_dict(self):
        """Test NegativeExpression.from_python() with dict."""
        data = {
            "negative_expression": {
                "operator": "!",
                "expression": {"selector_node": "[exists]"},
            }
        }
        node = NegativeExpression.from_python(data)
        assert isinstance(node, NegativeExpression)


class TestConditionalNodesFromPython:
    """Test creating conditional AST nodes from Python/Pydantic."""

    def test_if_condition_from_pydantic(self):
        """Test IfCondition.from_python() with Pydantic schema."""
        schema = IfConditionSchema(
            if_condition=IfConditionData(
                expr=CompareExpressionSchema(
                    compare_expression=CompareExpressionData(
                        left=SelectorNodeSchema(selector_node="[type]"),
                        operator="==",
                        right=LSStringSchema(ls_string='"nginx"'),
                    )
                ),
                body=[
                    PluginSchema(
                        plugin=PluginData(
                            plugin_name="mutate",
                            attributes=[],
                        )
                    )
                ],
            )
        )
        node = IfCondition.from_python(schema)
        assert isinstance(node, IfCondition)
        assert len(node.children) == 1

    def test_if_condition_from_dict(self):
        """Test IfCondition.from_python() with dict."""
        data = {
            "if_condition": {
                "expr": {
                    "compare_expression": {
                        "left": {"selector_node": "[status]"},
                        "operator": ">=",
                        "right": {"number": 400},
                    }
                },
                "body": [
                    {
                        "plugin": {
                            "plugin_name": "drop",
                            "attributes": [],
                        }
                    }
                ],
            }
        }
        node = IfCondition.from_python(data)
        assert isinstance(node, IfCondition)

    def test_else_if_condition_from_pydantic(self):
        """Test ElseIfCondition.from_python() with Pydantic schema."""
        schema = ElseIfConditionSchema(
            else_if_condition=ElseIfConditionData(
                expr=CompareExpressionSchema(
                    compare_expression=CompareExpressionData(
                        left=SelectorNodeSchema(selector_node="[type]"),
                        operator="==",
                        right=LSStringSchema(ls_string='"syslog"'),
                    )
                ),
                body=[],
            )
        )
        node = ElseIfCondition.from_python(schema)
        assert isinstance(node, ElseIfCondition)

    def test_else_if_condition_from_dict(self):
        """Test ElseIfCondition.from_python() with dict."""
        data = {
            "else_if_condition": {
                "expr": {
                    "selector_node": "[enabled]",
                },
                "body": [],
            }
        }
        node = ElseIfCondition.from_python(data)
        assert isinstance(node, ElseIfCondition)

    def test_else_condition_from_pydantic(self):
        """Test ElseCondition.from_python() with Pydantic schema."""
        schema = ElseConditionSchema(
            else_condition=[
                PluginSchema(
                    plugin=PluginData(
                        plugin_name="mutate",
                        attributes=[],
                    )
                )
            ]
        )
        node = ElseCondition.from_python(schema)
        assert isinstance(node, ElseCondition)
        assert len(node.children) == 1

    def test_else_condition_from_dict(self):
        """Test ElseCondition.from_python() with dict."""
        data = {
            "else_condition": [
                {
                    "plugin": {
                        "plugin_name": "drop",
                        "attributes": [],
                    }
                }
            ]
        }
        node = ElseCondition.from_python(data)
        assert isinstance(node, ElseCondition)

    def test_branch_from_pydantic(self):
        """Test Branch.from_python() with Pydantic schema."""
        branch = [
            IfConditionSchema(
                if_condition=IfConditionData(
                    expr=SelectorNodeSchema(selector_node="[field]"),
                    body=[],
                )
            ),
            ElseConditionSchema(else_condition=[]),
        ]
        schema = BranchSchema(branch=branch)
        node = Branch.from_python(schema)
        assert isinstance(node, Branch)
        assert len(node.children) == 2

    def test_branch_from_dict(self):
        """Test Branch.from_python() with dict."""
        data = {
            "branch": [
                {
                    "if_condition": {
                        "expr": {"selector_node": "[test]"},
                        "body": [],
                    }
                }
            ]
        }
        node = Branch.from_python(data)
        assert isinstance(node, Branch)


class TestComplexRoundtrip:
    """Test complex roundtrip conversions."""

    def test_full_config_roundtrip(self):
        """Test full config: AST -> Pydantic -> AST."""
        from logstash_parser import parse_logstash_config

        config = """
        input {
            beats {
                port => 5044
            }
        }

        filter {
            if [type] == "nginx" {
                grok {
                    match => { "message" => "%{PATTERN}" }
                }
            }
        }

        output {
            elasticsearch {
                hosts => ["localhost:9200"]
            }
        }
        """

        # Parse to AST
        ast1 = parse_logstash_config(config)

        # Convert to Pydantic
        schema = ast1.to_python(as_pydantic=True)

        # Convert back to AST
        ast2 = Config.from_python(schema)

        # Compare
        assert ast1.to_python() == ast2.to_python()

    def test_nested_structures_roundtrip(self):
        """Test nested structures roundtrip."""
        from logstash_parser import parse_logstash_config

        config = """
        filter {
            mutate {
                add_field => {
                    "level1" => {
                        "level2" => {
                            "level3" => "value"
                        }
                    }
                }
            }
        }
        """

        ast1 = parse_logstash_config(config)
        schema = ast1.to_python(as_pydantic=True)
        ast2 = Config.from_python(schema)

        assert ast1.to_python() == ast2.to_python()
