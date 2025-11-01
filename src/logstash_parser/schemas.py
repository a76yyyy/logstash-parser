"""Pydantic schemas for Logstash AST nodes.

This module defines Pydantic models that mirror the AST node structure,
enabling JSON serialization/deserialization and data validation.

Uses snake_case keys as type discriminators (e.g., {"ls_string": {...}})
instead of node_type field for more concise representation.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

# ============================================================================
# Simple Type Schemas (using snake_case field names)
# ============================================================================


class ASTNodeSchema(BaseModel):
    pass


class LSStringSchema(ASTNodeSchema):
    """Schema for LSString node."""

    ls_string: str = Field(..., description="Raw string with quotes (lexeme)")

    model_config = {"extra": "forbid"}


class LSBareWordSchema(ASTNodeSchema):
    """Schema for LSBareWord node."""

    ls_bare_word: str = Field(..., description="Bare word value")

    model_config = {"extra": "forbid"}


class NumberSchema(ASTNodeSchema):
    """Schema for Number node."""

    number: int | float = Field(..., description="Numeric value")

    model_config = {"extra": "forbid"}


class BooleanSchema(ASTNodeSchema):
    """Schema for Boolean node."""

    boolean: bool = Field(..., description="Boolean value")

    model_config = {"extra": "forbid"}


class RegexpSchema(ASTNodeSchema):
    """Schema for Regexp node."""

    regexp: str = Field(..., description="Raw regexp pattern (lexeme)")

    model_config = {"extra": "forbid"}


class SelectorNodeSchema(ASTNodeSchema):
    """Schema for SelectorNode."""

    selector_node: str = Field(..., description="Raw selector string like [foo][bar]")

    model_config = {"extra": "forbid"}


# ============================================================================
# Data Structures
# ============================================================================


class HashSchema(ASTNodeSchema):
    """Schema for Hash node.

    Hash is represented as a dict where keys are serialized key values
    and values are the corresponding value schemas.
    """

    hash: dict[str, "ValueSchema"] = Field(default_factory=dict, description="Hash entries as key-value pairs")

    model_config = {"extra": "forbid"}


class ArraySchema(ASTNodeSchema):
    """Schema for Array node."""

    array: list[
        "PluginSchema | BooleanSchema | LSBareWordSchema | LSStringSchema | NumberSchema | ArraySchema | HashSchema"
    ] = Field(default_factory=list, description="Array elements")

    model_config = {"extra": "forbid"}


class AttributeSchema(ASTNodeSchema, RootModel[dict[str, "ValueSchema"]]):
    """Schema for Attribute node.

    Attribute is represented as a dict where the key is the serialized attribute name
    and the value is the corresponding value schema.

    Uses RootModel to serialize directly as a dict without wrapper field.
    """

    root: dict[str, "ValueSchema"]


# ============================================================================
# Plugin
# ============================================================================


class PluginData(BaseModel):
    """Data for Plugin node."""

    plugin_name: str = Field(..., description="Plugin name")
    attributes: list[AttributeSchema] = Field(default_factory=list, description="Plugin attributes")

    model_config = {"extra": "forbid"}


class PluginSchema(ASTNodeSchema):
    """Schema for Plugin node."""

    plugin: PluginData

    model_config = {"extra": "forbid"}


# ============================================================================
# Expressions
# ============================================================================


class CompareExpressionData(BaseModel):
    """Data for CompareExpression node."""

    left: "ValueSchema" = Field(..., description="Left operand")
    operator: str = Field(..., description="Comparison operator")
    right: "ValueSchema" = Field(..., description="Right operand")

    model_config = {"extra": "forbid"}


class CompareExpressionSchema(ASTNodeSchema):
    """Schema for CompareExpression node."""

    compare_expression: CompareExpressionData

    model_config = {"extra": "forbid"}


class RegexExpressionData(BaseModel):
    """Data for RegexExpression node."""

    left: "ValueSchema" = Field(..., description="Left operand")
    operator: str = Field(..., description="Regex operator")
    pattern: "ValueSchema" = Field(..., description="Regex pattern")

    model_config = {"extra": "forbid"}


class RegexExpressionSchema(ASTNodeSchema):
    """Schema for RegexExpression node."""

    regex_expression: RegexExpressionData

    model_config = {"extra": "forbid"}


class InExpressionData(BaseModel):
    """Data for InExpression node."""

    value: "ValueSchema" = Field(..., description="Value to check")
    operator: str = Field("in", description="In operator")
    collection: "ValueSchema" = Field(..., description="Collection to check in")

    model_config = {"extra": "forbid"}


class InExpressionSchema(ASTNodeSchema):
    """Schema for InExpression node."""

    in_expression: InExpressionData

    model_config = {"extra": "forbid"}


class NotInExpressionData(BaseModel):
    """Data for NotInExpression node."""

    value: "ValueSchema" = Field(..., description="Value to check")
    operator: str = Field("not in", description="Not in operator")
    collection: "ValueSchema" = Field(..., description="Collection to check in")

    model_config = {"extra": "forbid"}


class NotInExpressionSchema(ASTNodeSchema):
    """Schema for NotInExpression node."""

    not_in_expression: NotInExpressionData

    model_config = {"extra": "forbid"}


class NegativeExpressionData(BaseModel):
    """Data for NegativeExpression node."""

    operator: str = Field(..., description="Negation operator")
    expression: "ValueSchema" = Field(..., description="Expression to negate")

    model_config = {"extra": "forbid"}


class NegativeExpressionSchema(ASTNodeSchema):
    """Schema for NegativeExpression node."""

    negative_expression: NegativeExpressionData

    model_config = {"extra": "forbid"}


class BooleanExpressionData(BaseModel):
    """Data for BooleanExpression node."""

    left: "ValueSchema" = Field(..., description="Left operand")
    operator: str = Field(..., description="Boolean operator (and/or/xor/nand)")
    right: "ValueSchema" = Field(..., description="Right operand")

    model_config = {"extra": "forbid"}


class BooleanExpressionSchema(ASTNodeSchema):
    """Schema for BooleanExpression node."""

    boolean_expression: BooleanExpressionData

    model_config = {"extra": "forbid"}


# ============================================================================
# Conditional Branches
# ============================================================================


class IfConditionData(BaseModel):
    """Data for IfCondition node."""

    expr: "ExpressionSchema | BooleanExpressionSchema" = Field(..., description="Condition expression")
    body: list["BranchOrPluginSchema"] = Field(default_factory=list, description="Body of if block")

    model_config = {"extra": "forbid"}


class IfConditionSchema(ASTNodeSchema):
    """Schema for IfCondition node."""

    if_condition: IfConditionData

    model_config = {"extra": "forbid"}


class ElseIfConditionData(BaseModel):
    """Data for ElseIfCondition node."""

    expr: "ExpressionSchema | BooleanExpressionSchema" = Field(..., description="Condition expression")
    body: list["BranchOrPluginSchema"] = Field(default_factory=list, description="Body of else if block")

    model_config = {"extra": "forbid"}


class ElseIfConditionSchema(ASTNodeSchema):
    """Schema for ElseIfCondition node."""

    else_if_condition: ElseIfConditionData

    model_config = {"extra": "forbid"}


class ElseConditionSchema(ASTNodeSchema):
    """Schema for ElseCondition node."""

    else_condition: list["BranchOrPluginSchema"] = Field(default_factory=list, description="Body of else block")

    model_config = {"extra": "forbid"}


class BranchSchema(ASTNodeSchema):
    """Schema for Branch node."""

    branch: list["ConditionSchema"] = Field(default_factory=list, description="Branch conditions")

    model_config = {"extra": "forbid"}


# ============================================================================
# Configuration
# ============================================================================


class PluginSectionSchema(ASTNodeSchema):
    """Schema for PluginSection node.

    PluginSection is represented as a dict where the key is the plugin_type
    (input/filter/output) and the value is the list of children.

    Example:
        {"plugin_section": {"filter": [...]}}
    """

    plugin_section: dict[Literal["input", "filter", "output"], list["BranchOrPluginSchema"]] = Field(
        ..., description="Plugin section with type as key and children as value"
    )

    model_config = {"extra": "forbid"}


class ConfigSchema(ASTNodeSchema):
    """Schema for Config node (root)."""

    config: list[PluginSectionSchema] = Field(default_factory=list, description="Plugin sections")

    model_config = {"extra": "forbid"}


# ============================================================================
# Union Types
# ============================================================================

# NameSchema: LSString or LSBareWord (for attribute names)
NameSchema = Annotated[LSStringSchema | LSBareWordSchema, Field(discriminator=None)]

# ValueSchema: All possible value types
ValueSchema = Annotated[
    LSStringSchema
    | LSBareWordSchema
    | NumberSchema
    | BooleanSchema
    | RegexpSchema
    | SelectorNodeSchema
    | HashSchema
    | ArraySchema
    | PluginSchema
    | CompareExpressionSchema
    | RegexExpressionSchema
    | InExpressionSchema
    | NotInExpressionSchema
    | NegativeExpressionSchema
    | BooleanExpressionSchema,
    Field(discriminator=None),
]

# ExpressionSchema: All possible expression types (union type, not a wrapper class)
ExpressionSchema = Annotated[
    CompareExpressionSchema
    | RegexExpressionSchema
    | InExpressionSchema
    | NotInExpressionSchema
    | NegativeExpressionSchema
    | BooleanExpressionSchema
    | SelectorNodeSchema,
    Field(discriminator=None),
]


# ConditionSchema: If/ElseIf/Else conditions
ConditionSchema = Annotated[IfConditionSchema | ElseIfConditionSchema | ElseConditionSchema, Field(discriminator=None)]

# BranchOrPluginSchema: Branch or Plugin
BranchOrPluginSchema = Annotated[BranchSchema | PluginSchema, Field(discriminator=None)]


# ============================================================================
# Rebuild models to resolve forward references
# ============================================================================

PluginData.model_rebuild()
CompareExpressionData.model_rebuild()
RegexExpressionData.model_rebuild()
InExpressionData.model_rebuild()
NotInExpressionData.model_rebuild()
NegativeExpressionData.model_rebuild()
BooleanExpressionData.model_rebuild()
IfConditionData.model_rebuild()
ElseIfConditionData.model_rebuild()
PluginSectionSchema.model_rebuild()
