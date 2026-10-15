#!/usr/bin/env python3
"""Fast static integration checks for Compose, proxy, and provisioning contracts."""

import json
import os
import subprocess
from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parent.parent
config = subprocess.run(
    ["docker", "compose", "--env-file", ".env.example", "config", "--format", "json"],
    cwd=ROOT,
    check=True,
    capture_output=True,
    text=True,
)
services = json.loads(config.stdout)["services"]
proxy_ip = services["proxy"]["networks"]["default"]["ipv4_address"]
assert services["analytics"]["environment"]["FKIT_TRUSTED_PROXY_CIDRS"] == f"{proxy_ip}/32"

business = {"postgres", "analytics", "generator", "web"}
monitoring = {"prometheus", "grafana", "postgres-exporter", "node-exporter"}
assert services["infisical"]["image"] == "infisical/infisical:v0.165.16"
assert services["infisical"]["environment"]["TELEMETRY_ENABLED"] == "false"
assert services["infisical"]["environment"]["ANNOUNCEMENTS_ENABLED"] == "false"
assert services["infisical"]["environment"]["OTEL_TELEMETRY_COLLECTION_ENABLED"] == "false"
assert "ports" not in services["infisical"]
assert services["infisical"]["healthcheck"]["test"] == ["CMD", "curl", "-fsS", "http://localhost:8080/api/status"]
assert "ports" not in services["infisical-postgres"]
assert "ports" not in services["infisical-redis"]
assert "infisical-data" in services["infisical-postgres"]["networks"]
assert set(services["infisical-postgres"]["networks"]) == {"infisical-data"}
assert set(services["infisical-redis"]["networks"]) == {"infisical-data"}
assert services["infisical-redis"]["healthcheck"]["test"] == ["CMD", "redis-cli", "ping"]
assert services["infisical"]["depends_on"]["infisical-redis"]["condition"] == "service_healthy"
assert "infisical-edge" in services["proxy"]["networks"]
assert "infisical-edge" in services["infisical"]["networks"]
for name in business:
    dependencies = set(services[name].get("depends_on", {}))
    assert not dependencies.intersection(monitoring), f"{name} depends on monitoring: {dependencies}"
assert not set(services["prometheus"].get("depends_on", {})).intersection(business), \
    "Prometheus startup must not depend on business services"
assert services["cert-setup"]["environment"]["DNS_PROPAGATION_WAIT_SECONDS"] == "20"
assert services["cert-setup"]["environment"]["CERTBOT_CHALLENGE"] == "dns-01"
assert services["cert-setup"]["entrypoint"] == ["/bin/sh", "/opt/fkit/certbot/setup.sh"]
assert services["cert-renew"]["entrypoint"] == ["/bin/sh", "/opt/fkit/certbot/renew.sh"]
for service_name in ("cert-setup", "cert-renew", "proxy"):
    volume_targets = {volume["target"] for volume in services[service_name]["volumes"]}
    assert "/var/www/certbot" in volume_targets, f"{service_name} is missing the ACME webroot"

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
        assert f"location ^~ /api/{service}/actuator/prometheus {{ return 404; }}" in text
    assert "proxy_set_header Authorization $http_authorization;" in text
    assert "proxy_set_header X-Trace-Id $http_x_trace_id;" in text
assert "server_name bi.kitexp.ru api.bi.kitexp.ru generator.bi.kitexp.ru grafana.bi.kitexp.ru secrets.kitexp.ru;" in tls
assert "server_name grafana.bi.kitexp.ru;" in tls
assert "set $grafana_upstream grafana:3000;" in tls
assert "proxy_pass http://$grafana_upstream;" in tls
assert "grafana" not in nginx, "Grafana is published only through the TLS listener"
assert services["grafana"]["environment"]["GF_SERVER_ROOT_URL"] == "https://grafana.bi.kitexp.ru/"
assert "server_name secrets.kitexp.ru;" in tls
assert "set $infisical_upstream infisical:8080;" in tls
assert "proxy_pass http://$infisical_upstream;" in tls
assert "resolver 127.0.0.11 valid=10s;" in tls
assert "server_name api.bi.kitexp.ru;" in tls
assert "server_name generator.bi.kitexp.ru;" in tls
assert tls.count("location ^~ /actuator/prometheus { return 404; }") == 2
assert "proxy_pass http://analytics:8080;" in tls
assert "proxy_pass http://generator:8080;" in tls
assert tls.count("proxy_set_header X-Original-URI $request_uri;") == 2
for text in (nginx, tls):
    assert "location ^~ /.well-known/acme-challenge/" in text

