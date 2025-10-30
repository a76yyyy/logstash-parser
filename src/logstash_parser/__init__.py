# Defines the grammar for logstash conf files
# Usage: PEG.config.parse_string(conf_text)


from logstash_parser.ast_nodes import (
    build_array_node,
    build_attribute_node,
    build_boolean_node,
    build_branch_node,
    build_compare_expression,
    build_condition_else_if_node,
    build_condition_else_node,
    build_condition_node,
    build_config_node,
    build_expression,
    build_hash_entry_node,
    build_hash_node,
    build_if_condition_node,
    build_in_expression,
    build_lsbw,
    build_lsstring,
    build_name,
    build_negative_expression,
    build_not_in_expression,
    build_number,
    build_plugin_node,
    build_plugin_section_node,
    build_regexp,
    build_regexp_node,
    build_rvalue,
    build_selector_node,
)
from logstash_parser.grammar import (
    array,
    attribute,
    bare_word,
    boolean,
    branch,
    compare_expression,
    condition,
    config,
    else_if_rule,
    else_rule,
    expression,
    hash_entry,
    hashmap,
    if_rule,
    in_expression,
    name,
    negative_expression,
    not_in_expression,
    number,
    plugin,
    plugin_section,
    regexp,
    regexp_expression,
    rvalue,
    selector,
    string,
)


class ParseError(Exception):
    pass


class PEG:
    """

    Parsing expression grammar

    """

    boolean.set_parse_action(build_boolean_node)

    string.set_parse_action(build_lsstring)

    compare_expression.set_parse_action(build_compare_expression)

    regexp.set_parse_action(build_regexp)

    regexp_expression.set_parse_action(build_regexp_node)

    in_expression.set_parse_action(build_in_expression)

    not_in_expression.set_parse_action(build_not_in_expression)

    selector.set_parse_action(build_selector_node)

    bare_word.set_parse_action(build_lsbw)

    number.set_parse_action(build_number)

    name.set_parse_action(build_name)

    attribute.set_parse_action(build_attribute_node)

    plugin.set_parse_action(build_plugin_node)

    array.set_parse_action(build_array_node)

    hash_entry.set_parse_action(build_hash_entry_node)

    hashmap.set_parse_action(build_hash_node)

    plugin_section.set_parse_action(build_plugin_section_node)

    condition.set_parse_action(build_condition_node)

    if_rule.set_parse_action(build_if_condition_node)

    else_if_rule.set_parse_action(build_condition_else_if_node)

    else_rule.set_parse_action(build_condition_else_node)

    branch.set_parse_action(build_branch_node)

    negative_expression.set_parse_action(build_negative_expression)

    expression.set_parse_action(build_expression)

    rvalue.set_parse_action(build_rvalue)

    config.set_parse_action(build_config_node)


# Assign the parse actions to the grammar rules
# TODO: Need to set this parse action for method call
# PEG.method_call.set_parse_action(build_method_call_node)


def parse_logstash_config(config_text: str):
    """
    Parse Logstash configuration text into AST.

    Args:
        config_text: Logstash configuration string

    Returns:
        Config AST node

    Raises:
        ParseError: If parsing fails
    """
    try:
        result = config.parse_string(config_text)
        if not result:
            raise ParseError("Failed to parse configuration: empty result")
        return result[0]
    except Exception as e:
        raise ParseError(f"Failed to parse Logstash configuration: {e}") from e
