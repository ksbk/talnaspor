from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from talnaspor.pxweb import get_metadata


def test_get_metadata_returns_validated_model() -> None:
    fake_response = Mock()
    fake_response.text = """
    {
        "title": "Consumer Price Index",
        "variables": [
            {
                "code": "Month",
                "text": "Month",
                "values": ["2026M09"],
                "valueTexts": ["September 2026"]
            }
        ]
    }
    """

    with patch("talnaspor.pxweb.requests.get", return_value=fake_response) as mock_get:
        metadata = get_metadata("https://example.org/table.px")

    assert metadata.title == "Consumer Price Index"
    assert metadata.variables[0].code == "Month"
    assert metadata.variables[0].values == ["2026M09"]

    fake_response.raise_for_status.assert_called_once_with()
    mock_get.assert_called_once_with(
        "https://example.org/table.px",
        timeout=15,
    )


def test_get_metadata_rejects_invalid_structure() -> None:
    fake_response = Mock()
    fake_response.text = '["unexpected", "list"]'

    with (
        patch("talnaspor.pxweb.requests.get", return_value=fake_response),
        pytest.raises(ValidationError),
    ):
        get_metadata("https://example.org/table.px")
