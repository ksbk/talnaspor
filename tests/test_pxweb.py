import json
from unittest.mock import Mock, patch

import pytest
import requests
from pydantic import ValidationError

from talnaspor.pxweb import MAX_RETRY_WAIT, PXMetadata, RateLimited, get_data, get_metadata


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


@pytest.mark.parametrize(
    ("variables", "message"),
    [
        ([], "at least one variable"),
        (
            [
                {"code": "Month", "text": "Month", "values": ["2026M09"]},
                {"code": "Month", "text": "Month", "values": ["2026M08"]},
            ],
            "codes must be unique",
        ),
        ([{"code": "Month", "text": "Month", "values": []}], "has no values"),
        (
            [{"code": "Month", "text": "Month", "values": ["2026M09", "2026M09"]}],
            "duplicate values",
        ),
        (
            [
                {
                    "code": "Month",
                    "text": "Month",
                    "values": ["2026M08", "2026M09"],
                    "valueTexts": ["August 2026"],
                }
            ],
            "mismatched value texts",
        ),
    ],
)
def test_metadata_rejects_inconsistent_variables(
    variables: list[dict[str, object]],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        PXMetadata.model_validate({"title": "Consumer Price Index", "variables": variables})


def test_get_data_submits_query() -> None:
    fake_response = Mock()
    fake_response.text = '{"value":[5.9]}'

    query: dict[str, object] = {
        "query": [],
        "response": {"format": "json-stat2"},
    }

    with patch("talnaspor.pxweb.requests.post", return_value=fake_response) as mock_post:
        result = get_data("https://example.org/table.px", query)

    assert result == '{"value":[5.9]}'
    fake_response.raise_for_status.assert_called_once_with()
    mock_post.assert_called_once_with(
        "https://example.org/table.px",
        data=json.dumps(query),
        headers={"Content-Type": "application/json"},
        timeout=20,
    )


def test_get_metadata_propagates_http_error() -> None:
    fake_response = Mock()
    fake_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

    with (
        patch("talnaspor.pxweb.requests.get", return_value=fake_response),
        pytest.raises(requests.HTTPError, match="404"),
    ):
        get_metadata("https://example.org/table.px")


def test_get_data_propagates_http_error() -> None:
    fake_response = Mock()
    fake_response.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")

    with (
        patch("talnaspor.pxweb.requests.post", return_value=fake_response),
        pytest.raises(requests.HTTPError, match="400"),
    ):
        get_data("https://example.org/table.px", {"query": []})


def limited() -> Mock:
    response = Mock(status_code=429, headers={"Retry-After": "10"})
    return response


def test_retries_once_after_a_rate_limit() -> None:
    ok = Mock(status_code=200, text='{"value":[5.9]}')
    with (
        patch("talnaspor.pxweb.requests.post", side_effect=[limited(), ok]) as post,
        patch("talnaspor.pxweb.time.sleep") as sleep,
    ):
        result = get_data("https://example.org/table.px", {"query": []})

    assert result == '{"value":[5.9]}'
    assert post.call_count == 2
    sleep.assert_called_once_with(MAX_RETRY_WAIT)


def test_reports_a_persistent_rate_limit() -> None:
    with (
        patch("talnaspor.pxweb.requests.get", side_effect=[limited(), limited()]),
        patch("talnaspor.pxweb.time.sleep"),
        pytest.raises(RateLimited),
    ):
        get_metadata("https://example.org/table.px")


def test_serves_identical_requests_from_the_cache() -> None:
    ok = Mock(status_code=200, text='{"value":[5.9]}')
    with patch("talnaspor.pxweb.requests.post", return_value=ok) as post:
        get_data("https://example.org/table.px", {"query": []})
        get_data("https://example.org/table.px", {"query": []})
        get_data("https://example.org/table.px", {"query": [{"code": "Ár"}]})

    assert post.call_count == 2
