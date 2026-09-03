"""
Project Nexus

Safe arithmetic

Exact math for a bot that must not guess numbers. No eval(): a restricted AST
walk over a whitelist of operators, functions and constants, so a
prompt-injected "expression" can only ever do arithmetic.

Lives in utils (rather than only in the tool) because the router has to know
whether a message *is* a calculation before any tool is called.
"""

import ast
import math
import operator
import re

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "sqrt": math.sqrt,
    "cbrt": lambda value: math.copysign(abs(value) ** (1 / 3), value),
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "ln": math.log,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "degrees": math.degrees,
    "radians": math.radians,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "hypot": math.hypot,
    "perm": math.perm,
    "comb": math.comb,
    "pow": pow,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "tau": math.tau,
    "e": math.e,
    "inf": math.inf,
}

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

MAX_POW_DIGITS = 16

EXPRESSION_RE = re.compile(
    r"[-+*/^%().\d]|sqrt|cbrt|log10|log2|log|ln|exp|sin|cos|tan|asin|acos|"
    r"atan2|atan|degrees|radians|floor|ceil|factorial|gcd|hypot|perm|comb|"
    r"abs|round|min|max|sum|pow|pi|tau|\be\b",
)


class CalculationError(ValueError):
    """Raised when the expression cannot be evaluated safely."""


def evaluate(expression: str):
    """Evaluate an arithmetic expression without eval()."""
    if not expression or len(expression) > 2000:
        raise CalculationError("expression missing or too long")

    normalized = (
        expression.replace("×", "*")
        .replace("÷", "/")
        .replace("^", "**")
        .replace("−", "-")
        .replace(",", "")
    )

    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as error:
        raise CalculationError(f"could not parse: {error.msg}") from error

    return _eval_node(tree.body)


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        value = node.value

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CalculationError("only numbers are allowed")

        return value

    if isinstance(node, ast.BinOp):
        handler = OPERATORS.get(type(node.op))

        if handler is None:
            raise CalculationError(f"operator {type(node.op).__name__} not allowed")

        left = _eval_node(node.left)
        right = _eval_node(node.right)

        if isinstance(node.op, ast.Pow):
            if abs(right) > MAX_POW_DIGITS or (
                isinstance(left, float) and abs(left) > 1e8 and right > 4
            ):
                raise CalculationError("exponent too large")

        try:
            return handler(left, right)
        except ZeroDivisionError as error:
            raise CalculationError("division by zero") from error
        except (OverflowError, ValueError) as error:
            raise CalculationError(f"out of range ({error})") from error

    if isinstance(node, ast.UnaryOp):
        handler = OPERATORS.get(type(node.op))

        if handler is None:
            raise CalculationError("unary operator not allowed")

        return handler(_eval_node(node.operand))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise CalculationError("only named math functions are allowed")

        function = SAFE_FUNCTIONS.get(node.func.id)

        if function is None:
            raise CalculationError(f"function {node.func.id!r} is not available")

        if node.keywords:
            raise CalculationError("keyword arguments are not allowed")

        return function(*[_eval_node(arg) for arg in node.args])

    if isinstance(node, ast.Name):
        if node.id in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id]

        raise CalculationError(f"unknown name {node.id!r}")

    raise CalculationError(f"{type(node).__name__} is not allowed")


def normalize_percents(text: str) -> str:
    """Rewrite '12% of 480' / '15 percent' into arithmetic a parser accepts."""
    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?)\s*of\s*(\d+(?:\.\d+)?)",
        r"(\1/100)*\2",
        text,
        flags=re.IGNORECASE,
    )

    return re.sub(
        r"(\d+(?:\.\d+)?)\s*(?:%|percent)",
        r"(\1/100)",
        text,
        flags=re.IGNORECASE,
    )


def extract_expression(text: str) -> str | None:
    """Pull the arithmetic out of a sentence like 'what is 17*23 + 4?'."""
    if not text:
        return None

    text = normalize_percents(text)

    candidate = re.sub(r"^(?:calculate|compute|solve|what(?:'?s| is)|how much is)\b",
                       "", text.strip(), flags=re.IGNORECASE)
    candidate = re.sub(r"[?=]$", "", candidate.strip()).strip()

    if re.fullmatch(r"[-+*/^%().\d\s,e]+", candidate) and any(
        char.isdigit() for char in candidate
    ):
        return candidate

    # Longest run of math-ish characters inside a sentence.
    best = None

    for match in re.finditer(
        r"[-+*/^%().\d]+(?:\s*(?:sqrt|cbrt|log10|log2|log|ln|sin|cos|tan|"
        r"factorial|abs|min|max|pow)\s*\([-+\d.,*/^ ]+\)|\^[ -]*\d+)?",
        candidate,
    ):
        chunk = match.group(0).strip()

        if len(chunk) >= 3 and any(char.isdigit() for char in chunk):
            if best is None or len(chunk) > len(best):
                best = chunk

    return best


def is_numeric(text: str) -> bool:
    """Does this message mostly contain a calculation?"""
    expression = extract_expression(text)

    if not expression:
        return False

    digits = sum(character.isdigit() for character in expression)
    operators = sum(
        character in "+-*/^%" for character in expression
    )

    return digits >= 2 and operators >= 1


