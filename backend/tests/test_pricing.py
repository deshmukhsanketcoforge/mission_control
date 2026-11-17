"""Cost is calculated in code from token counts and a price table."""

from decimal import Decimal

import pytest

from app.domain.pricing import UnknownModelError, cost_usd, format_usd, total_cost
from app.llm.models import FAST_MODEL, STRONG_MODEL

M = 1_000_000


def test_fast_model_prices_per_million_tokens():
    assert cost_usd(FAST_MODEL, M, 0) == Decimal("0.10")
    assert cost_usd(FAST_MODEL, 0, M) == Decimal("0.50")


def test_strong_model_prices_per_million_tokens():
    assert cost_usd(STRONG_MODEL, M, 0) == Decimal("2.00")
    assert cost_usd(STRONG_MODEL, 0, M) == Decimal("10.00")


def test_input_and_output_are_added():
    # 1000 in * 0.10/M + 500 out * 0.50/M = 0.0001 + 0.00025
    assert cost_usd(FAST_MODEL, 1000, 500) == Decimal("0.00035")


def test_result_is_exact_decimal_not_float():
    result = cost_usd(FAST_MODEL, 3, 0)
    assert isinstance(result, Decimal)
    assert result == Decimal("0.0000003")


def test_zero_tokens_cost_nothing():
    assert cost_usd(FAST_MODEL, 0, 0) == Decimal(0)


def test_unknown_model_is_an_error_not_a_free_call():
    with pytest.raises(UnknownModelError, match="mystery-model"):
        cost_usd("mystery-model", 10, 10)


def test_negative_tokens_are_rejected():
    with pytest.raises(ValueError):
        cost_usd(FAST_MODEL, -1, 0)
    with pytest.raises(ValueError):
        cost_usd(FAST_MODEL, 0, -1)


def test_demo_model_is_free():
    assert cost_usd("demo", 5000, 5000) == Decimal(0)


def test_total_cost_sums_decimals_without_float_error():
    parts = [Decimal("0.1"), Decimal("0.2"), Decimal("0.3")]
    assert total_cost(parts) == Decimal("0.6")
    assert total_cost([]) == Decimal(0)


@pytest.mark.parametrize(
    "value,text",
    [
        (Decimal("0.00035"), "0.00035"),
        (Decimal("0"), "0"),
        (Decimal("0.6000"), "0.6"),
        (Decimal("1E-7"), "0.0000001"),
        (Decimal("2.50"), "2.5"),
    ],
)
def test_format_usd_never_uses_scientific_notation(value, text):
    assert format_usd(value) == text
