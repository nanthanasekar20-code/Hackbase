"""
Thin wrapper around the Gemini API client, used by the Planning Agent
(app/agents/planning_agent.py) and the Resume Value enrichment script
(scripts/enrich_resume_value.py).

Requires settings.gemini_api_key to be set (copy .env.example to .env and
fill it in — get a free key at https://aistudio.google.com/apikey). If
it's missing, get_gemini_model() raises GeminiNotConfiguredError with
instructions rather than silently falling back to fabricated output.
"""

from __future__ import annotations

from google.api_core.exceptions import DeadlineExceeded, ResourceExhausted, RetryError, ServiceUnavailable
from google.api_core.retry import Retry, if_exception_type

from app.core.config import settings

# Errors worth a couple of short retries: quota/rate-limit (429) and
# transient upstream issues (503/504). Google's own default retry policy on
# these calls keeps retrying for a very long time (observed: over an hour
# on a real quota-exhausted run) before finally giving up — that's a bad
# fit for anything user-facing or for a batch script that should move on
# and checkpoint. This caps the whole retry loop to a few seconds instead:
# fail fast and loudly, same as everywhere else in this module.
_RETRYABLE_ERRORS = (ResourceExhausted, ServiceUnavailable, DeadlineExceeded)
_DEFAULT_RETRY_TIMEOUT_SECONDS = 10.0
_REQUEST_TIMEOUT_SECONDS = 15


def _build_retry(timeout: float) -> Retry:
    return Retry(
        predicate=if_exception_type(*_RETRYABLE_ERRORS),
        initial=1.0,
        multiplier=2.0,
        maximum=4.0,
        timeout=timeout,
    )


_RETRY = _build_retry(_DEFAULT_RETRY_TIMEOUT_SECONDS)

# What generate_json actually needs to catch: the retryable errors above
# (if one somehow escapes without being retried) PLUS RetryError — which,
# confirmed against a real quota-exhausted call, is what _RETRY itself
# raises once its 10s budget runs out mid-backoff. RetryError wraps the
# last underlying error rather than re-raising it directly, so it has to be
# caught explicitly too or it leaks out as a raw, unwrapped traceback
# instead of a clear GeminiUnavailableError.
_CAUGHT_ERRORS = _RETRYABLE_ERRORS + (RetryError,)


class GeminiNotConfiguredError(RuntimeError):
    """Raised when a Gemini-backed call is attempted without an API key."""


class GeminiUnavailableError(RuntimeError):
    """Raised when Gemini keeps failing (quota exhausted / transient outage) after a few short retries."""


def get_gemini_model(model_name: str | None = None):
    """
    Returns a configured google.generativeai.GenerativeModel. Imports the
    SDK lazily so nothing else in the app pays its import cost, and so a
    machine without it installed can still run everything that doesn't
    need Gemini.
    """
    if not settings.gemini_api_key:
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to "
            "backend/.env and set GEMINI_API_KEY=<your key> (get a free "
            "key at https://aistudio.google.com/apikey), then restart the "
            "server."
        )

    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(model_name or settings.gemini_model_name)


def generate_json(
    model,
    prompt: str,
    *,
    timeout: float = _REQUEST_TIMEOUT_SECONDS,
    retry_timeout: float = _DEFAULT_RETRY_TIMEOUT_SECONDS,
) -> str:
    """
    Calls the model asking for a JSON response and returns the raw text.
    Split out from callers so the prompt-building and response-parsing
    logic around this (in planning_agent.py / enrich_resume_value.py) can
    be unit-tested without a real network call — only this one function
    actually talks to Gemini.

    Retries a couple of times (a few seconds total, see _RETRY above) on
    quota/rate-limit or transient upstream errors, then raises
    GeminiUnavailableError with a clear message — never hangs for minutes
    retrying a real quota exhaustion, and never fabricates a response.

    `timeout`/`retry_timeout` default to the values tuned for the
    user-facing /plan endpoint (fail fast). A batch/offline caller that can
    tolerate a slower response — e.g. enrich_resume_value.py generating a
    large multi-problem JSON array on a smaller model — can pass larger
    values instead of shrinking its batch size and burning extra real
    quota just to fit a deadline meant for interactive use.
    """
    retry = _RETRY if retry_timeout == _DEFAULT_RETRY_TIMEOUT_SECONDS else _build_retry(retry_timeout)
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
            request_options={"retry": retry, "timeout": timeout},
        )
    except _CAUGHT_ERRORS as exc:
        # str(exc) for these errors often runs on for a while after the
        # first line — Google's client appends a raw protobuf dump (quota
        # dimensions, violation details, retry_delay) that's meaningless to
        # a person reading it in the UI. The first line alone is already a
        # complete, human-readable sentence (verified against a real quota
        # error and a real "model overloaded" error) — keep just that.
        reason = str(exc).split("\n", 1)[0].strip()
        raise GeminiUnavailableError(
            f"Gemini call failed after retrying for ~{retry_timeout:.0f}s: {reason} "
            "This is usually the free-tier quota (20 requests/day — see "
            "https://ai.dev/rate-limit) or a transient outage. Try again later."
        ) from exc
    return response.text
