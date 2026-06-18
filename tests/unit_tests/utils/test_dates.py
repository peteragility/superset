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
import warnings
from datetime import datetime, timezone
from unittest.mock import patch

from superset.utils.dates import datetime_to_epoch, now_as_float


def test_now_as_float_returns_positive_epoch_ms() -> None:
    result = now_as_float()
    assert isinstance(result, float)
    assert result > 0


def test_now_as_float_no_utcnow_deprecation_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        now_as_float()
    utcnow_warnings = [w for w in caught if "utcnow" in str(w.message).lower()]
    assert len(utcnow_warnings) == 0


def test_now_as_float_uses_timezone_aware_datetime() -> None:
    fixed_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    with patch(
        "superset.utils.dates.datetime",
        wraps=datetime,
    ) as mock_dt:
        mock_dt.now.return_value = fixed_dt
        result = now_as_float()
    mock_dt.now.assert_called_once_with(timezone.utc)
    expected = datetime_to_epoch(fixed_dt)
    assert result == expected


def test_datetime_to_epoch_naive_and_aware_agree() -> None:
    naive = datetime(2024, 1, 1, 0, 0, 0)
    aware = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert datetime_to_epoch(naive) == datetime_to_epoch(aware)
