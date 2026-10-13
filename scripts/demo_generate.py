#!/usr/bin/env python3
"""Fills the demo enterprises with telemetry through the public Generator API.

The analytics release 015-demo-enterprises seeds two demo enterprises and their
DISABLED generator scenarios. This script activates the scenarios, generates the
history from the machines' coverage start up to now (one historical run at a
time, as the generator allows) and then keeps every line alive with an endless
realtime run. It is safe to re-run: scenarios that already have a realtime run
are left alone, and a stopped stand only gets its gap back-filled.

    python3 scripts/demo_generate.py --url https://bi.kitexp.ru --username <bootstrap>
    python3 scripts/demo_generate.py --live-alarm      # overheat show on the homogenizer

Credentials come from FKIT_DEMO_USERNAME/FKIT_DEMO_PASSWORD, then from the
FKIT_BOOTSTRAP_* variables that `infisical run --path=/github-actions` provides on
the Dev host, and are asked interactively otherwise; the password is never
printed. Only the standard library is used.
"""
import argparse
import datetime as dt
import getpass
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENTERPRISES = ("DEMO_COSMETICS", "DEMO_WAREHOUSE")
LOOP_SCENARIOS = ("DEMO_PREPARATION", "DEMO_JAR_LINE", "DEMO_BOTTLE_LINE", "DEMO_TUBES_LINE", "DEMO_WAREHOUSE")
LIVE_SCENARIO = "DEMO_LIVE_ALARM"
LIVE_HOST_SCENARIO = "DEMO_PREPARATION"
ACTIVE_RUN = {"SCHEDULED", "QUEUED", "RUNNING", "STOP_REQUESTED"}
TERMINAL_RUN = {"COMPLETED", "STOPPED", "CANCELLED", "FAILED"}
# Leave a margin behind "now": historical runs must end no later than database time.
HISTORY_END_MARGIN = dt.timedelta(seconds=60)
# Gaps shorter than the machines' offline threshold are not worth a historical run.
MIN_GAP = dt.timedelta(minutes=2)


class ApiError(Exception):
    def __init__(self, status, body):
        self.status, self.body = status, body if isinstance(body, dict) else {}
        message = self.body.get("message") or f"HTTP {status}"
        fields = "; ".join(f"{f.get('path')}: {f.get('message')}" for f in self.body.get("fieldErrors") or [])
        super().__init__(f"{message} ({self.body.get('code', status)}){' — ' + fields if fields else ''}")


def log(message):
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def parse_instant(value):
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    head, sep, tail = value.partition(".")
    if sep:  # normalise any fraction length to microseconds for older Pythons
        digits = "".join(c for c in tail if c.isdigit())
        value = f"{head}.{(digits + '000000')[:6]}{tail[len(digits):]}"
    return dt.datetime.fromisoformat(value).astimezone(dt.timezone.utc)


def iso(moment):
    return moment.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def count(value):
    return f"{value or 0:,}".replace(",", " ")


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


