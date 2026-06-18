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
"""Regression tests for Query.get() → Session.get() migration.

SQLAlchemy 1.4+ deprecates ``Query.get()`` in favour of ``Session.get()``.
These tests verify that the migrated call-sites use the modern API and
behave correctly (return the model instance or ``None``).
"""

from __future__ import annotations

import ast
import pathlib
import warnings

import pytest

# Paths (relative to repo root) that were migrated.
_MIGRATED_SOURCE_FILES: list[str] = [
    "superset/security/manager.py",
    "superset/mcp_service/chart/preview_utils.py",
    "superset/daos/dataset.py",
    "superset/commands/importers/v1/examples.py",
    "superset/commands/sql_lab/estimate.py",
    "superset/commands/dataset/duplicate.py",
    "superset/cli/export_example.py",
]


def _repo_root() -> pathlib.Path:
    """Return the repository root (two levels above this test file)."""
    return pathlib.Path(__file__).resolve().parent.parent.parent


def _has_query_get_call(source: str) -> list[int]:
    """Return line numbers where ``session.query(Model).get(...)`` appears.

    Uses AST inspection so comments and strings are ignored.
    """
    tree = ast.parse(source)
    hits: list[int] = []
    for node in ast.walk(tree):
        # Look for call nodes like: <expr>.get(<args>)
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "get":
            continue
        # The object being called should itself be a Call (the .query() call)
        inner = func.value
        if not isinstance(inner, ast.Call):
            continue
        inner_func = inner.func
        if isinstance(inner_func, ast.Attribute) and inner_func.attr == "query":
            hits.append(node.lineno)
    return hits


@pytest.mark.parametrize("rel_path", _MIGRATED_SOURCE_FILES)
def test_no_deprecated_query_get_in_migrated_files(rel_path: str) -> None:
    """Ensure migrated source files no longer contain Query.get() calls."""
    source_file = _repo_root() / rel_path
    assert source_file.exists(), f"Expected source file not found: {rel_path}"
    source = source_file.read_text()
    hits = _has_query_get_call(source)
    assert hits == [], (
        f"{rel_path} still contains deprecated Query.get() at line(s) {hits}. "
        "Use Session.get(Model, id) instead."
    )


def test_session_get_no_legacy_warning(app_context: None) -> None:
    """Verify that Session.get() does not emit LegacyAPIWarning."""
    from superset.extensions import db
    from superset.models.dashboard import Dashboard

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        db.session.get(Dashboard, -1)

    legacy = [w for w in caught if "LegacyAPI" in str(w.category.__name__)]
    assert legacy == [], f"Session.get() emitted LegacyAPIWarning: {legacy}"
