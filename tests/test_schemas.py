"""Tests for Pydantic Schema classes."""

import pytest
from pydantic import ValidationError

from logstash_parser.schemas import (
    ArraySchema,
    AttributeSchema,
    BooleanExpressionData,
    BooleanExpressionSchema,
    BooleanSchema,
    BranchSchema,
    CompareExpressionData,
    CompareExpressionSchema,
    ConfigSchema,
    ElseConditionSchema,
    ElseIfConditionData,
    ElseIfConditionSchema,
    IfConditionData,
    IfConditionSchema,
    InExpressionData,
    InExpressionSchema,
    LSBareWordSchema,
    LSStringSchema,
    MethodCallData,
    MethodCallSchema,
    NegativeExpressionData,
    NegativeExpressionSchema,
    NotInExpressionData,
    NotInExpressionSchema,
    NumberSchema,
    PluginData,
    PluginSchema,
    PluginSectionSchema,
    RegexExpressionData,
    RegexExpressionSchema,
    RegexpSchema,
    SelectorNodeSchema,
)


class TestSimpleSchemas:
    """Test simple schema types."""

    def test_lsstring_schema(self):
        """Test LSStringSchema."""
        schema = LSStringSchema(ls_string='"hello"')
        assert schema.ls_string == '"hello"'

    def test_lsstring_schema_validation(self):
        """Test LSStringSchema validation."""
        with pytest.raises(ValidationError):
            LSStringSchema(wrong_field="test")  # type: ignore

    def test_lsbareword_schema(self):
        """Test LSBareWordSchema."""
        schema = LSBareWordSchema(ls_bare_word="mutate")
        assert schema.ls_bare_word == "mutate"

    def test_number_schema_int(self):
        """Test NumberSchema with integer."""
        schema = NumberSchema(number=123)
        assert schema.number == 123

    def test_number_schema_float(self):
        """Test NumberSchema with float."""
        schema = NumberSchema(number=45.67)
        assert schema.number == 45.67

    def test_boolean_schema_true(self):
        """Test BooleanSchema with True."""
        schema = BooleanSchema(boolean=True)
        assert schema.boolean is True

    def test_boolean_schema_false(self):
        """Test BooleanSchema with False."""
        schema = BooleanSchema(boolean=False)
        assert schema.boolean is False

    def test_regexp_schema(self):
        """Test RegexpSchema."""
        schema = RegexpSchema(regexp="/error/")
        assert schema.regexp == "/error/"

    def test_selector_schema(self):
        """Test SelectorNodeSchema."""
        schema = SelectorNodeSchema(selector_node="[field]")
        assert schema.selector_node == "[field]"


class TestDataStructureSchemas:
    """Test data structure schemas."""

    def test_array_schema(self):
        """Test ArraySchema."""
        schema = ArraySchema(
            array=[
                LSStringSchema(ls_string='"a"'),
                LSStringSchema(ls_string='"b"'),
            ]
        )
        assert len(schema.array) == 2

    def test_hash_schema(self):
        """Test HashSchema."""
        from logstash_parser.schemas import HashSchema

        schema = HashSchema(
            hash={
                '"key"': LSStringSchema(ls_string='"value"'),
            }
        )
        assert len(schema.hash) == 1

    def test_attribute_schema(self):
        """Test AttributeSchema."""
        schema = AttributeSchema(
            {
                "port": NumberSchema(number=5044),
            }
        )
        assert "port" in schema.root