class Api:
    def __init__(self, analytics, generator, username, password, timeout=60):
        self.analytics, self.generator = analytics.rstrip("/"), generator.rstrip("/")
        self.username, self.password, self.timeout = username, password, timeout
        self.token = None

    def login(self):
        body = self._request("POST", f"{self.analytics}/auth/login",
                             {"username": self.username, "password": self.password}, auth=False)
        self.token = body["accessToken"]

    def call(self, method, service, path, body=None, query=None, headers=None):
        base = self.analytics if service == "analytics" else self.generator
        url = f"{base}{path}"
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None}, doseq=True)
        for attempt in range(1, 6):
            try:
                return self._request(method, url, body, headers=headers)
            except ApiError as error:
                if error.status == 401 and attempt == 1:  # JWT lives 30 minutes; the run takes longer
                    self.login()
                    continue
                if error.status in (429, 502, 503, 504) and attempt < 5:
                    time.sleep(5 * attempt)
                    continue
                raise
            except urllib.error.URLError as error:
                if attempt == 5:
                    raise
                log(f"сеть недоступна ({error.reason}), повтор через {5 * attempt} с")
                time.sleep(5 * attempt)
        raise RuntimeError("unreachable")

    def _request(self, method, url, body=None, auth=True, headers=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if auth:
            request.add_header("Authorization", f"Bearer {self.token}")
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                parsed = json.loads(raw) if raw else {}
            except ValueError:
                parsed = {}
            raise ApiError(error.code, parsed) from None


class Demo:
    def __init__(self, api, args):
        self.api, self.args = api, args
        self.enterprises, self.scenarios = {}, {}

    # ------------------------------------------------------------------ discovery
    def discover(self):
        page = self.api.call("GET", "analytics", "/enterprises", query={"status": "ACTIVE", "size": 200})
        for item in page.get("items", []):
            if item["code"] in ENTERPRISES:
                self.enterprises[item["code"]] = item["id"]
        missing = [code for code in ENTERPRISES if code not in self.enterprises]
        if missing:
            raise SystemExit(f"Нет активных демо-предприятий {', '.join(missing)}: проверьте, что analytics "
                             "с релизом 015-demo-enterprises раскатан на стенд.")
        for enterprise in self.enterprises.values():
            for status in ("ACTIVE", "DISABLED"):
                page = self.api.call("GET", "generator", "/scenarios",
                                     query={"enterpriseId": enterprise, "status": status, "size": 200})
                for item in page.get("items", []):
                    self.scenarios[item["code"]] = item
        missing = [code for code in LOOP_SCENARIOS + (LIVE_SCENARIO,) if code not in self.scenarios]
        if missing:
            raise SystemExit(f"Не найдены демо-сценарии {', '.join(missing)}.")

    def activate(self, code):
        scenario = self.scenarios[code]
        if scenario["status"] == "ACTIVE":
            return
        if self.args.dry_run:
            log(f"{code}: будет активирован")
            return
        self.api.call("PUT", "generator", f"/scenarios/{scenario['id']}/status", {"status": "ACTIVE"})
        scenario["status"] = "ACTIVE"
        log(f"{code}: сценарий активирован")

    def runs(self, code):
        scenario = self.scenarios[code]
        items, cursor = [], None
        while True:
            page = self.api.call("GET", "generator", "/runs", query={
                "enterpriseId": scenario["enterpriseId"], "scenarioId": scenario["id"], "limit": 100, "cursor": cursor})
            items += page.get("items", [])
            cursor = page.get("nextCursor")
            if not cursor:
                return items

    def active_realtime(self, code):
        return next((r for r in self.runs(code) if r["mode"] == "REALTIME" and r["status"] in ACTIVE_RUN), None)

    def generated_through(self, code):
        """End of the telemetry this scenario already produced (exclusive), or None."""
        latest = None
        for run in self.runs(code):
            moment = None
            if run["mode"] == "HISTORICAL" and run["status"] == "COMPLETED":
                moment = parse_instant(self.run(run["id"]).get("eventTo"))
            elif (run.get("progress") or {}).get("generatedThrough"):
                # A realtime tick or a stopped chunk already wrote this instant.
                moment = parse_instant(run["progress"]["generatedThrough"]) + dt.timedelta(seconds=1)
            if moment and (latest is None or moment > latest):
                latest = moment
        return latest

    def coverage_from(self, code):
        detail = self.api.call("GET", "generator", f"/scenarios/{self.scenarios[code]['id']}")
        starts = [parse_instant(self.api.call("GET", "analytics", f"/machines/{t['machineId']}").get("coverageFrom"))
                  for t in detail["machineTargets"]]
        if any(start is None for start in starts):
            raise SystemExit(f"{code}: у машин сценария нет начала покрытия — они не активированы в analytics.")
        return max(starts)

    def run(self, run_id):
        return self.api.call("GET", "generator", f"/runs/{run_id}")

    # ------------------------------------------------------------------ runs
    def start_run(self, code, body):
        body = {"scenarioId": self.scenarios[code]["id"], **body}
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:24]
        key = f"demo-{body['mode'].lower()}-{fingerprint}"
        body.setdefault("randomSeed", int(fingerprint[:12], 16))
        while True:
            try:
                return self.api.call("POST", "generator", "/runs", body, headers={"Idempotency-Key": key})
            except ApiError as error:
                if error.body.get("code") == "HISTORICAL_CAPACITY_BUSY":
                    log("генератор занят другим историческим прогоном, жду 30 с")
                    time.sleep(30)
                    continue
                raise

    def wait(self, code, run_id, label):
        last_report = 0.0
        while True:
            run = self.run(run_id)
            progress = run.get("progress") or {}
            if run["status"] in TERMINAL_RUN:
                if run["status"] != "COMPLETED":
                    failure = run.get("failure") or {}
                    raise SystemExit(f"{code}: {label} завершился со статусом {run['status']} "
                                     f"{failure.get('code', '')} {failure.get('message', '')}".rstrip())
                log(f"{code}: {label} завершён, записано {count(progress.get('writtenMeasurements'))} измерений")
                return run
            if time.monotonic() - last_report >= 60:
                percent = progress.get("progressPercent")
                done = f"{percent:.0f}%" if isinstance(percent, (int, float)) else "…"
                log(f"{code}: {label} {done}, записано {count(progress.get('writtenMeasurements'))}")
                last_report = time.monotonic()
            time.sleep(self.args.poll_seconds)

    def backfill(self, code):
        start = max(filter(None, (self.coverage_from(code), self.generated_through(code))))
        for _ in range(3):  # history, then short top-ups for the minutes the history itself took
            end = now() - HISTORY_END_MARGIN
            if end - start < MIN_GAP:
                return
            hours = (end - start).total_seconds() / 3600
            if self.args.dry_run:
                log(f"{code}: будет сгенерирована история {iso(start)} → {iso(end)} ({hours:.1f} ч)")
                return
            log(f"{code}: история {iso(start)} → {iso(end)} ({hours:.1f} ч)")
            run = self.start_run(code, {"mode": "HISTORICAL", "from": iso(start), "to": iso(end)})
            self.wait(code, run["id"], "исторический прогон")
            start = end

    def start_realtime(self, code):
        if self.args.dry_run:
            log(f"{code}: будет запущен бесконечный realtime-прогон")
            return None
        run = self.start_run(code, {"mode": "REALTIME", "randomSeed": int(time.time())})
        log(f"{code}: realtime-прогон запущен ({run['id']})")
        return run

    # ------------------------------------------------------------------ commands
    def fill(self):
        for code in LOOP_SCENARIOS + (LIVE_SCENARIO,):
            self.activate(code)
        for code in LOOP_SCENARIOS:
            running = self.active_realtime(code)
            if running:
                log(f"{code}: realtime уже идёт ({running['id']}), пропускаю")
                continue
            if not self.args.no_backfill:
                self.backfill(code)
            self.start_realtime(code)
        log("Готово. Аналитика досчитает интервалы и KPI за несколько минут после последней записи.")

    def live_alarm(self):
        self.activate(LIVE_SCENARIO)
        host = self.active_realtime(LIVE_HOST_SCENARIO)
        if host and not self.args.dry_run:
            log(f"{LIVE_HOST_SCENARIO}: останавливаю realtime на время показа")
            self.api.call("POST", "generator", f"/runs/{host['id']}/stop")
            while self.run(host["id"])["status"] not in TERMINAL_RUN:
                time.sleep(2)
        if self.args.dry_run:
            log(f"{LIVE_SCENARIO}: будет запущен на 11 минут, затем {LIVE_HOST_SCENARIO} вернётся в realtime")
            return
        run = self.start_realtime(LIVE_SCENARIO)
        log("Сценарий: 2 мин норма → 3 мин рост температуры → 4 мин авария → 2 мин пуск. "
            "Остальные машины участка эти 11 минут без связи.")
        self.wait(LIVE_SCENARIO, run["id"], "живой показ")
        self.start_realtime(LIVE_HOST_SCENARIO)


