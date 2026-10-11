#!/usr/bin/env python3
"""Start an isolated Compose stack and verify monitoring outages do not affect apps."""

import base64
import ipaddress
import json
import os
import socket
import subprocess
import time
import urllib.parse
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = Path(ROOT) / "observability/grafana/dashboards"
PROJECT = f"fkit-story14-smoke-{os.getpid()}"
NETWORK = f"{PROJECT}_default"
ANALYTICS_IMAGE = f"fkit-bi-analytics:story14-{os.getpid()}"
GENERATOR_IMAGE = f"fkit-bi-generator:story14-{os.getpid()}"
JWT_SECRET = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
BOOTSTRAP_PASSWORD = "Story14-Local-Test-Only-Password-42"


def repository_path(name):
    checkout = Path(ROOT) / ".ci" / name
    if checkout.is_dir():
        return checkout
    return Path(ROOT).parent / name


def run(command, *, cwd=ROOT, env=None, check=True, timeout=180):
    try:
        return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True,
                              check=check, timeout=timeout)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{error.stdout}\n{error.stderr}") from error


def compose(*args, env=None, check=True, timeout=180):
    return run(["docker", "compose", "--env-file", ".env.example", "--project-name", PROJECT,
                *args], env=env, check=check, timeout=timeout)


def available_compose_subnet():
    network_ids = run(["docker", "network", "ls", "-q"], timeout=15).stdout.split()
    existing = []
    if network_ids:
        for network in json.loads(run(["docker", "network", "inspect", *network_ids], timeout=30).stdout):
            for config in network.get("IPAM", {}).get("Config") or []:
                if config.get("Subnet"):
                    existing.append(ipaddress.ip_network(config["Subnet"], strict=False))
    for third_octet in range(1, 255):
        candidate = ipaddress.ip_network(f"10.240.{third_octet}.0/24")
        if not any(candidate.version == used.version and candidate.overlaps(used) for used in existing):
            return str(candidate)
    raise RuntimeError("No free /24 subnet found for the monitoring smoke test")


def container_request(service, path, trace_id="monitoring-isolation-42", post_data=None):
    command = ["exec", "-T", service, "wget", "-S", "-qO-", "-Y", "off", "-T", "3",
               "--header", f"X-Trace-Id: {trace_id}"]
    if post_data is not None:
        command.extend(["--header", "Content-Type: application/json", "--post-data", post_data])
    command.append(f"http://127.0.0.1:8080{path}")
    return compose(*command, check=False, timeout=15)


def assert_business_services(env, require_login):
    for service in ("analytics", "generator"):
        result = container_request(service, "/actuator/health/readiness")
        assert result.returncode == 0 and '"status":"UP"' in result.stdout, (service, result.stdout, result.stderr)
        assert "X-Trace-Id: monitoring-isolation-42" in result.stderr, (service, result.stderr)
        metrics = container_request(service, "/actuator/prometheus")
        application = f"fkit-bi-{service}"
        assert metrics.returncode == 0 and "jvm_memory_used_bytes" in metrics.stdout, (service, metrics.stderr)
        assert "http_server_requests_seconds_bucket" in metrics.stdout, service
        assert f'application="{application}"' in metrics.stdout, service

    if require_login:
        body = json.dumps({"username": "story14-smoke", "password": BOOTSTRAP_PASSWORD})
        result = container_request("analytics", "/api/v1/auth/login", post_data=body)
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload.get("accessToken"), payload
        assert "X-Trace-Id: monitoring-isolation-42" in result.stderr
        token = payload["accessToken"]
        logs = compose("logs", "--no-color", "analytics", check=True, timeout=15).stdout
        assert BOOTSTRAP_PASSWORD not in logs and token not in logs, "credentials were written to Analytics logs"


def helper_get(path, authorization=None):
    command = ["docker", "run", "--rm", "--network", NETWORK, "alpine:3.22", "wget",
               "-qO-", "-Y", "off", "-T", "4"]
    if authorization:
        command.extend(["--header", f"Authorization: {authorization}"])
    command.append(path)
    return run(command, check=True, timeout=15).stdout


