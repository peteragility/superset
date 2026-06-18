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
"""Regression tests for the cryptography upgrade (GHSA-537c-gmf6-5ccf)."""

import importlib

from packaging.version import Version


def test_cryptography_minimum_version() -> None:
    """Ensure the installed cryptography version is at least 48.0.1,
    the first release that ships a non-vulnerable OpenSSL
    (GHSA-537c-gmf6-5ccf)."""
    cryptography = importlib.import_module("cryptography")
    assert Version(cryptography.__version__) >= Version("48.0.1")


def test_no_default_backend_import() -> None:
    """Verify that Superset call-sites no longer import the deprecated
    ``default_backend`` helper removed in modern cryptography releases."""
    from superset.db_engine_specs import snowflake as snowflake_spec
    from superset.utils import core as utils_core

    utils_src = importlib.util.find_spec(utils_core.__name__)
    snowflake_src = importlib.util.find_spec(snowflake_spec.__name__)

    for spec in (utils_src, snowflake_src):
        assert spec is not None
        assert spec.origin is not None
        with open(spec.origin) as fh:
            source = fh.read()
        assert "default_backend" not in source, (
            f"{spec.origin} still references the deprecated default_backend"
        )


def test_parse_ssl_cert_without_backend() -> None:
    """``parse_ssl_cert`` must work without the deprecated backend arg."""
    from cryptography.x509 import load_pem_x509_certificate

    from tests.integration_tests.fixtures.certificates import ssl_certificate

    cert = load_pem_x509_certificate(ssl_certificate.encode("utf-8"))
    assert cert.serial_number > 0


def test_load_pem_private_key_without_backend() -> None:
    """``serialization.load_pem_private_key`` must work without the
    deprecated backend arg, as used by the Snowflake engine spec."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    loaded = serialization.load_pem_private_key(pem, password=None)
    assert loaded.key_size == 2048
