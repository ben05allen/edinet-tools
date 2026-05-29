"""Pytest configuration for EDINET API Tools tests.

The autouse `set_test_env_vars` fixture below scrubs API credentials for
every non-integration test so accidental real-network calls fail loud.
Integration tests (marked with @pytest.mark.integration) keep the real
EDINET_API_KEY so they can talk to the live API.

Note: prior versions of this file shipped ~9 stand-alone sample/mock
fixtures (sample_csv_data, mock_llm_response, etc.). Verified 2026-05-23
that none were consumed by any test in the suite — dead code, removed.
Add new fixtures here only when at least one test will use them; otherwise
inline the test data with the test that needs it (easier to reason about,
no spooky-action-at-a-distance shape coupling).
"""
import os

import pytest


@pytest.fixture(autouse=True)
def set_test_env_vars(request):
    """Scrub credentials for the duration of every non-integration test.

    Integration tests (@pytest.mark.integration) keep the real
    EDINET_API_KEY so they can hit the live API; everything else gets a
    placeholder so any accidental real-network code path fails on auth
    rather than silently hitting prod.
    """
    is_integration_test = request.node.get_closest_marker('integration') is not None

    original_env = {}
    test_env_vars = {
        'LLM_API_KEY': 'test-llm-key',
        'LLM_MODEL': 'claude-4-sonnet',
        'LLM_FALLBACK_MODEL': 'gpt-5-mini',
    }
    if not is_integration_test:
        test_env_vars['EDINET_API_KEY'] = 'test-api-key'

    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value