def main():
    parser = argparse.ArgumentParser(description="Генерация телеметрии для демо-предприятий FKIT BI")
    parser.add_argument("--url", default=os.environ.get("FKIT_DEMO_URL", "https://bi.kitexp.ru"),
                        help="публичный адрес стенда (по умолчанию https://bi.kitexp.ru)")
    parser.add_argument("--analytics-url", help="базовый URL Analytics API, по умолчанию <url>/api/analytics/api/v1")
    parser.add_argument("--generator-url", help="базовый URL Generator API, по умолчанию <url>/api/generator/api/v1")
    parser.add_argument("--username", default=os.environ.get("FKIT_DEMO_USERNAME") or os.environ.get("FKIT_BOOTSTRAP_USERNAME"),
                        help="логин (или FKIT_DEMO_USERNAME / FKIT_BOOTSTRAP_USERNAME)")
    parser.add_argument("--no-backfill", action="store_true", help="не догенерировать историю, только запустить realtime")
    parser.add_argument("--live-alarm", action="store_true", help="живой показ аварии на гомогенизаторе")
    parser.add_argument("--dry-run", action="store_true", help="показать план без изменений")
    parser.add_argument("--poll-seconds", type=float, default=10.0, help=argparse.SUPPRESS)
    args = parser.parse_args()

    username = args.username or input("Логин: ").strip()
    password = os.environ.get("FKIT_DEMO_PASSWORD") or os.environ.get("FKIT_BOOTSTRAP_PASSWORD") or getpass.getpass("Пароль: ")
    base = args.url.rstrip("/")
    api = Api(args.analytics_url or f"{base}/api/analytics/api/v1",
              args.generator_url or f"{base}/api/generator/api/v1", username, password)
    try:
        api.login()
        demo = Demo(api, args)
        demo.discover()
        demo.live_alarm() if args.live_alarm else demo.fill()
    except ApiError as error:
        raise SystemExit(f"Ошибка API: {error}") from None
    except KeyboardInterrupt:
        raise SystemExit("Прервано. Запущенные прогоны продолжают работать в генераторе; "
                         "повторный запуск скрипта продолжит с места остановки.") from None


if __name__ == "__main__":
    main()
