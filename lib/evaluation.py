from re import search
from sys import exit
import lib.globals as g


def prepareToken(token: str, first_column: bool, row_duration: int) -> str:
    if token[:2] == "//" or token[:2] == '"//':  # ignore comment
        return ""
    return evaluateMath(evaluateVariables(token, row_duration), first_column)


def evaluateVariables(
    token: str, row_duration: int
) -> str:  # evaluates all variables of form $ or #
    while match_obj := search("\\$\\w+", token):  # replace variables with their values
        name = match_obj.group().lower()[1:]
        value = g.vars.get(name)
        if value is None:
            exit("[evaluateVariables] Variable " + match_obj.group() + " not found")
        token = token.replace(match_obj.group(), value)

    token = token.replace("#", str(row_duration))

    return token.lower()


def evaluateMath(token: str, whole_token: bool) -> str:  # evaluates math expressions
    while match_obj := search(
        "\\/[ \\(]*\\.?[0-9]", token
    ):  # replace division / with ÷ to differentiate from loops
        token = token.replace(match_obj.group(), match_obj.group().replace("/", "÷"))
    if whole_token:  # match math expressions that take up the whole token
        math_regex = "^(([0-9,\\. \\+\\-\\*÷\\(\\)])+([\\+\\-\\*÷])([0-9,\\. \\+\\-\\*÷\\(\\)])+)$"
        group = 1
    else:  # match math expressions that begin/end with parentheses, commas, brackets, or semicolons
        math_regex = "([\\(\\,\\;\\[])(([0-9,\\. \\+\\-\\*÷\\(\\)])+([\\+\\-\\*÷])([0-9,\\. \\+\\-\\*÷\\(\\)])+)([\\)\\,\\;\\]])"
        group = 2
    try:
        # evaluate math operations
        while match_obj := search(math_regex, token):
            # replace the math expression with its evaluation, first replacing ÷ with / so Python can evaluate the division
            token = token.replace(
                match_obj.group(group),
                str(eval(match_obj.group(group).replace("÷", "/"))),
            )
    except:
        pass  # handles bad match groups with parentheses

    return token.lower()


def evaluateLast(
    token: str, prev: float
):  # replaces any ! marks with prev, then calls evaluateMath
    token = token.replace("!", str(prev))
    return evaluateMath(token, True)


def evaluateCurrentFrame(
    token: str, offset: int
):  # replaces any @ marks with offset, then calls evaluateMath
    token = token.replace("@", str(offset))
    return evaluateMath(token, True)
