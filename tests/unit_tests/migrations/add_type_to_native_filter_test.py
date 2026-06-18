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
import logging
from importlib import import_module
from unittest.mock import MagicMock, patch

import pytest

from superset.utils import json

migration_module = import_module(
    "superset.migrations.versions."
    "2021-08-31_11-37_021b81fe4fbb_add_type_to_native_filter_configuration",
)
upgrade = migration_module.upgrade
downgrade = migration_module.downgrade
Dashboard = migration_module.Dashboard


@pytest.fixture
def mock_session():
    with (
        patch.object(migration_module, "op") as mock_op,
        patch.object(migration_module, "db") as mock_db,
    ):
        session = MagicMock()
        mock_db.Session.return_value = session
        mock_op.get_bind.return_value = MagicMock()
        yield session


def _make_dashboard(pk: int, json_metadata: str | None) -> MagicMock:
    dashboard = MagicMock(spec=Dashboard)
    dashboard.id = pk
    dashboard.json_metadata = json_metadata
    return dashboard


def test_upgrade_skips_invalid_json_and_logs_with_context(
    mock_session: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """The upgrade path should catch ValueError for malformed JSON,
    log the dashboard ID for debugging, and continue processing."""
    valid_meta = json.dumps({"native_filter_configuration": [{"name": "filter1"}]})
    bad_dashboard = _make_dashboard(42, "{invalid json")
    good_dashboard = _make_dashboard(99, valid_meta)

    mock_session.query.return_value.all.return_value = [
        bad_dashboard,
        good_dashboard,
    ]

    with caplog.at_level(logging.ERROR, logger="alembic.env"):
        upgrade()

    assert "Dashboard<pk:42>" in caplog.text
    # The good dashboard should still be processed
    updated = json.loads(good_dashboard.json_metadata)
    assert updated["native_filter_configuration"][0]["type"] == "NATIVE_FILTER"
    mock_session.commit.assert_called_once()


def test_downgrade_skips_invalid_json_and_logs_with_context(
    mock_session: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """The downgrade path should catch ValueError for malformed JSON,
    log the dashboard ID for debugging, and continue processing."""
    valid_meta = json.dumps(
        {"native_filter_configuration": [{"name": "filter1", "type": "NATIVE_FILTER"}]}
    )
    bad_dashboard = _make_dashboard(7, "not-json")
    good_dashboard = _make_dashboard(8, valid_meta)

    mock_session.query.return_value.all.return_value = [
        bad_dashboard,
        good_dashboard,
    ]

    with caplog.at_level(logging.ERROR, logger="alembic.env"):
        downgrade()

    assert "Dashboard<pk:7>" in caplog.text
    updated = json.loads(good_dashboard.json_metadata)
    assert "type" not in updated["native_filter_configuration"][0]
    mock_session.commit.assert_called_once()


def test_upgrade_does_not_catch_non_value_errors(
    mock_session: MagicMock,
) -> None:
    """Exceptions other than ValueError should propagate (not be swallowed)."""
    bad_dashboard = _make_dashboard(1, "anything")
    mock_session.query.return_value.all.return_value = [bad_dashboard]

    with patch.object(
        migration_module.json,
        "loads",
        side_effect=RuntimeError("unexpected"),
    ):
        with pytest.raises(RuntimeError, match="unexpected"):
            upgrade()