class TestPluginSchemas:
    """Test plugin-related schemas."""

    def test_plugin_schema(self):
        """Test PluginSchema."""
        schema = PluginSchema(
            plugin=PluginData(
                plugin_name="beats",
                attributes=[
                    AttributeSchema(
                        {
                            "port": NumberSchema(number=5044),
                        }
                    )
                ],
            )
        )
        assert schema.plugin.plugin_name == "beats"
        assert len(schema.plugin.attributes) == 1

    def test_plugin_section_schema(self):
        """Test PluginSectionSchema."""
        schema = PluginSectionSchema(
            plugin_section={
                "input": [
                    PluginSchema(
                        plugin=PluginData(
                            plugin_name="beats",
                            attributes=[
                                AttributeSchema(
                                    {
                                        "port": NumberSchema(number=5044),
                                    }
                                )
                            ],
                        )
                    )
                ]
            }
        )
        assert "input" in schema.plugin_section
        assert len(schema.plugin_section["input"]) == 1

    def test_config_schema(self):
        """Test ConfigSchema."""
        schema = ConfigSchema(
            config=[
                PluginSectionSchema(
                    plugin_section={
                        "input": [
                            PluginSchema(
                                plugin=PluginData(
                                    plugin_name="beats",
                                    attributes=[
                                        AttributeSchema(
                                            {
                                                "port": NumberSchema(number=5044),
                                            }
                                        )
                                    ],
                                )
                            )
                        ]
                    }
                )
            ]
        )
        assert len(schema.config) == 1


class TestExpressionSchemas:
    """Test expression schemas."""

    def test_compare_expression_schema(self):
        """Test CompareExpressionSchema."""
        schema = CompareExpressionSchema(
            compare_expression=CompareExpressionData(
                left=SelectorNodeSchema(selector_node="[status]"),
                operator="==",
                right=NumberSchema(number=200),
            )
        )
        assert schema.compare_expression.operator == "=="

    def test_regex_expression_schema(self):
        """Test RegexExpressionSchema."""
        schema = RegexExpressionSchema(
            regex_expression=RegexExpressionData(
                left=SelectorNodeSchema(selector_node="[message]"),
                operator="=~",
                pattern=RegexpSchema(regexp="/error/"),
            )
        )
        assert schema.regex_expression.operator == "=~"

    def test_in_expression_schema(self):
        """Test InExpressionSchema."""
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
        assert schema.in_expression.operator == "in"

    def test_not_in_expression_schema(self):
        """Test NotInExpressionSchema."""
        schema = NotInExpressionSchema(
            not_in_expression=NotInExpressionData(
                value=SelectorNodeSchema(selector_node="[status]"),
                operator="not in",
                collection=ArraySchema(array=[NumberSchema(number=400)]),
            )
        )
        assert schema.not_in_expression.operator == "not in"

    def test_negative_expression_schema(self):
        """Test NegativeExpressionSchema."""
        schema = NegativeExpressionSchema(
            negative_expression=NegativeExpressionData(
                operator="!",
                expression=SelectorNodeSchema(selector_node="[field]"),
            )
        )
        assert schema.negative_expression.operator == "!"

    def test_boolean_expression_schema(self):
        """Test BooleanExpressionSchema."""
        schema = BooleanExpressionSchema(
            boolean_expression=BooleanExpressionData(
                left=CompareExpressionSchema(
                    compare_expression=CompareExpressionData(
                        left=SelectorNodeSchema(selector_node="[status]"),
                        operator="==",
                        right=NumberSchema(number=200),
                    )
                ),
                operator="and",
                right=CompareExpressionSchema(
                    compare_expression=CompareExpressionData(
                        left=SelectorNodeSchema(selector_node="[method]"),
                        operator="==",
                        right=LSStringSchema(ls_string='"GET"'),
                    )
                ),
            )
        )
        assert schema.boolean_expression.operator == "and"


