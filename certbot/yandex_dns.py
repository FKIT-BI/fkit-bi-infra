#!/usr/bin/env python3
"""Certbot DNS-01 hooks for Yandex Cloud DNS; only the challenge value is removed."""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


DNS_API = os.environ.get("YANDEX_DNS_API", "https://dns.api.cloud.yandex.net/dns/v1")
IAM_API = os.environ.get("YANDEX_IAM_API", "https://iam.api.cloud.yandex.net/iam/v1/tokens")
OPERATION_API = os.environ.get("YANDEX_OPERATION_API", "https://operation.api.cloud.yandex.net/operations")


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def request(url: str, token: str | None = None, body: dict | None = None, timeout: float = 20) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Yandex API returned HTTP {error.code}: {detail}") from error


def access_token() -> str:
    service_account = os.environ["YANDEX_SERVICE_ACCOUNT_ID"]
    key_id = os.environ["YANDEX_KEY_ID"]
    key_data = json.loads(Path(os.environ.get(
        "YANDEX_SERVICE_ACCOUNT_KEY_FILE", "/run/secrets/yandex-service-account-key.json"
    )).read_text())
    private_key = serialization.load_pem_private_key(key_data["private_key"].encode(), password=None)
    now = datetime.now(timezone.utc)
    header = b64url(json.dumps({"alg": "PS256", "kid": key_id, "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps({
        "iss": service_account,
        "aud": IAM_API,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }, separators=(",", ":")).encode())
    message = f"{header}.{payload}".encode()
    signature = private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=hashes.SHA256().digest_size),
        hashes.SHA256(),
    )
    result = request(IAM_API, body={"jwt": f"{header}.{payload}.{b64url(signature)}"})
    return result["iamToken"]


def challenge_record_sets(token: str, zone_id: str, record_name: str) -> list[dict]:
    base_url = f"{DNS_API}/zones/{urllib.parse.quote(zone_id, safe='')}:listRecordSets?pageSize=1000"
    matches = []
    page_token = None
    while True:
        url = base_url
        if page_token:
            url += f"&pageToken={urllib.parse.quote(page_token, safe='')}"
        result = request(url, token)
        matches.extend(item for item in result.get("recordSets", [])
                       if item.get("name") == record_name and item.get("type") == "TXT")
        page_token = result.get("nextPageToken")
        if not page_token:
            return matches


def update_record_sets(token: str, zone_id: str, additions: list[dict], deletions: list[dict]) -> None:
    url = f"{DNS_API}/zones/{urllib.parse.quote(zone_id, safe='')}:updateRecordSets"
    operation = request(url, token, {"additions": additions, "deletions": deletions})
    operation_id = operation.get("id")
    if not operation_id:
        raise RuntimeError("Yandex DNS did not return an operation id")
    deadline = time.monotonic() + 60
    while not operation.get("done") and time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        time.sleep(min(1, max(0, remaining)))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        operation = request(
            f"{OPERATION_API}/{urllib.parse.quote(operation_id, safe='')}",
            token,
            timeout=min(20, remaining),
        )
    if not operation.get("done"):
        raise RuntimeError("Yandex DNS update did not finish within 60 seconds")
    if operation.get("error"):
        raise RuntimeError(f"Yandex DNS update failed: {operation['error'].get('message', 'unknown error')}")


def modify_challenge(remove: bool) -> None:
    token_value = os.environ["CERTBOT_VALIDATION"]
    zone_id = os.environ["DNS_ZONE_ID"]
    record_name = os.environ.get("DNS_RECORD_NAME", "_acme-challenge.bi.kitexp.ru.")
    # DNS APIs represent TXT RDATA with the surrounding presentation-format quotes.
    txt_value = f'"{token_value}"'
    token = access_token()
    current_sets = challenge_record_sets(token, zone_id, record_name)
    current = current_sets[0] if current_sets else None
    values = list(current.get("data", [])) if current else []
    if remove:
        if not current or txt_value not in values:
            return
        values.remove(txt_value)
    else:
        if txt_value not in values:
            values.append(txt_value)

    new_set = {"name": record_name, "type": "TXT", "ttl": "60", "data": values}
    update_record_sets(token, zone_id, [new_set] if values else [], [current] if current else [])
    if not remove:
        time.sleep(int(os.environ.get("DNS_PROPAGATION_WAIT_SECONDS", "20")))


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"auth", "cleanup"}:
        print("usage: yandex_dns.py auth|cleanup", file=sys.stderr)
        return 2
    try:
        modify_challenge(remove=sys.argv[1] == "cleanup")
        return 0
    except Exception as error:  # Certbot needs the hook failure to abort issuance.
        print(f"Yandex DNS hook failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
