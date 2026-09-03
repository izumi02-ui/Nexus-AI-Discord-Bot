"""
Project Nexus

Calculator Tool

Language models are not reliable at arithmetic. Any numeric question Nexus is
asked should be answered from this tool's output, not from the model's
mental math, which is why it is registered before the model is consulted.

Uses a restricted AST walk - no eval(), no attribute access, no names outside
the whitelist - so a prompt-injected expression cannot execute anything.
"""

from typing import List

from search.search_result import SearchResult
from tools.base import BaseTool

from utils.calculator import (  # noqa: F401 - re-exported for callers
    CalculationError,
    SAFE_CONSTANTS,
    SAFE_FUNCTIONS,
    evaluate,
    extract_expression,
    is_numeric,
)


class CalculatorTool(BaseTool):

    keywords = (
        "calculate", "compute", "what is", "solve", "sqrt", "percentage",
        "percent", "plus", "minus", "times", "divided",
    )

    searchable = False
    ttl = None

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def priority(self) -> int:
        return 100

    @property
    def description(self) -> str:
        return "Exact arithmetic (never trust the model's mental math)"

    @property
    def available(self) -> bool:
        return True

    async def execute(self, query: str) -> List[SearchResult]:
        expression = extract_expression(str(query))

        if not expression:
            return []

        try:
            value = evaluate(expression)
        except CalculationError as error:
            result = SearchResult(
                title=f"Calculation: {expression}",
                content=f"Could not evaluate “{expression}”: {error}.",
                source="Calculator",
                confidence=1.0,
                success=True,
                error=str(error),
                metadata={"expression": expression},
            )

            result.stamp(tool=self.name)

            return [result]

        if isinstance(value, float):
            rendered = (
                f"{value:.12g}"
            )
        else:
            rendered = str(value)

        result = SearchResult(
            title=f"{expression} = {rendered}",
            content=(
                f"Expression: {expression}\n"
                f"Exact result: {rendered}\n"
                "(Computed by the Nexus calculator; safe to quote verbatim.)"
            ),
            source="Calculator",
            confidence=1.0,
            category="math",
            metadata={"expression": expression, "value": value},
        )

        result.stamp(tool=self.name)

        return [result]


calculator = CalculatorTool()
