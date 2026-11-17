"""What each model call costs, calculated in code from token counts.

Prices are US dollars per million tokens, as ``(input, output)``. Money is kept
as ``Decimal`` so sums are exact. A model that is not in the table is an error,
never a free call.
"""

from collections.abc import Iterable
from decimal import Decimal

from app.llm.models import FAST_MODEL, STRONG_MODEL

_MILLION = Decimal(1_000_000)

PRICES_PER_MILLION: dict[str, tuple[Decimal, Decimal]] = {
    # Haiku 5.5 prices apply to prompts up to 100K tokens. Our prompts are far smaller.
    FAST_MODEL: (Decimal("0.10"), Decimal("0.50")),
    STRONG_MODEL: (Decimal("2.00"), Decimal("10.00")),
    # Offline demo client (no API key). It calls no model, so it costs nothing.
    "demo": (Decimal(0), Decimal(0)),
}


class UnknownModelError(KeyError):
    """The model has no entry in the price table."""

    def __str__(self) -> str:
        return f"No price known for model {self.args[0]!r}"


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts cannot be negative")
    try:
        price_in, price_out = PRICES_PER_MILLION[model]
    except KeyError:
        raise UnknownModelError(model) from None
    return (price_in * input_tokens + price_out * output_tokens) / _MILLION


def total_cost(costs: Iterable[Decimal]) -> Decimal:
    return sum(costs, Decimal(0))


def format_usd(value: Decimal) -> str:
    """Plain decimal text, never scientific notation, without trailing zeros."""
    return format(value.normalize(), "f")
