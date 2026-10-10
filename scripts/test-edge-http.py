#!/usr/bin/env python3
"""Exercise Nginx routes and TLS-mode behavior with in-container mock upstreams."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
NGINX_IMAGE = "nginx:1.27-alpine"


def docker(*args, check=True, **kwargs):
    return subprocess.run(["docker", *args], check=check, text=True, capture_output=True, **kwargs)


def request(container, url, host, tls=False, trace="edge:test-42"):
    args = ["exec", container, "wget", "-S", "-qO-", "-Y", "off", "-T", "2",
            "--header", f"Host: {host}", "--header", "Authorization: Bearer test-token",
            "--header", f"X-Trace-Id: {trace}"]
    if tls:
        args.append("--no-check-certificate")
    args.append(url)
    return docker(*args, check=False)


def assert_route(container, url, host, tls=False):
    result = request(container, url, host, tls=tls)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "path": "/check",
        "authorization": "Bearer test-token",
        "trace_id": "edge:test-42",
    }, payload
    assert "X-Trace-Id: edge:test-42" in result.stderr, result.stderr


def check_mode(mode):
    container = f"fkit-edge-test-{os.getpid()}-{mode.replace('-', '')}"
    with tempfile.TemporaryDirectory(prefix=".fkit-edge-test-", dir=ROOT) as temporary:
        temp = Path(temporary)
        conf_dir = temp / "conf.d"
        conf_dir.mkdir()
        cert_dir = (temp / "self-signed/bi.kitexp.ru" if mode == "self-signed"
                    else temp / "live/bi.kitexp.ru")
        cert_dir.mkdir(parents=True)
        subprocess.run([
            "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-days", "1",
            "-keyout", str(cert_dir / "privkey.pem"),
            "-out", str(cert_dir / "fullchain.pem"),
            "-subj", "/CN=bi.kitexp.ru",
            "-addext", "subjectAltName=DNS:bi.kitexp.ru,DNS:*.bi.kitexp.ru",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        http_conf = (ROOT / "nginx/default.conf").read_text()
        http_conf = http_conf.replace("analytics:8080", "127.0.0.1:18081")
        http_conf = http_conf.replace("generator:8080", "127.0.0.1:18082")
        http_conf = http_conf.replace("web:80", "127.0.0.1:18083")
        # Mock upstreams run in the same container, so no service or host ports are exposed.
        http_conf += """
server {
  listen 18081;
  location / {
    default_type application/json;
    add_header X-Trace-Id $http_x_trace_id always;
    return 200 '{\"path\":\"$request_uri\",\"authorization\":\"$http_authorization\",\"trace_id\":\"$http_x_trace_id\"}';
  }
}
server {
  listen 18082;
  location / {
    default_type application/json;
    add_header X-Trace-Id $http_x_trace_id always;
    return 200 '{\"path\":\"$request_uri\",\"authorization\":\"$http_authorization\",\"trace_id\":\"$http_x_trace_id\"}';
  }
}
server { listen 18083; return 200 'web'; }
"""
        (conf_dir / "default.conf").write_text(http_conf)
        tls_template = temp / "tls.conf.template"
        tls_conf = (ROOT / "nginx/tls.conf.template").read_text()
        tls_conf = tls_conf.replace("analytics:8080", "127.0.0.1:18081")
        tls_conf = tls_conf.replace("generator:8080", "127.0.0.1:18082")
        tls_conf = tls_conf.replace("web:80", "127.0.0.1:18083")
        tls_template.write_text(tls_conf)

        docker("run", "-d", "--name", container,
               "-e", f"TLS_MODE={mode}",
               "--add-host", "bi.kitexp.ru:127.0.0.1",
               "--add-host", "node.bi.kitexp.ru:127.0.0.1",
               "-v", f"{conf_dir}:/etc/nginx/conf.d",
               "-v", f"{tls_template}:/etc/nginx/tls.conf.template:ro",
               "-v", f"{ROOT / 'nginx/start.sh'}:/opt/fkit/nginx/start.sh:ro",
               "-v", f"{temp}:/etc/letsencrypt:ro",
               NGINX_IMAGE, "/bin/sh", "/opt/fkit/nginx/start.sh")
        try:
            ready = False
            for _ in range(40):
                result = request(container, "http://127.0.0.1/api/analytics/check", "45.132.176.28")
                if result.returncode == 0:
                    ready = True
                    break
                time.sleep(0.1)
            diagnostics = docker("exec", container, "sh", "-c", "netstat -lnt; tail -n 90 /etc/nginx/conf.d/default.conf", check=False)
            assert ready, f"{docker('logs', container, check=False).stderr}\n{diagnostics.stdout}\n{diagnostics.stderr}\nlast request: {result.stderr}"

            if mode == "off":
                assert_route(container, "http://127.0.0.1/api/analytics/check", "bi.kitexp.ru")
                # TLS is intentionally absent in off mode.
                tls_attempt = request(container, "https://127.0.0.1/api/analytics/check", "bi.kitexp.ru", tls=True)
                assert tls_attempt.returncode != 0
            else:
                redirect = request(container, "http://127.0.0.1/api/analytics/check", "bi.kitexp.ru")
                assert "301 Moved Permanently" in redirect.stderr, redirect.stderr
                assert "Location: https://bi.kitexp.ru/api/analytics/check" in redirect.stderr, redirect.stderr
                assert_route(container, "https://127.0.0.1/api/analytics/check", "bi.kitexp.ru", tls=True)
                assert_route(container, "https://127.0.0.1/api/generator/check", "node.bi.kitexp.ru", tls=True)

            # IP access remains HTTP in all modes.
            assert_route(container, "http://127.0.0.1/api/generator/check", "45.132.176.28")

            for app in ("analytics", "generator"):
                metrics_tls = mode != "off"
                metrics_scheme = "https" if metrics_tls else "http"
                metrics = request(
                    container,
                    f"{metrics_scheme}://127.0.0.1/api/{app}/actuator/prometheus",
                    "bi.kitexp.ru",
                    tls=metrics_tls,
                )
                assert metrics.returncode != 0 and "404 Not Found" in metrics.stderr, metrics.stderr
        finally:
            docker("rm", "-f", container, check=False)


for selected_mode in ("off", "self-signed", "public"):
    check_mode(selected_mode)
    print(f"Nginx route/TLS behavior passed for TLS_MODE={selected_mode}.")
