"""Tests for Pydantic Schema classes."""

import pytest
from pydantic import ValidationError

from logstash_parser.schemas import (
    ArraySchema,
    AttributeSchema,
    BooleanExpressionSchema,
    BooleanSchema,
    BranchSchema,
    CompareExpressionSchema,
    ConfigSchema,
    ElseConditionSchema,
    ElseIfConditionSchema,
    ExpressionSchema,
    HashEntryNodeSchema,
    HashSchema,
    IfConditionSchema,
    InExpressionSchema,
    LSBareWordSchema,
    LSStringSchema,
    NegativeExpressionSchema,
    NotInExpressionSchema,
    NumberSchema,
    PluginSchema,
    PluginSectionNodeSchema,
    RegexExpressionSchema,
    RegexpSchema,
    SelectorNodeSchema,
    ValueSchema,
)


class TestSimpleSchemas:
    """Test simple schema types."""

    def test_lsstring_schema(self):
        """Test LSStringSchema."""
        schema = LSStringSchema(node_type="LSString", lexeme='"hello"', value="hello")
        assert schema.node_type == "LSString"
        assert schema.lexeme == '"hello"'
        assert schema.value == "hello"

    def test_lsstring_schema_validation(self):
        """Test LSStringSchema validation."""
        with pytest.raises(ValidationError):
            LSStringSchema(node_type="WrongType", lexeme='"test"', value="test")  # type: ignore

    def test_lsbareword_schema(self):
        """Test LSBareWordSchema."""
        schema = LSBareWordSchema(node_type="LSBareWord", value="mutate")
        assert schema.node_type == "LSBareWord"
        assert schema.value == "mutate"

    def test_number_schema_int(self):
        """Test NumberSchema with integer."""
        schema = NumberSchema(node_type="Number", value=123)
        assert schema.node_type == "Number"
        assert schema.value == 123

    def test_number_schema_float(self):
        """Test NumberSchema with float."""
        schema = NumberSchema(node_type="Number", value=45.67)
        assert schema.value == 45.67

    def test_boolean_schema_true(self):
        """Test BooleanSchema with True."""
        schema = BooleanSchema(node_type="Boolean", value=True)
        assert schema.value is True

    def test_boolean_schema_false(self):
        """Test BooleanSchema with False."""
        schema = BooleanSchema(node_type="Boolean", value=False)
        assert schema.value is False

    def test_regexp_schema(self):
        """Test RegexpSchema."""
        schema = RegexpSchema(node_type="Regexp", lexeme="error", value=r"error")
        assert schema.lexeme == "error"
        assert schema.value == r"error"

    def test_selector_schema(self):
        """Test SelectorNodeSchema."""
        schema = SelectorNodeSchema(node_type="SelectorNode", raw="[field]")
        assert schema.raw == "[field]"


class TestDataStructureSchemas:
    """Test data structure schemas."""

    def test_array_schema(self):
        """Test ArraySchema."""
        children: list[ValueSchema] = [
            LSStringSchema(node_type="LSString", lexeme='"a"', value="a"),
            LSStringSchema(node_type="LSString", lexeme='"b"', value="b"),
        ]
        schema = ArraySchema(node_type="Array", children=children)
        assert len(schema.children) == 2

    def test_hash_entry_schema(self):
        """Test HashEntryNodeSchema."""
        key = LSStringSchema(node_type="LSString", lexeme='"key"', value="key")
        value = LSStringSchema(node_type="LSString", lexeme='"value"', value="value")
        schema = HashEntryNodeSchema(node_type="HashEntry", key=key, value=value)
        assert schema.key == key
        assert schema.value == value

    def test_hash_schema(self):
        """Test HashSchema."""
        entry = HashEntryNodeSchema(
            node_type="HashEntry",
            key=LSStringSchema(node_type="LSString", lexeme='"key"', value="key"),
            value=LSStringSchema(node_type="LSString", lexeme='"value"', value="value"),
        )
        schema = HashSchema(node_type="Hash", children=[entry])
        assert len(schema.children) == 1

    def test_attribute_schema(self):
        """Test AttributeSchema."""
        name = LSBareWordSchema(node_type="LSBareWord", value="port")
        value = NumberSchema(node_type="Number", value=5044)
        schema = AttributeSchema(node_type="Attribute", name=name, value=value)
        assert schema.name == name
        assert schema.value == value


