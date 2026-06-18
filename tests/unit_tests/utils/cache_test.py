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

# pylint: disable=import-outside-toplevel, unused-argument

import re
import warnings
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from pytest_mock import MockerFixture


def test_set_and_log_cache_dttm_format(mocker: MockerFixture) -> None:
    """set_and_log_cache stores a naive-looking ISO timestamp (no tz suffix)."""
    from superset.utils.cache import set_and_log_cache

    cache_instance = mocker.MagicMock()
    cache_instance.cache = MagicMock()  # not NullCache
    mocker.patch(
        "superset.utils.cache.app",
        **{
            "config.__getitem__": lambda self, key: {
                "CACHE_DEFAULT_TIMEOUT": 300,
                "STATS_LOGGER": MagicMock(),
                "STORE_CACHE_KEYS_IN_METADATA_DB": False,
            }[key],
        },
    )

    set_and_log_cache(cache_instance, "key", {"data": 1}, cache_timeout=60)

    stored = cache_instance.set.call_args[0][1]
    assert "dttm" in stored
    # must match YYYY-MM-DDTHH:MM:SS with no timezone suffix
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", stored["dttm"])


def test_set_and_log_cache_no_utcnow_deprecation(mocker: MockerFixture) -> None:
    """set_and_log_cache must not emit a utcnow DeprecationWarning."""
    from superset.utils.cache import set_and_log_cache

    cache_instance = mocker.MagicMock()
    cache_instance.cache = MagicMock()
    mocker.patch(
        "superset.utils.cache.app",
        **{
            "config.__getitem__": lambda self, key: {
                "CACHE_DEFAULT_TIMEOUT": 300,
                "STATS_LOGGER": MagicMock(),
                "STORE_CACHE_KEYS_IN_METADATA_DB": False,
            }[key],
        },
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        set_and_log_cache(cache_instance, "key", {"data": 1}, cache_timeout=60)

    utcnow_warnings = [w for w in caught if "utcnow" in str(w.message).lower()]
    assert len(utcnow_warnings) == 0


def test_etag_cache_default_content_changed_time_is_aware() -> None:
    """etag_cache's fallback content_changed_time uses timezone-aware UTC."""
    fixed_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    with patch("superset.utils.cache.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = mock_dt.now(timezone.utc)
    assert result.tzinfo is not None


def test_memoized_func(mocker: MockerFixture) -> None:
    """
    Test the ``memoized_func`` decorator.
    """
    from superset.utils.cache import memoized_func

    cache = mocker.MagicMock()

    decorator = memoized_func("db:{self.id}:schema:{schema}:view_list", cache)
    decorated = decorator(lambda self, schema, cache=False: 42)

    self = mocker.MagicMock()
    self.id = 1

    # skip cache
    result = decorated(self, "public", cache=False)
    assert result == 42
    cache.get.assert_not_called()

    # check cache, no cached value
    cache.get.return_value = None
    result = decorated(self, "public", cache=True)
    assert result == 42
    cache.get.assert_called_with("db:1:schema:public:view_list")

    # check cache, cached value
    cache.get.return_value = 43
    result = decorated(self, "public", cache=True)
    assert result == 43
