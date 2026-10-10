#!/usr/bin/env python3
"""Verify failed renewal logging and successful execution of the Nginx reload hook."""

import os
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RENEW = ROOT / "certbot/renew.sh"


def run_renew(temp: Path, mode: str, nginx_pid: int) -> subprocess.CompletedProcess[str]:
    bin_dir = temp / f"bin-{mode}"
    bin_dir.mkdir()
    call_log = temp / f"certbot-{mode}.log"

    fake_certbot = bin_dir / "certbot"
    fake_certbot.write_text("""#!/bin/sh
printf '%s\n' "$*" >> "$TEST_CERTBOT_CALL_LOG"
hook=''
while [ "$#" -gt 0 ]; do
  if [ "$1" = --deploy-hook ]; then shift; hook="$1"; fi
  shift
done
[ "$FAKE_CERTBOT_MODE" = success ] || exit 1
/bin/sh -c "$hook"
""")
    fake_certbot.chmod(0o755)

    fake_sleep = bin_dir / "sleep"
    fake_sleep.write_text("#!/bin/sh\nkill -TERM \"$PPID\"\nexit 0\n")
    fake_sleep.chmod(0o755)

    env = os.environ.copy()
    env.update({
        "TLS_MODE": "public",
        "PATH": f"{bin_dir}:{env.get('PATH', '')}",
        "TEST_CERTBOT_CALL_LOG": str(call_log),
        "FAKE_CERTBOT_MODE": mode,
        "NGINX_MASTER_PID": str(nginx_pid),
        "RELOAD_HOOK": str(ROOT / "certbot/reload-nginx.sh"),
    })
    result = subprocess.run(["sh", str(RENEW)], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode in (-15, 143), result
    assert "--deploy-hook" in call_log.read_text() and "reload-nginx.sh" in call_log.read_text()
    return result


with tempfile.TemporaryDirectory(prefix="fkit-renew-test-") as temporary:
    temp = Path(temporary)
    marker = temp / "reloaded"
    ready = temp / "ready"
    fake_nginx = temp / "fake-nginx.sh"
    fake_nginx.write_text("""#!/bin/sh
trap 'printf reloaded > "$TEST_RELOAD_MARKER"' HUP
printf ready > "$TEST_READY_MARKER"
while :; do /bin/sleep 1; done
""")
    fake_nginx.chmod(0o755)
    nginx_env = os.environ | {"TEST_RELOAD_MARKER": str(marker), "TEST_READY_MARKER": str(ready)}
    nginx = subprocess.Popen([str(fake_nginx)], env=nginx_env)
    try:
        for _ in range(50):
            if ready.exists():
                break
            time.sleep(0.02)
        assert ready.exists()

        failed = run_renew(temp, "failure", nginx.pid)
        assert "Certbot renewal failed; the current certificate is retained." in failed.stderr
        assert not marker.exists(), "failed renewal must not reload Nginx"

        succeeded = run_renew(temp, "success", nginx.pid)
        assert "Certbot renewal check completed." in succeeded.stdout
        for _ in range(50):
            if marker.exists():
                break
            time.sleep(0.02)
        assert marker.read_text() == "reloaded"
    finally:
        nginx.terminate()
        nginx.wait(timeout=5)

print("Failed renewal is logged without reload; successful renewal executes the Nginx reload hook.")
