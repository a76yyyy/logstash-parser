# file: peg.py
# Defines the grammar for logstash conf files
# Usage: PEG.config.parse_string(conf_text)

from re import compile

import pyparsing as pp
from pyparsing import common as ppc
from ast_nodes import *

class ParseError(Exception):
    pass

class PEG:
    """

    Parsing expression grammar

    """

    array_start = pp.Suppress(pp.Literal("["))
    array_stop = pp.Suppress(pp.Literal("]"))
    object_start = pp.Suppress(pp.Literal("{"))
    object_stop = pp.Suppress(pp.Literal("}"))
    parenthesis_start = pp.Suppress(pp.Literal("("))
    parenthesis_stop = pp.Suppress(pp.Literal(")"))
    setter = pp.Suppress(pp.Literal("=>"))

    value = pp.Forward().set_name("value")
    rvalue = pp.Forward().set_name("rvalue")
    expression = pp.Forward().set_name("expression")
    branch_or_plugin = pp.Forward().set_name("branch_or_plugin")


    r"""
      True
    """

    true = pp.Keyword("true").set_parse_action(pp.replace_with(True))
    true.set_name("true")

    r"""
      False
    """

    false = pp.Keyword("false").set_parse_action(pp.replace_with(False))
    false.set_name("false")

    r"""
      true / false
    """

    boolean = true | false
    boolean.set_name("boolean")
    boolean.set_parse_action(build_boolean_node)
    
    r"""
      rule whitespace
        [ \t\r\n]+ <LogStash::Config::AST::Whitespace>
      end
    """

    whitespace = pp.White()
    whitespace.set_name("whitespace")

    r"""
      rule comment
        (whitespace? "#" [^\r\n]* "\r"? "\n")+ <LogStash::Config::AST::Comment>
      end
    """
    comment = pp.Regex(compile(r"#.*"))
    comment.set_name("comment")

    r"""
      rule cs
        (comment / whitespace)* <LogStash::Config::AST::Whitespace>
      end
    """

    cs = comment | whitespace
    cs.set_name("cs")

    r"""
      rule single_quoted_string
        ( "'" ( "\\'" / !"'" . )* "'" <LogStash::Config::AST::String>)
      end
    """

    single_quoted_string = pp.QuotedString(quote_char="'", esc_char="\\", unquote_results=False, multiline=True)
    single_quoted_string.set_name("single_quoted_string")

    r"""
      rule double_quoted_string
        ( '"' ( '\"' / !'"' . )* '"' <LogStash::Config::AST::String>)
      end
    """

    double_quoted_string = pp.QuotedString(quote_char='"', esc_char="\\", unquote_results=False, multiline=True)
    double_quoted_string.set_name("double_quoted_string")

    r"""
      rule string
        double_quoted_string / single_quoted_string
      end
    """

    string = double_quoted_string | single_quoted_string
    string.set_name("string")
    string.set_parse_action(build_lsstring)

    r"""
      rule compare_operator 
        ("==" / "!=" / "<=" / ">=" / "<" / ">") 
        <LogStash::Config::AST::ComparisonOperator>
      end
    """

    compare_operator = pp.Literal("==") | pp.Literal("!=") | pp.Literal("<=") | pp.Literal(">=") | pp.Literal("<") | pp.Literal(">")
    compare_operator.set_name("compare_operator")

    r"""
      rule compare_expression
        rvalue cs compare_operator cs rvalue
        <LogStash::Config::AST::ComparisonExpression>
      end
    """

    compare_expression = rvalue + compare_operator + rvalue
    compare_expression.set_name("compare_expression")

    r"""
      rule boolean_operator
        ("and" / "or" / "xor" / "nand")
        <LogStash::Config::AST::BooleanOperator>
      end
    """

    boolean_operator = pp.Literal("and") | pp.Literal("or") | pp.Literal("xor") | pp.Literal("nand")
    boolean_operator.set_name("boolean_operator")

    r"""
      rule regexp
        ( '/' ( '\/' / !'/' . )* '/'  <LogStash::Config::AST::RegExp>)
      end
    """

    regexp = pp.QuotedString(quote_char="/", esc_char=None)
    regexp.set_name("regexp")


    r"""
      rule regexp_operator
        ("=~" / "!~") <LogStash::Config::AST::RegExpOperator>
      end
    """

    regexp_operator = pp.Literal("=~") | pp.Literal("!~")
    regexp_operator.set_name("regexp_operator")

    r"""
      rule regexp_expression
        rvalue cs  regexp_operator cs (string / regexp)
        <LogStash::Config::AST::RegexpExpression>
      end
    """

    regexp_expression = rvalue + regexp_operator + pp.Or([string, regexp])
    regexp_expression.set_name("regexp_expression")

    r"""
      rule in_operator
        "in"
      end
    """

    in_operator = pp.Literal("in")

    r"""
      rule in_expression
        rvalue cs in_operator cs rvalue
        <LogStash::Config::AST::InExpression>
      end
    """

    in_expression = rvalue + in_operator + rvalue
    in_expression.set_name("in_expression")

    r"""
      rule not_in_operator
        "not " cs "in"
      end
    """

    not_in_operator = pp.Literal("not") + pp.Literal("in")

    r"""
      rule not_in_expression
        rvalue cs not_in_operator cs rvalue
        <LogStash::Config::AST::NotInExpression>
      end
    """

    not_in_expression = rvalue + not_in_operator + rvalue
    not_in_expression.set_name("not_in_expression")

    r"""
      rule selector_element
        "[" [^\]\[,]+ "]"
        <LogStash::Config::AST::SelectorElement>
      end
    """
    # [key]
    selector_element = pp.Literal("[") + pp.Regex(compile(r"[^\]\[,]+")) + pp.Literal("]")
    selector_element.set_name("selector_element")

    r"""
      rule selector
        selector_element+
        <LogStash::Config::AST::Selector>
      end
    """
    # [some][logstash][key] => ['[', 'some', ']', '[', 'logstash', ']', '[', 'key', ']'] => ['[some][logstash][key]']
    selector = pp.Combine(pp.OneOrMore(selector_element))
    selector.set_name("selector")
    selector.set_parse_action(build_selector_node)

    r"""
      rule bareword
        [A-Za-z_] [A-Za-z0-9_]+
        <LogStash::Config::AST::Bareword>
      end
    """

    bare_word = pp.Word(pp.alphas + "_", pp.alphanums + "_")
    bare_word.set_name("bare_word")
    bare_word.set_parse_action(build_lsbw)

    r"""
      rule method
        bareword
      end
    """
    method = pp.Word(pp.alphas + "_", pp.alphanums + "_")
    method.set_name("method")

    r"""
      rule number
        "-"? [0-9]+ ("." [0-9]*)?
        <LogStash::Config::AST::Number>
      end
    """

    number = ppc.number
    number.set_parse_action(build_number)

    r"""
      rule plugin_type
        ("input" / "filter" / "output")
      end
    """

    plugin_type = pp.Literal("input") | pp.Literal("filter") | pp.Literal("output")
    plugin_type.set_name("plugin_type")

    r"""
      rule name
        (
          ([A-Za-z0-9_-]+ <LogStash::Config::AST::Name>)
          / string
        )
      end
    """

    name = ( pp.Word(pp.alphanums + "_-") .set_parse_action(build_lsbw) | string )
    name.set_name("name")

    r"""
      rule attribute
        name cs "=>" cs value
        <LogStash::Config::AST::Attribute>
      end
    """

    attribute = pp.Group(name + setter + pp.Group(value))
    attribute.set_name("attribute")
    attribute.set_parse_action(build_attribute_node)

    r"""
      rule plugin
        name cs "{"
          cs
          attributes:( attribute (whitespace cs attribute)*)?
          cs
        "}"
        <LogStash::Config::AST::Plugin>
      end
    """

    plugin = pp.Group(name + pp.Group(object_start + pp.ZeroOrMore(attribute) + object_stop))
    plugin.set_name("plugin")
    plugin.set_parse_action(build_plugin_node)

    """
      rule array_value
        bareword / string / number / array / hash
      end
    """

    # DEFINED IN TREETOP BUT NOT USED

    """
      rule plugins
        (plugin (cs plugin)*)?
        <LogStash::Config::AST::Plugins>
      end
    """

    # DEFINED IN TREETOP BUT NOT USED

    r"""
      rule array
        "["
        cs
        (
          value (_ "," _ value)*
        )?
        _
        "]"
        <LogStash::Config::AST::Array>
      end
    """
    # [abc, def, ghi]
    array = pp.Group(array_start + pp.DelimitedList(pp.ZeroOrMore(value)).set_name("array_values") + array_stop)
    array.set_name("array")
    array.set_parse_action(build_array_node)

    r"""
      rule hashentry
        name:(number / bareword / string) cs "=>" cs value
        <LogStash::Config::AST::HashEntry>
      end
    """

    hash_entry = pp.Group((number | bare_word | string) + setter + pp.Group(value))
    hash_entry.set_name("hash_entry")
    hash_entry.set_parse_action(build_hash_entry_node)

    r"""
      rule hash
        "{"
          cs
          hashentries?
          cs
        "}"
        <LogStash::Config::AST::Hash>
      end

      https://www.elastic.co/guide/en/logstash/current/configuration-file-structure.html#hash
    """

    hashmap = object_start + pp.Group(pp.ZeroOrMore(hash_entry)) + object_stop
    hashmap.set_name("hashmap")
    hashmap.set_parse_action(build_hash_node)

    r"""
      rule method_call
          method cs "(" cs
            (
              rvalue ( cs "," cs rvalue )*
            )?
          cs ")"
        <LogStash::Config::AST::MethodCall>
      end
    """

    method_call = method + pp.Group(parenthesis_start + pp.DelimitedList(pp.ZeroOrMore(rvalue)) + parenthesis_stop)
    method_call.set_name("method_call")

    r"""
      rule plugin_section
        plugin_type cs "{"
          cs (branch_or_plugin cs)*
        "}"
        <LogStash::Config::AST::PluginSection>
      end
    """

    plugin_section = pp.Group(plugin_type + object_start + pp.Group(pp.ZeroOrMore(branch_or_plugin)) + object_stop)
    plugin_section.set_name("plugin_selection")

    r"""
      rule condition
        expression (cs boolean_operator cs expression)*
        <LogStash::Config::AST::Condition>
      end
    """

    condition = expression + pp.ZeroOrMore(boolean_operator + expression)
    condition.set_name("condition")

    r"""
      rule if
        "if" cs condition cs "{" cs (branch_or_plugin cs)* "}"
        <LogStash::Config::AST::If>
      end
    """

    if_rule = pp.Group(pp.Keyword("if") + pp.Group(condition + pp.Group(object_start + pp.Group(pp.ZeroOrMore(branch_or_plugin)) + object_stop)))
    if_rule.set_name("if")
    if_rule.set_parse_action(build_if_condition_node)

    r"""
      rule else_if
        "else" cs "if" cs condition cs "{" cs ( branch_or_plugin cs)* "}"
        <LogStash::Config::AST::Elsif>
      end
    """
    # "else    \n #comment\n  if" as one string "else if"

    else_if_rule = pp.Group(pp.Combine(pp.Keyword("else") + pp.ZeroOrMore(cs).set_parse_action(pp.replace_with(" ")) + pp.Keyword("if")) + pp.Group(
        condition + pp.Group(object_start + pp.Group(pp.ZeroOrMore(branch_or_plugin)) + object_stop)))
    else_if_rule.set_name("else_if")
    else_if_rule.set_parse_action(build_condition_else_if_node)

    r"""
      rule else
        "else" cs "{" cs (branch_or_plugin cs)* "}"
        <LogStash::Config::AST::Else>
      end
    """

    else_rule = pp.Group(pp.Keyword("else") + pp.Group(object_start + pp.ZeroOrMore(branch_or_plugin) + object_stop))
    else_rule.set_name("else")
    else_rule.set_parse_action(build_condition_else_node)

    r"""
      rule branch
        if (cs else_if)* (cs else)?
        <LogStash::Config::AST::Branch>
      end
    """

    branch = if_rule + pp.ZeroOrMore(else_if_rule) + pp.Optional(else_rule)
    branch.set_name("branch")
    branch.set_parse_action(build_branch_node)

    r"""
      rule negative_expression
        (
            ("!" cs "(" cs condition cs ")")
          / ("!" cs selector)
        ) <LogStash::Config::AST::NegativeExpression>
      end
    """

    negative_expression = (pp.Literal("!") + parenthesis_start + condition + parenthesis_stop) | (pp.Literal("!") + selector)
    negative_expression.set_name("negative_expression")

    r"""
      rule expression
        (
            ("(" cs condition cs ")")
          / negative_expression
          / in_expression
          / not_in_expression
          / compare_expression
          / regexp_expression
          / rvalue
        ) <LogStash::Config::AST::Expression>
      end
    """

    expression << pp.Group(
        (parenthesis_start + condition + parenthesis_stop) |
        negative_expression |
        in_expression |
        not_in_expression |
        compare_expression |
        regexp_expression |
        rvalue
    )

    r"""
      rule value
        plugin / bareword / string / number / array / hash
      end
    """
    # in addition: IP support, Boolean

    value << (plugin | boolean | bare_word | string | number | array | hashmap )

    r"""
      rule rvalue
        string / number / selector / array / method_call / regexp
      end
    """
    # in addition: IP support

    rvalue << ( string | number | selector | array | method_call | regexp)

    r"""
      rule branch_or_plugin
        branch / plugin
      end
    """

    branch_or_plugin << (branch | plugin)

    """
      rule config
        cs plugin_section cs (cs plugin_section)* cs <LogStash::Config::AST::Config>
      end
    """

    config = pp.ZeroOrMore(plugin_section)
    config.ignore(comment)
    config.set_name("config")

# Assign the parse actions to the grammar rules
# PEG.method_call.set_parse_action(build_method_call_node)
PEG.config.set_parse_action(build_config_node)
PEG.compare_expression.set_parse_action(lambda t: CompareExpression(t[0], t[1], t[2]))
PEG.in_expression.set_parse_action(lambda t: InExpression(t[0], t[1], t[2]))
PEG.not_in_expression.set_parse_action(lambda t: NotInExpression(t[0], 'not in', t[3]))
PEG.negative_expression.set_parse_action(lambda t: build_negative_expression(t))
PEG.expression.set_parse_action(lambda t: Expression(t[0]))
PEG.rvalue.set_parse_action(lambda t: RValue(t[0]))
PEG.condition.set_parse_action(build_condition_node)
PEG.plugin_section.set_parse_action(plugin_section_parse_action)