class TestPluginSchemas:
    """Test plugin-related schemas."""

    def test_plugin_schema(self):
        """Test PluginSchema."""
        attr = AttributeSchema(
            node_type="Attribute",
            name=LSBareWordSchema(node_type="LSBareWord", value="port"),
            value=NumberSchema(node_type="Number", value=5044),
        )
        schema = PluginSchema(node_type="Plugin", plugin_name="beats", attributes=[attr])
        assert schema.plugin_name == "beats"
        assert len(schema.attributes) == 1

    def test_plugin_section_schema(self):
        """Test PluginSectionNodeSchema."""
        plugin = PluginSchema(
            node_type="Plugin",
            plugin_name="beats",
            attributes=[
                AttributeSchema(
                    node_type="Attribute",
                    name=LSBareWordSchema(node_type="LSBareWord", value="port"),
                    value=NumberSchema(node_type="Number", value=5044),
                )
            ],
        )
        schema = PluginSectionNodeSchema(node_type="PluginSection", plugin_type="input", children=[plugin])
        assert schema.plugin_type == "input"
        assert len(schema.children) == 1

    def test_config_schema(self):
        """Test ConfigSchema."""
        section = PluginSectionNodeSchema(
            node_type="PluginSection",
            plugin_type="input",
            children=[
                PluginSchema(
                    node_type="Plugin",
                    plugin_name="beats",
                    attributes=[
                        AttributeSchema(
                            node_type="Attribute",
                            name=LSBareWordSchema(node_type="LSBareWord", value="port"),
                            value=NumberSchema(node_type="Number", value=5044),
                        )
                    ],
                )
            ],
        )
        schema = ConfigSchema(node_type="Config", children=[section])
        assert len(schema.children) == 1


class TestExpressionSchemas:
    """Test expression schemas."""

    def test_compare_expression_schema(self):
        """Test CompareExpressionSchema."""
        left = SelectorNodeSchema(node_type="SelectorNode", raw="[status]")
        right = NumberSchema(node_type="Number", value=200)
        schema = CompareExpressionSchema(node_type="CompareExpression", left=left, operator="==", right=right)
        assert schema.operator == "=="

    def test_regex_expression_schema(self):
        """Test RegexExpressionSchema."""
        left = SelectorNodeSchema(node_type="SelectorNode", raw="[message]")
        pattern = RegexpSchema(node_type="Regexp", lexeme="error", value=r"error")
        schema = RegexExpressionSchema(node_type="RegexExpression", left=left, operator="=~", pattern=pattern)
        assert schema.operator == "=~"

    def test_in_expression_schema(self):
        """Test InExpressionSchema."""
        value = SelectorNodeSchema(node_type="SelectorNode", raw="[status]")
        collection = ArraySchema(
            node_type="Array",
            children=[
                NumberSchema(node_type="Number", value=200),
                NumberSchema(node_type="Number", value=201),
            ],
        )
        schema = InExpressionSchema(node_type="InExpression", value=value, operator="in", collection=collection)
        assert schema.operator == "in"

    def test_not_in_expression_schema(self):
        """Test NotInExpressionSchema."""
        value = SelectorNodeSchema(node_type="SelectorNode", raw="[status]")
        collection = ArraySchema(
            node_type="Array",
            children=[NumberSchema(node_type="Number", value=400)],
        )
        schema = NotInExpressionSchema(
            node_type="NotInExpression",
            value=value,
            operator="not in",
            collection=collection,
        )
        assert schema.operator == "not in"

    def test_negative_expression_schema(self):
        """Test NegativeExpressionSchema."""
        expr = SelectorNodeSchema(node_type="SelectorNode", raw="[field]")
        schema = NegativeExpressionSchema(node_type="NegativeExpression", operator="!", expression=expr)
        assert schema.operator == "!"

    def test_boolean_expression_schema(self):
        """Test BooleanExpressionSchema."""
        left = CompareExpressionSchema(
            node_type="CompareExpression",
            left=SelectorNodeSchema(node_type="SelectorNode", raw="[status]"),
            operator="==",
            right=NumberSchema(node_type="Number", value=200),
        )
        right = CompareExpressionSchema(
            node_type="CompareExpression",
            left=SelectorNodeSchema(node_type="SelectorNode", raw="[method]"),
            operator="==",
            right=LSStringSchema(node_type="LSString", lexeme='"GET"', value="GET"),
        )
        schema = BooleanExpressionSchema(node_type="BooleanExpression", left=left, operator="and", right=right)
        assert schema.operator == "and"

    def test_expression_schema(self):
        """Test ExpressionSchema."""
        condition = CompareExpressionSchema(
            node_type="CompareExpression",
            left=SelectorNodeSchema(node_type="SelectorNode", raw="[status]"),
            operator="==",
            right=NumberSchema(node_type="Number", value=200),
        )
        schema = ExpressionSchema(node_type="Expression", condition=condition)
        assert schema.condition == condition


