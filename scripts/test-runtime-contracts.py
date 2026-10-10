#!/usr/bin/env python3
"""Fast static integration checks for Compose, proxy, and provisioning contracts."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
config = subprocess.run(
    ["docker", "compose", "--env-file", ".env.example", "config", "--format", "json"],
    cwd=ROOT,
    check=True,
    capture_output=True,
    text=True,
)
services = json.loads(config.stdout)["services"]

business = {"postgres", "analytics", "generator", "web"}
monitoring = {"prometheus", "grafana", "postgres-exporter", "node-exporter"}
for name in business:
    dependencies = set(services[name].get("depends_on", {}))
    assert not dependencies.intersection(monitoring), f"{name} depends on monitoring: {dependencies}"
assert not set(services["prometheus"].get("depends_on", {})).intersection(business), \
    "Prometheus startup must not depend on business services"
assert services["cert-setup"]["environment"]["DNS_PROPAGATION_WAIT_SECONDS"] == "20"
assert services["cert-setup"]["entrypoint"] == ["/bin/sh", "/opt/fkit/certbot/setup.sh"]
assert services["cert-renew"]["entrypoint"] == ["/bin/sh", "/opt/fkit/certbot/renew.sh"]

published = {name: service.get("ports", []) for name, service in services.items() if service.get("ports")}
assert {port["published"] for port in published["proxy"]} == {"80", "443"}
assert published["grafana"][0]["host_ip"] == "127.0.0.1"
assert not monitoring.difference({"grafana"}).intersection(published), "Prometheus/exporter ports must stay private"
assert not {"analytics", "generator", "postgres", "web"}.intersection(published)

nginx = (ROOT / "nginx/default.conf").read_text()
tls = (ROOT / "nginx/tls.conf.template").read_text()
for text in (nginx, tls):
    for service in ("analytics", "generator"):
        assert f"proxy_pass http://{service}:8080/;" in text
        assert f"location = /api/{service}/actuator/prometheus {{ return 404; }}" in text
    assert "proxy_set_header Authorization $http_authorization;" in text
    assert "proxy_set_header X-Trace-Id $http_x_trace_id;" in text

prometheus = (ROOT / "observability/prometheus/prometheus.yml").read_text()
assert "scrape_interval: 15s" in prometheus
for target in ("analytics:8080", "generator:8080", "postgres-exporter:9187", "node-exporter:9100"):
    assert target in prometheus

dashboards = list((ROOT / "observability/grafana/dashboards").glob("*.json"))
assert len(dashboards) == 6, f"expected six provisioned dashboards, found {len(dashboards)}"
for dashboard in dashboards:
    json.loads(dashboard.read_text())

print("Runtime contract checks passed: private targets, independent business services, routes, trace/auth forwarding, and six dashboards.")