infra_workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
assert "id-token" not in infra_workflow.get("permissions", {})
assert "id-token" not in infra_workflow["jobs"]["verify"].get("permissions", {})

workflow_roots = {"infra": ROOT}
workflow_root_overrides = json.loads(os.environ.get("FKIT_BI_WORKFLOW_ROOTS", "{}"))
workflow_roots.update({name: Path(path) for name, path in workflow_root_overrides.items()})
in_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
if workflow_root_overrides:
    required_repositories = {"infra", "analytics", "generator", "web"}
elif in_github_actions:
    required_repositories = {"infra", "analytics", "generator"}
else:
    required_repositories = {"infra", "analytics", "generator", "web"}

for repository in ("analytics", "generator", "web"):
    if in_github_actions and not workflow_root_overrides and repository == "web":
        continue  # Infra CI intentionally checks out analytics and generator, but not web.
    if repository in workflow_roots:
        continue
    repository_root = ROOT.parent / f"fkit-bi-{repository}"
    if not repository_root.exists():
        repository_root = ROOT / ".ci" / f"fkit-bi-{repository}"
    if not repository_root.exists():
        if repository in required_repositories:
            raise AssertionError(f"missing required workflow checkout for {repository}")
        continue
    workflow_roots[repository] = repository_root

missing_repositories = required_repositories.difference(workflow_roots)
assert not missing_repositories, f"missing required workflow checkouts: {sorted(missing_repositories)}"

for repository, repository_root in workflow_roots.items():
    workflow = yaml.safe_load((repository_root / ".github/workflows/ci.yml").read_text())
    jobs = workflow["jobs"]
    deploy_job_name = "deliver-dev" if repository == "infra" else "deploy-dev"
    deploy_job = jobs[deploy_job_name]
    expected_path = f"/github-actions/{repository}"
    assert "id-token" not in workflow.get("permissions", {}), repository
    for job_name, job in jobs.items():
        if job_name != deploy_job_name:
            assert "id-token" not in job.get("permissions", {}), f"{repository}/{job_name}"
    assert deploy_job["permissions"]["id-token"] == "write", repository
    expected_gate = "github.event_name == 'push' && github.ref == 'refs/heads/develop'"
    if repository != "infra":
        expected_gate += " && vars.FKIT_BI_DEV_DEPLOY_ENABLED == 'true'"
    assert deploy_job.get("if") == expected_gate, repository
    infisical_steps = [step for step in deploy_job["steps"]
                       if step.get("uses", "").startswith("Infisical/secrets-action@")]
    assert len(infisical_steps) == 1, repository
    action = infisical_steps[0]
    inputs = action.get("with", {})
    assert action["uses"] == "Infisical/secrets-action@8a06c1bdcd5b8635d510c52d4b57a92c1ccef785", repository
    assert inputs["method"] == "oidc", repository
    assert inputs["identity-id"] == "${{ vars.FKIT_BI_INFISICAL_IDENTITY_ID }}", repository
    assert inputs["oidc-audience"] == "https://github.com/FKIT-BI", repository
    assert inputs["domain"] == "https://secrets.kitexp.ru", repository
    assert inputs["project-slug"] == "${{ vars.FKIT_BI_INFISICAL_PROJECT_SLUG }}", repository
    assert inputs["env-slug"] == "dev", repository
    assert inputs["secret-path"] == expected_path, repository
    assert not any("secrets.FKIT_BI_DEV_SSH_PRIVATE_KEY" in json.dumps(step, sort_keys=True)
                   for step in deploy_job["steps"]), repository
    if repository != "infra":
        assert "GH_TOKEN" not in deploy_job.get("env", {}), repository
        clone_step = next(step for step in deploy_job["steps"]
                          if "gh repo clone FKIT-BI/fkit-bi-infra" in step.get("run", ""))
        assert clone_step.get("env", {}).get("GH_TOKEN") == "${{ secrets.FKIT_BI_GITHUB_TOKEN }}", repository

prometheus = (ROOT / "observability/prometheus/prometheus.yml").read_text()
assert "scrape_interval: 15s" in prometheus
for target in ("analytics:8080", "generator:8080", "postgres-exporter:9187", "node-exporter:9100"):
    assert target in prometheus

dashboards = list((ROOT / "observability/grafana/dashboards").glob("*.json"))
assert len(dashboards) == 6, f"expected six provisioned dashboards, found {len(dashboards)}"
for dashboard in dashboards:
    json.loads(dashboard.read_text())

print(f"Runtime contract checks passed for {', '.join(workflow_roots)}: private targets, isolated OIDC, paths, routes, and six dashboards.")
