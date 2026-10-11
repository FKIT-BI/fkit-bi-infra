#!/usr/bin/env python3
"""Verify the public Certbot command without contacting ACME or Yandex Cloud."""

import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "certbot/setup.sh"


def execute(exit_code: int):
    with tempfile.TemporaryDirectory(prefix="fkit-setup-test-") as temporary:
        temp = Path(temporary)
        bin_dir = temp / "bin"
        bin_dir.mkdir()
        key_file = temp / "key.json"
        key_file.write_text("{}")
        call_log = temp / "certbot.log"
        fake = bin_dir / "certbot"
        fake.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" > \"$TEST_CERTBOT_CALL_LOG\"\nexit \"$FAKE_CERTBOT_EXIT\"\n")
        fake.chmod(0o755)
        key_validator = bin_dir / "python3"
        key_validator.write_text("#!/bin/sh\nexit \"$FAKE_KEY_VALIDATION_EXIT\"\n")
        key_validator.chmod(0o755)
        env = os.environ | {
            "TLS_MODE": "public",
            "CERTBOT_EMAIL": "operator@example.test",
            "DNS_ZONE_ID": "zone-test",
            "YANDEX_SERVICE_ACCOUNT_ID": "service-account-test",
            "YANDEX_KEY_ID": "key-test",
            "YANDEX_SERVICE_ACCOUNT_KEY_FILE": str(key_file),
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
            "TEST_CERTBOT_CALL_LOG": str(call_log),
            "FAKE_CERTBOT_EXIT": str(exit_code),
            "FAKE_KEY_VALIDATION_EXIT": "0",
        }
        result = subprocess.run(["sh", str(SETUP)], env=env, capture_output=True, text=True)
        return result, call_log.read_text() if call_log.exists() else ""


success, command = execute(0)
assert success.returncode == 0, success.stderr
for expected in (
    "certonly --non-interactive --agree-tos --email operator@example.test",
    "--manual --preferred-challenges dns",
    "--manual-auth-hook python3 /opt/fkit/certbot/yandex_dns.py auth",
    "--manual-cleanup-hook python3 /opt/fkit/certbot/yandex_dns.py cleanup",
    "--cert-name bi.kitexp.ru -d bi.kitexp.ru -d *.bi.kitexp.ru",
):
    assert expected in command, command

failure, _ = execute(17)
assert failure.returncode == 17, failure

with tempfile.TemporaryDirectory(prefix="fkit-invalid-yandex-key-") as temporary:
    temp = Path(temporary)
    bin_dir = temp / "bin"
    bin_dir.mkdir()
    key_file = temp / "key.json"
    key_file.write_text("{}")
    validator = bin_dir / "python3"
    validator.write_text("#!/bin/sh\nexit 1\n")
    validator.chmod(0o755)
    call_log = temp / "certbot.log"
    fake = bin_dir / "certbot"
    fake.write_text("#!/bin/sh\nprintf called > \"$TEST_CERTBOT_CALL_LOG\"\n")
    fake.chmod(0o755)
    env = os.environ | {
        "TLS_MODE": "public", "CERTBOT_EMAIL": "operator@example.test",
        "DNS_ZONE_ID": "zone-test", "YANDEX_SERVICE_ACCOUNT_ID": "service-account-test",
        "YANDEX_KEY_ID": "key-test", "YANDEX_SERVICE_ACCOUNT_KEY_FILE": str(key_file),
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "TEST_CERTBOT_CALL_LOG": str(call_log),
    }
    result = subprocess.run(["sh", str(SETUP)], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert not call_log.exists(), "Certbot must not start when key validation fails"

print("Public setup passes the expected DNS-01 apex/wildcard command and propagates Certbot failures.")
