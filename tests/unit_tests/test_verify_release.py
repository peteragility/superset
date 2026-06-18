# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _import_verify_release(monkeypatch: pytest.MonkeyPatch):
    """Make the RELEASING directory importable for the test module."""
    monkeypatch.syspath_prepend(
        str(
            pytest.importorskip("pathlib").Path(__file__).resolve().parents[2]
            / "RELEASING"
        )
    )


def test_verify_key_requests_get_called_with_timeout():
    """verify_key() must pass an explicit timeout to requests.get (Bandit B113)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ABCDEF1234567890 user@apache.org"

    with patch("requests.get", return_value=mock_response) as mock_get:
        # Import here so the monkeypatch fixture has taken effect
        from verify_release import verify_key

        verify_key("ABCDEF1234567890", "user@apache.org")

        mock_get.assert_called_once_with(
            "https://downloads.apache.org/superset/KEYS",
            timeout=30,
        )


def test_verify_key_returns_verified_when_key_and_email_found():
    """verify_key() returns success message when both key and email are in KEYS."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ABCDEF1234567890 user@apache.org"

    with patch("requests.get", return_value=mock_response):
        from verify_release import verify_key

        result = verify_key("ABCDEF1234567890", "user@apache.org")
        assert result == "RSA/EDDSA key and email verified against Apache KEYS file"


def test_verify_key_returns_failure_when_fetch_fails():
    """verify_key() returns failure message on non-200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("requests.get", return_value=mock_response):
        from verify_release import verify_key

        result = verify_key("ABCDEF1234567890", "user@apache.org")
        assert result == "Failed to fetch KEYS file"