class TestConditionalSchemas:
    """Test conditional branch schemas."""

    def test_if_condition_schema(self):
        """Test IfConditionSchema."""
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
                            attributes=[
                                AttributeSchema(
                                    {
                                        "add_tag": ArraySchema(array=[LSStringSchema(ls_string='"nginx"')]),
                                    }
                                )
                            ],
                        )
                    )
                ],
            )
        )
        assert schema.if_condition is not None

    def test_else_if_condition_schema(self):
        """Test ElseIfConditionSchema."""
        schema = ElseIfConditionSchema(
            else_if_condition=ElseIfConditionData(
                expr=CompareExpressionSchema(
                    compare_expression=CompareExpressionData(
                        left=SelectorNodeSchema(selector_node="[type]"),
                        operator="==",
                        right=LSStringSchema(ls_string='"syslog"'),
                    )
                ),
                body=[PluginSchema(plugin=PluginData(plugin_name="mutate", attributes=[]))],
            )
        )
        assert schema.else_if_condition is not None

    def test_else_condition_schema(self):
        """Test ElseConditionSchema."""
        schema = ElseConditionSchema(
            else_condition=[PluginSchema(plugin=PluginData(plugin_name="mutate", attributes=[]))]
        )
        assert schema.else_condition is not None

    def test_branch_schema(self):
        """Test BranchSchema."""
        schema = BranchSchema(
            branch=[
                IfConditionSchema(
                    if_condition=IfConditionData(
                        expr=CompareExpressionSchema(
                            compare_expression=CompareExpressionData(
                                left=SelectorNodeSchema(selector_node="[type]"),
                                operator="==",
                                right=LSStringSchema(ls_string='"nginx"'),
                            )
                        ),
                        body=[PluginSchema(plugin=PluginData(plugin_name="mutate", attributes=[]))],
                    )
                )
            ]
        )
        assert len(schema.branch) == 1


class TestSchemaSerialization:
    """Test schema serialization."""

    def test_schema_to_dict(self):
        """Test schema model_dump."""
        schema = LSStringSchema(ls_string='"test"')
        data = schema.model_dump()
        assert data["ls_string"] == '"test"'

    def test_schema_to_json(self):
        """Test schema model_dump_json."""
        schema = LSStringSchema(ls_string='"test"')
        json_str = schema.model_dump_json()
        assert isinstance(json_str, str)
        assert "ls_string" in json_str

    def test_schema_from_dict(self):
        """Test schema model_validate."""
        data = {"ls_string": '"test"'}
        schema = LSStringSchema.model_validate(data)
        assert schema.ls_string == '"test"'

    def test_schema_from_json(self):
        """Test schema model_validate_json."""
        json_str = '{"ls_string": "\\"test\\""}'
        schema = LSStringSchema.model_validate_json(json_str)
        assert schema.ls_string == '"test"'


class TestMethodCallSchema:
    """Test MethodCallSchema validation."""

    def test_method_call_schema_valid(self):
        """Test valid MethodCallSchema."""
        schema = MethodCallSchema(
            method_call=MethodCallData(
                method_name="test",
                arguments=[LSStringSchema(ls_string='"arg"')],
            )
        )

        assert schema.method_call.method_name == "test"
        assert len(schema.method_call.arguments) == 1

    def test_method_call_schema_empty_args(self):
        """Test MethodCallSchema with empty arguments."""
        schema = MethodCallSchema(
            method_call=MethodCallData(
                method_name="now",
                arguments=[],
            )
        )

        assert schema.method_call.method_name == "now"
        assert len(schema.method_call.arguments) == 0

    def test_method_call_schema_validation_error(self):
        """Test MethodCallSchema validation error."""
        with pytest.raises(ValidationError):
            MethodCallSchema(
                method_call=MethodCallData(
                    method_name="test",
                    arguments="not_a_list",  # type: ignore
                )
            )

    def test_method_call_schema_extra_fields_forbidden(self):
        """Test that extra fields are forbidden in MethodCallSchema."""
        with pytest.raises(ValidationError):
            MethodCallSchema(
                method_call=MethodCallData(
                    method_name="test",
                    arguments=[],
                    extra_field="not_allowed",  # type: ignore
                )
            )


class TestSchemaValidation:
    """Test schema validation."""

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            LSStringSchema(
                ls_string='"test"',
                extra_field="not_allowed",  # type: ignore
            )

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            LSStringSchema()  # type: ignore

    def test_type_validation(self):
        """Test that types are validated."""
        with pytest.raises(ValidationError):
            NumberSchema(number="not_a_number")  # type: ignore
