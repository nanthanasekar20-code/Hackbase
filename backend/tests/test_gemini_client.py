"""
Tests for app.rag.gemini_client.generate_json's retry/fail-fast behavior.

model.generate_content is mocked (no real network call), so these can't
exercise Google's actual retry machinery end-to-end — but they do verify
the two things that matter: (1) a retryable error is wrapped into a clear
GeminiUnavailableError instead of propagating a raw SDK exception or
hanging, and (2) the short retry/timeout policy is actually the one wired
into the request, not Google's much longer default.
"""

from unittest.mock import MagicMock

import pytest
from google.api_core.exceptions import DeadlineExceeded, InvalidArgument, ResourceExhausted, RetryError

from app.rag.gemini_client import _RETRY, _REQUEST_TIMEOUT_SECONDS, GeminiUnavailableError, generate_json


def test_generate_json_returns_response_text_on_success():
    model = MagicMock()
    model.generate_content.return_value = MagicMock(text='{"ok": true}')

    result = generate_json(model, "some prompt")

    assert result == '{"ok": true}'


def test_generate_json_passes_short_retry_and_timeout_policy():
    model = MagicMock()
    model.generate_content.return_value = MagicMock(text="{}")

    generate_json(model, "some prompt")

    _, kwargs = model.generate_content.call_args
    request_options = kwargs["request_options"]
    assert request_options["retry"] is _RETRY
    assert request_options["retry"].timeout == 10.0  # a few seconds, not Google's long default
    assert request_options["timeout"] == _REQUEST_TIMEOUT_SECONDS


def test_generate_json_wraps_resource_exhausted_in_clear_error():
    model = MagicMock()
    model.generate_content.side_effect = ResourceExhausted("quota exceeded")

    with pytest.raises(GeminiUnavailableError, match="quota"):
        generate_json(model, "some prompt")


def test_generate_json_wraps_deadline_exceeded_in_clear_error():
    model = MagicMock()
    model.generate_content.side_effect = DeadlineExceeded("deadline exceeded")

    with pytest.raises(GeminiUnavailableError):
        generate_json(model, "some prompt")


def test_generate_json_wraps_retry_error_in_clear_error():
    # This is what actually surfaces (confirmed against a real
    # quota-exhausted run) when _RETRY's own 10s budget is exceeded mid
    # backoff — google.api_core wraps the last underlying error in a
    # RetryError rather than re-raising it directly.
    model = MagicMock()
    model.generate_content.side_effect = RetryError(
        "Timeout of 10.0s exceeded", cause=DeadlineExceeded("504 Deadline Exceeded")
    )

    with pytest.raises(GeminiUnavailableError):
        generate_json(model, "some prompt")


def test_generate_json_strips_raw_protobuf_dump_from_error_message():
    # Regression: found via a real quota-exhausted call surfaced to a real
    # user in the UI. google.api_core's ResourceExhausted.__str__() runs a
    # clean first line, then dumps raw protobuf (quota_dimensions,
    # violations, retry_delay blocks) after a newline — that dump used to
    # get embedded verbatim in GeminiUnavailableError's message and shown
    # to the user as unreadable noise. Only the first line should survive.
    model = MagicMock()
    model.generate_content.side_effect = ResourceExhausted(
        "429 You exceeded your current quota, see https://ai.dev/rate-limit.\n"
        '* Quota exceeded for metric: generate_content_free_tier_requests, limit: 20\n'
        "Please retry in 12.3s. [links {\n  description: \"...\"\n}\n]"
    )

    with pytest.raises(GeminiUnavailableError) as exc_info:
        generate_json(model, "some prompt")

    message = str(exc_info.value)
    assert "429 You exceeded your current quota" in message
    assert "quota_dimensions" not in message
    assert "links {" not in message
    assert "violations" not in message


def test_generate_json_does_not_swallow_non_retryable_errors():
    model = MagicMock()
    model.generate_content.side_effect = InvalidArgument("bad request")

    with pytest.raises(InvalidArgument):
        generate_json(model, "some prompt")