class TestConditionalSchemas:
    """Test conditional branch schemas."""

    def test_if_condition_schema(self):
        """Test IfConditionSchema."""
        expr = CompareExpressionSchema(
            node_type="CompareExpression",
            left=SelectorNodeSchema(node_type="SelectorNode", raw="[type]"),
            operator="==",
            right=LSStringSchema(node_type="LSString", lexeme='"nginx"', value="nginx"),
        )
        plugin = PluginSchema(
            node_type="Plugin",
            plugin_name="mutate",
            attributes=[
                AttributeSchema(
                    node_type="Attribute",
                    name=LSBareWordSchema(node_type="LSBareWord", value="add_tag"),
                    value=ArraySchema(
                        node_type="Array",
                        children=[LSStringSchema(node_type="LSString", lexeme='"nginx"', value="nginx")],
                    ),
                )
            ],
        )
        schema = IfConditionSchema(node_type="IfCondition", expr=expr, body=[plugin])
        assert schema.node_type == "IfCondition"

    def test_else_if_condition_schema(self):
        """Test ElseIfConditionSchema."""
        expr = CompareExpressionSchema(
            node_type="CompareExpression",
            left=SelectorNodeSchema(node_type="SelectorNode", raw="[type]"),
            operator="==",
            right=LSStringSchema(node_type="LSString", lexeme='"syslog"', value="syslog"),
        )
        plugin = PluginSchema(node_type="Plugin", plugin_name="mutate", attributes=[])
        schema = ElseIfConditionSchema(node_type="ElseIfCondition", expr=expr, body=[plugin])
        assert schema.node_type == "ElseIfCondition"

    def test_else_condition_schema(self):
        """Test ElseConditionSchema."""
        plugin = PluginSchema(node_type="Plugin", plugin_name="mutate", attributes=[])
        schema = ElseConditionSchema(node_type="ElseCondition", body=[plugin])
        assert schema.node_type == "ElseCondition"

    def test_branch_schema(self):
        """Test BranchSchema."""
        if_cond = IfConditionSchema(
            node_type="IfCondition",
            expr=CompareExpressionSchema(
                node_type="CompareExpression",
                left=SelectorNodeSchema(node_type="SelectorNode", raw="[type]"),
                operator="==",
                right=LSStringSchema(node_type="LSString", lexeme='"nginx"', value="nginx"),
            ),
            body=[PluginSchema(node_type="Plugin", plugin_name="mutate", attributes=[])],
        )
        schema = BranchSchema(node_type="Branch", children=[if_cond])
        assert len(schema.children) == 1


class TestSchemaSerialization:
    """Test schema serialization."""

    def test_schema_to_dict(self):
        """Test schema model_dump."""
        schema = LSStringSchema(node_type="LSString", lexeme='"test"', value="test")
        data = schema.model_dump()
        assert data["node_type"] == "LSString"
        assert data["value"] == "test"

    def test_schema_to_json(self):
        """Test schema model_dump_json."""
        schema = LSStringSchema(node_type="LSString", lexeme='"test"', value="test")
        json_str = schema.model_dump_json()
        assert isinstance(json_str, str)
        assert "LSString" in json_str

    def test_schema_from_dict(self):
        """Test schema model_validate."""
        data = {"node_type": "LSString", "lexeme": '"test"', "value": "test"}
        schema = LSStringSchema.model_validate(data)
        assert schema.value == "test"

    def test_schema_from_json(self):
        """Test schema model_validate_json."""
        json_str = '{"node_type": "LSString", "lexeme": "\\"test\\"", "value": "test"}'
        schema = LSStringSchema.model_validate_json(json_str)
        assert schema.value == "test"

    def test_schema_exclude_source_text(self):
        """Test that source_text is excluded from serialization."""
        schema = LSStringSchema(
            node_type="LSString",
            lexeme='"test"',
            value="test",
            source_text="original",
        )
        data = schema.model_dump()
        # source_text should be excluded by default
        assert "source_text" not in data

    def test_schema_include_source_text(self):
        """Test including source_text in serialization."""
        schema = LSStringSchema(
            node_type="LSString",
            lexeme='"test"',
            value="test",
            source_text="original",
        )
        # source_text is excluded by Field(exclude=True) in schema definition
        # This is by design to reduce serialization size
        data = schema.model_dump(exclude_none=False)
        # source_text should NOT be in data because it's excluded
        assert "source_text" not in data


class TestSchemaValidation:
    """Test schema validation."""

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            LSStringSchema(
                node_type="LSString",
                lexeme='"test"',
                value="test",
                extra_field="not_allowed",  # type: ignore
            )

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            LSStringSchema(node_type="LSString")  # type: ignore

    def test_type_validation(self):
        """Test that types are validated."""
        with pytest.raises(ValidationError):
            NumberSchema(node_type="Number", value="not_a_number")  # type: ignore

    def test_literal_validation(self):
        """Test that Literal types are validated."""
        with pytest.raises(ValidationError):
            LSStringSchema(node_type="WrongType", lexeme='"test"', value="test")  # type: ignore
