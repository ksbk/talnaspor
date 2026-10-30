import pytest

from talnaspor.validation import validate_value


def test_accepts_valid_month() -> None:
    allowed = ["2026M08", "2026M09", "2026M10"]

    result = validate_value("2026M09", allowed)

    assert result == "2026M09"


def test_rejects_invalid_month() -> None:
    allowed = ["2026M08", "2026M09", "2026M10"]

    with pytest.raises(ValueError, match="Unsupported value"):
        validate_value("2027M01", allowed)


def test_rejects_invalid_measurement() -> None:
    allowed = ["index", "change_M", "change_A"]

    with pytest.raises(ValueError, match="Unsupported value"):
        validate_value("inflation_rate", allowed)
