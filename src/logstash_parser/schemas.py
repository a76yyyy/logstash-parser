"""Pydantic schemas for Logstash AST nodes.

This module defines Pydantic models that mirror the AST node structure,
enabling JSON serialization/deserialization and data validation.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class ASTNodeSchema(BaseModel):
    """Base schema for all AST nodes."""

    node_type: Any = Field(..., description="Type of the AST node")
    source_text: str | None = Field(None, exclude=True, description="Original source text (not serialized)")

    model_config = {"extra": "forbid"}


# ============================================================================
# Simple Types
# ============================================================================


class LSStringSchema(ASTNodeSchema):
    """Schema for LSString node."""

    node_type: Literal["LSString"] = "LSString"
    lexeme: str = Field(..., description="Raw string with quotes")
    value: str = Field(..., description="Parsed string value")


class LSBareWordSchema(ASTNodeSchema):
    """Schema for LSBareWord node."""

    node_type: Literal["LSBareWord"] = "LSBareWord"
    value: str = Field(..., description="Bare word value")


class NumberSchema(ASTNodeSchema):
    """Schema for Number node."""

    node_type: Literal["Number"] = "Number"
    value: int | float = Field(..., description="Numeric value")


class BooleanSchema(ASTNodeSchema):
    """Schema for Boolean node."""

    node_type: Literal["Boolean"] = "Boolean"
    value: bool = Field(..., description="Boolean value")


class RegexpSchema(ASTNodeSchema):
    """Schema for Regexp node."""

    node_type: Literal["Regexp"] = "Regexp"
    lexeme: str = Field(..., description="Raw regexp pattern")
    value: str = Field(..., description="Parsed regexp value")


class SelectorNodeSchema(ASTNodeSchema):
    """Schema for SelectorNode."""

    node_type: Literal["SelectorNode"] = "SelectorNode"
    raw: str = Field(..., description="Raw selector string like [foo][bar]")


# ============================================================================
# Data Structures
# ============================================================================


class HashEntryNodeSchema(ASTNodeSchema):
    """Schema for HashEntryNode."""

    node_type: Literal["HashEntry"] = "HashEntry"
    key: "LSStringSchema | LSBareWordSchema | NumberSchema" = Field(..., description="Hash key")
    value: "ValueSchema" = Field(..., description="Hash value")


class HashSchema(ASTNodeSchema):
    """Schema for Hash node."""

    node_type: Literal["Hash"] = "Hash"
    children: list[HashEntryNodeSchema] = Field(default_factory=list, description="Hash entries")


class ArraySchema(ASTNodeSchema):
    """Schema for Array node."""

    node_type: Literal["Array"] = "Array"
    children: list["ValueSchema"] = Field(default_factory=list, description="Array elements")


class AttributeSchema(ASTNodeSchema):
    """Schema for Attribute node."""

    node_type: Literal["Attribute"] = "Attribute"
    name: LSStringSchema | LSBareWordSchema = Field(..., description="Attribute name")
    value: "ValueSchema" = Field(..., description="Attribute value")


# ============================================================================
# Plugin
# ============================================================================


class PluginSchema(ASTNodeSchema):
    """Schema for Plugin node."""

    node_type: Literal["Plugin"] = "Plugin"
    plugin_name: str = Field(..., description="Plugin name")
    attributes: list[AttributeSchema] = Field(default_factory=list, description="Plugin attributes")


# ============================================================================
# Expressions
# ============================================================================


class CompareExpressionSchema(ASTNodeSchema):
    """Schema for CompareExpression node."""

    node_type: Literal["CompareExpression"] = "CompareExpression"
    left: "ValueSchema" = Field(..., description="Left operand")
    operator: str = Field(..., description="Comparison operator")
    right: "ValueSchema" = Field(..., description="Right operand")


class RegexExpressionSchema(ASTNodeSchema):
    """Schema for RegexExpression node."""

    node_type: Literal["RegexExpression"] = "RegexExpression"
    left: "ValueSchema" = Field(..., description="Left operand")
    operator: str = Field(..., description="Regex operator")
    pattern: "ValueSchema" = Field(..., description="Regex pattern")


class InExpressionSchema(ASTNodeSchema):
    """Schema for InExpression node."""

    node_type: Literal["InExpression"] = "InExpression"
    value: "ValueSchema" = Field(..., description="Value to check")
    operator: str = Field("in", description="In operator")
    collection: "ValueSchema" = Field(..., description="Collection to check in")


class NotInExpressionSchema(ASTNodeSchema):
    """Schema for NotInExpression node."""

    node_type: Literal["NotInExpression"] = "NotInExpression"
    value: "ValueSchema" = Field(..., description="Value to check")
    operator: str = Field("not in", description="Not in operator")
    collection: "ValueSchema" = Field(..., description="Collection to check in")


class NegativeExpressionSchema(ASTNodeSchema):
    """Schema for NegativeExpression node."""

    node_type: Literal["NegativeExpression"] = "NegativeExpression"
    operator: str = Field(..., description="Negation operator")
    expression: "ValueSchema" = Field(..., description="Expression to negate")


class BooleanExpressionSchema(ASTNodeSchema):
    """Schema for BooleanExpression node."""

    node_type: Literal["BooleanExpression"] = "BooleanExpression"
    left: "ValueSchema" = Field(..., description="Left operand")
    operator: str = Field(..., description="Boolean operator (and/or/xor/nand)")
    right: "ValueSchema" = Field(..., description="Right operand")


class ExpressionSchema(ASTNodeSchema):
    """Schema for Expression node (wrapper)."""

    node_type: Literal["Expression"] = "Expression"
    condition: "ValueSchema" = Field(..., description="Wrapped condition")


# ============================================================================
# Conditional Branches
# ============================================================================


class IfConditionSchema(ASTNodeSchema):
    """Schema for IfCondition node."""

    node_type: Literal["IfCondition"] = "IfCondition"
    expr: "ExpressionValueSchema" = Field(..., description="Condition expression")
    body: list["BranchOrPluginSchema"] = Field(default_factory=list, description="Body of if block")


class ElseIfConditionSchema(ASTNodeSchema):
    """Schema for ElseIfCondition node."""

    node_type: Literal["ElseIfCondition"] = "ElseIfCondition"
    expr: "ExpressionValueSchema" = Field(..., description="Condition expression")
    body: list["BranchOrPluginSchema"] = Field(default_factory=list, description="Body of else if block")


class ElseConditionSchema(ASTNodeSchema):
    """Schema for ElseCondition node."""

    node_type: Literal["ElseCondition"] = "ElseCondition"
    body: list["BranchOrPluginSchema"] = Field(default_factory=list, description="Body of else block")


class BranchSchema(ASTNodeSchema):
    """Schema for Branch node."""

    node_type: Literal["Branch"] = "Branch"
    children: list[IfConditionSchema | ElseIfConditionSchema | ElseConditionSchema] = Field(
        default_factory=list, description="Branch conditions"
    )


# ============================================================================
# Configuration
# ============================================================================


class PluginSectionNodeSchema(ASTNodeSchema):
    """Schema for PluginSectionNode."""

    node_type: Literal["PluginSection"] = "PluginSection"
    plugin_type: str = Field(..., description="Section type (input/filter/output)")
    children: list["BranchOrPluginSchema"] = Field(default_factory=list, description="Plugins or branches in section")


class ConfigSchema(ASTNodeSchema):
    """Schema for Config node (root)."""

    node_type: Literal["Config"] = "Config"
    children: list[PluginSectionNodeSchema] = Field(default_factory=list, description="Plugin sections")


# ============================================================================
# Union Types
# ============================================================================

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
    | BooleanExpressionSchema
    | ExpressionSchema,
    Field(discriminator="node_type"),
]

# ExpressionValueSchema: All possible expression types
ExpressionValueSchema = Annotated[
    CompareExpressionSchema
    | RegexExpressionSchema
    | InExpressionSchema
    | NotInExpressionSchema
    | NegativeExpressionSchema
    | BooleanExpressionSchema
    | ExpressionSchema,
    Field(discriminator="node_type"),
]

# BranchOrPluginSchema: Branch or Plugin
BranchOrPluginSchema = Annotated[
    BranchSchema | PluginSchema,
    Field(discriminator="node_type"),
]


# ============================================================================
# Rebuild models to resolve forward references
# ============================================================================

HashEntryNodeSchema.model_rebuild()
HashSchema.model_rebuild()
ArraySchema.model_rebuild()
AttributeSchema.model_rebuild()
PluginSchema.model_rebuild()
CompareExpressionSchema.model_rebuild()
RegexExpressionSchema.model_rebuild()
InExpressionSchema.model_rebuild()
NotInExpressionSchema.model_rebuild()
NegativeExpressionSchema.model_rebuild()
BooleanExpressionSchema.model_rebuild()
ExpressionSchema.model_rebuild()
IfConditionSchema.model_rebuild()
ElseIfConditionSchema.model_rebuild()
ElseConditionSchema.model_rebuild()
BranchSchema.model_rebuild()
PluginSectionNodeSchema.model_rebuild()
ConfigSchema.model_rebuild()
