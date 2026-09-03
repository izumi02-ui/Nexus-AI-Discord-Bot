"""
Calculator safety: the model must never do arithmetic in its head.

Two properties matter and both are cheap to test: every expression the bot
advertises must evaluate exactly (a wrong sum in a "verified" answer is worse
than a refusal), and nothing may escape the sandbox (the input arrives from a
 Discord message, i.e. from an attacker).
"""

import pytest

from utils.calculator import (
    CalculationError,
    evaluate,
    extract_expression,
    is_numeric,
    normalize_percents,
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2+2", 4),
        ("17*23", 391),
        ("10/4", 2.5),
        ("2^10", 1024),
        ("sqrt(144)+1", 13),
        ("(3+4)*2", 14),
        ("2**8", 256),
    ],
)
def test_arithmetic(expression, expected):
    assert abs(float(evaluate(expression)) - expected) < 1e-9


def test_thousands_separators_are_tolerated():
    assert abs(evaluate("1,234.5*2") - 2469.0) < 1e-6


def test_percent_wording_is_understood():
    assert abs(evaluate(extract_expression("what is 15% of 240?")) - 36.0) < 1e-9
    assert abs(evaluate(normalize_percents("12% of 480")) - 57.6) < 1e-9


@pytest.mark.parametrize(
    "text",
    [
        "__import__('os').system('rm -rf /')",
        "open('/etc/passwd').read()",
        "1/0",
        "2**5000",
        "import os",
        "lambda: 1",
        "[x for x in range(10)]",
        "eval('1+1')",
    ],
)
def test_dangerous_or_silly_input_is_refused(text):
    with pytest.raises(CalculationError):
        evaluate(text)


def test_expression_extraction_from_prose():
    assert extract_expression("calculate 1000*365") == "1000*365"
    assert extract_expression("what is the capital of india") is None


def test_arithmetic_inside_prose_is_still_detected():
    # "what is 17*23" must be computed, not answered from the model's memory,
    # so the detector is deliberately tolerant of surrounding words.
    assert is_numeric("17*23") is True
    assert is_numeric("what is 17*23") is True
    assert is_numeric("what is the capital of india") is False


def test_float_output_is_stable():
    assert str(evaluate("1/3")).startswith("0.3333")