def wait_for_monitoring():
    deadline = time.monotonic() + 120
    last_error = None
    last_state = None
    while time.monotonic() < deadline:
        try:
            targets = json.loads(helper_get("http://prometheus:9090/api/v1/targets"))
            health = {target["labels"]["job"]: target["health"]
                      for target in targets["data"]["activeTargets"]}
            last_state = {"targets": health}
            if all(health.get(job) == "up" for job in ("analytics", "generator", "postgres", "node")):
                dashboards = json.loads(helper_get("http://grafana:3000/api/search?type=dash-db",
                                                   "Basic " + base64.b64encode(b"admin:replace-with-a-grafana-secret").decode()))
                last_state["dashboards"] = len(dashboards)
                if len(dashboards) == 6:
                    return health, dashboards
        except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as error:
            last_error = error
        time.sleep(1)
    raise RuntimeError(f"Monitoring targets/dashboards did not become ready: {last_state}; last error: {last_error}")


def dashboard_expressions():
    def collect(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "expr" and isinstance(child, str):
                    yield child
                else:
                    yield from collect(child)
        elif isinstance(value, list):
            for child in value:
                yield from collect(child)

    for dashboard in sorted(DASHBOARD_DIR.glob("*.json")):
        yield from collect(json.loads(dashboard.read_text()))


def prometheus_query(expression):
    encoded = urllib.parse.quote(expression, safe="")
    payload = json.loads(helper_get(f"http://prometheus:9090/api/v1/query?query={encoded}"))
    assert payload.get("status") == "success", (expression, payload)
    return payload["data"]["result"]


def assert_dashboard_queries():
    expressions = list(dashboard_expressions())
    assert expressions, "no dashboard queries found"
    for expression in expressions:
        prometheus_query(expression)
    for expression in (
        "up",
        "jvm_memory_used_bytes",
        "http_server_requests_seconds_count",
        "http_server_requests_seconds_bucket",
    ):
        assert prometheus_query(expression), f"runtime metric has no live series: {expression}"


def main():
    env = os.environ.copy()
    env.update({
        "ANALYTICS_IMAGE": ANALYTICS_IMAGE,
        "GENERATOR_IMAGE": GENERATOR_IMAGE,
        "FKIT_JWT_SECRET": JWT_SECRET,
        "FKIT_BOOTSTRAP_USERNAME": "story14-smoke",
        "FKIT_BOOTSTRAP_DISPLAY_NAME": "Story 1.4 smoke test",
        "FKIT_BOOTSTRAP_PASSWORD": BOOTSTRAP_PASSWORD,
        "GRAFANA_ADMIN_PASSWORD": "replace-with-a-grafana-secret",
    })
    env["COMPOSE_SUBNET"] = available_compose_subnet()
    env["PROXY_CONTAINER_IP"] = str(ipaddress.ip_network(env["COMPOSE_SUBNET"])[-2])
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        env["GRAFANA_PORT"] = str(listener.getsockname()[1])

    built_images = []
    try:
        run(["docker", "build", "-t", ANALYTICS_IMAGE, "-f", "Dockerfile", "."],
            cwd=repository_path("fkit-bi-analytics"), env=env, timeout=300)
        built_images.append(ANALYTICS_IMAGE)
        run(["docker", "build", "-t", GENERATOR_IMAGE, "-f", "Dockerfile", "."],
            cwd=repository_path("fkit-bi-generator"), env=env, timeout=300)
        built_images.append(GENERATOR_IMAGE)

        compose("up", "-d", "postgres", "analytics", "generator", "prometheus", "grafana",
                "postgres-exporter", "node-exporter", env=env, timeout=300)
        health, dashboards = wait_for_monitoring()
        assert len(dashboards) == 6 and len(health) >= 4, (health, dashboards)
        assert helper_get("http://grafana:3000/api/datasources",
                          "Basic " + base64.b64encode(b"admin:replace-with-a-grafana-secret").decode()).find("prometheus") >= 0
        compose("--profile", "bootstrap", "run", "--rm", "analytics-bootstrap", env=env, timeout=60)

        assert_business_services(env, require_login=True)
        assert_dashboard_queries()
        compose("stop", "prometheus", env=env, timeout=30)
        assert_business_services(env, require_login=True)
        compose("start", "prometheus", env=env, timeout=30)
        wait_for_monitoring()
        compose("stop", "grafana", env=env, timeout=30)
        assert_business_services(env, require_login=True)
        print("Readiness, Prometheus metrics and authenticated Analytics API stayed available through Prometheus and Grafana stops.")
    finally:
        compose("down", "--volumes", "--remove-orphans", env=env, check=False, timeout=90)
        for image in built_images:
            run(["docker", "image", "rm", image], check=False, timeout=20)


if __name__ == "__main__":
    main()
