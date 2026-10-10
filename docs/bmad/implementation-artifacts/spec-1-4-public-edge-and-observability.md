---
title: '1.4 — Публичная точка входа и наблюдаемость'
type: 'feature'
created: '2026-10-10'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'eaaf7359e3f100858b97856baf9c370d9b322309'
context:
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/epic-1-context.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-security-audit/security-and-deployment.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-observability-runtime/SPEC.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-observability-runtime/runtime-topology.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-observability-runtime/metrics-catalog.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-observability-runtime/dashboards-and-alerts.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Стенд пока доступен через временный HTTP proxy и не имеет воспроизводимого мониторинга.

**Approach:** Объединить Nginx edge и настроенный мониторинг в стандартном запуске Compose; TLS-режим выбирается явно, отказ мониторинга не влияет на бизнес-сервисы.

## Boundaries & Constraints

**Always:** Только Nginx публикует порты 80/443; backend, БД и мониторинг закрыты. Сохранить HTTP-доступ по IP; маршрутизировать `bi.kitexp.ru` и поддомены одного уровня по путям. По умолчанию `TLS_MODE=off` для разработки; `public` использует Certbot DNS-01/Yandex hooks для apex+wildcard, `self-signed` создаёт постоянный демонстрационный сертификат. Public никогда не переключается на self-signed: ошибка первичного выпуска блокирует TLS-запуск; при renewal сохраняется текущий сертификат и записывается ошибка. DNS и другие secrets передаются извне. В TLS-режимах HTTP домена перенаправляется на HTTPS, IP остаётся HTTP. Сохранять Authorization и передавать ограниченный traceId. Логи приложений — JSON без secrets/payloads. Compose запускает Prometheus, Grafana и оба exporter; scrape=15s, retention=7d/1GB; provisioning datasource, шести dashboards и rules. Grafana публикуется только на loopback. Приложения отдают Micrometer metrics. Мониторинг не зависит от business services и не входит в readiness.

**Never:** Не выпускать production certificate, менять Yandex DNS или выполнять deploy; hooks тестировать без production credentials. Не добавлять Loki, Tempo, cAdvisor, Alertmanager, внешние уведомления, отдельный monitoring host/DB roles, высококардинальные labels или изменения API/DB/auth Story 1.3.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Ошибка |
|---|---|---|---|
| TLS off | Локальный Compose без DNS credentials | HTTP по IP/domain и маршруты API доступны | Certbot не запускается |
| TLS public | Настроены zone/key secrets | DNS-01 выдаёт/обновляет apex+wildcard cert; Nginx его перечитывает | Без fallback; ошибка первичного выпуска не поднимает TLS |
| TLS self-signed | Нет публичного DNS secret | Автоматически созданный постоянный cert; IP доступен по HTTP | Не скрывать предупреждение о недоверенном cert |
| Monitoring down | Prometheus/Grafana остановлены | Analytics, Generator, PostgreSQL и API остаются доступны | Readiness/startup не зависят от мониторинга |
| Trace/log | Запрос через Nginx | Один ограниченный traceId в response и JSON logs | Не принимать невалидный trace клиента |

</frozen-after-approval>

## Code Map

- `compose.yaml`, `nginx/default.conf`, `scripts/validate.sh` — edge/маршруты; сохранить Authorization и доверенный proxy Story 1.3.
- `spec-security-audit/security-and-deployment.md` — hostnames, TLS modes, DNS hooks, ports и secrets.
- `spec-observability-runtime/` — topology, metrics, labels, dashboards и alerts; оставить общий DB account.
- POM/config/TraceIdFilter обоих backend — закрытые metrics, JSON logs и безопасный trace; сохранить JWT/readiness.
- `docs/dev-deployment.md`, `README.md`, `.env.example` — параметры deployment; без deploy/реального ACME.

## Tasks & Acceptance

**Execution:**
- [x] `compose.yaml`, `nginx/`, `certbot/` — опубликовать нужные ports, маршрутизировать IP/domain, настроить TLS modes/Yandex hooks/renewal и изолированный мониторинг.
- [x] `observability/` — настроить scrape/rules, exporters, шесть dashboards, retention 7d/1GB и bounded labels.
- [x] POM/config обоих backend — включить закрытые Prometheus metrics и JSON logs; сохранить auth/readiness.
- [x] Infra tests/docs — проверить mock DNS hooks, маршруты, targets/provisioning и отказ мониторинга; описать ports/secrets.

**Acceptance Criteria:**
- Given каждый TLS mode, when запускается Compose, then HTTP-маршруты IP/domain доступны и применяется нужный TLS; public renewal не делает fallback, self-signed переживает рестарт.
- Given стандартный Compose, when поднимается мониторинг, then scrape targets, datasource, шесть dashboards и rules доступны только внутри сети.
- Given мониторинг остановлен, when проверяются readiness/API/telemetry, then business services работают, а response/logs содержат безопасный traceId без secrets.

## Implementation Notes

Для тестов Yandex DNS эмулируется; credentials для реального ACME передаст оператор. Сохранить общий DB account и закрытый мониторинг.

## Spec Change Log

## Review Triage Log

| ID | Вердикт | Маршрут | Проверенное основание |
|---|---|---|---|
| B1 | medium | defer | Custom domain metrics действительно ещё не существуют, но их источники — ingestion/calculation capabilities будущих stories; Story 1.4 не должна изобретать ещё отсутствующие операции. |
| B2 | medium | patch | `prometheus.depends_on` ждёт оба приложения и exporter, поэтому initial monitoring startup блокируется недоступной business/DB цепочкой вопреки независимости monitoring. |
| B3 | medium | patch | В rules отсутствует отдельный alert на рост `pg_stat_database_deadlocks`, явно требуемый companion spec. |
| B4 | medium | patch | 5xx ratio имеет только `clamp_min`, поэтому единичный 5xx при почти нулевом traffic способен держать alert; добавляется gate минимум 100 запросов за 5 минут. |
| B5 | medium | patch | Promtool tests покрывают только dropped/projection; обязательный сценарий `PrometheusTargetDown` отсутствует. |
| B6 | medium | patch | Ingestion dashboard не содержит generation measurement rate, sequence gaps, active runs, schedule lag и явные write errors, перечисленные в dashboard contract. |
| B7 | medium | patch | API dashboard не содержит slow-routes и active/in-flight HTTP panels, перечисленных в dashboard contract. |
| B8 | medium | patch | PostgreSQL dashboard показывает deadlocks, но не lock/activity view, требуемый dashboard contract. |
| B9 | medium | defer | Live telemetry batch и рост custom metrics нельзя проверить до появления ingestion/projection operations; это реальный future verification gate, не изменение Story 1.4. |
| B10 | low | patch | Evidence утверждает, что live Compose outage test не выполнялся, хотя `validate.sh` запускает именно такой smoke test; запись будет приведена к фактической проверке. |
| B11 | medium | patch | После `compose run cert-setup` запуск `cert-renew` с dependencies создаёт regular `cert-setup` второй раз; deploy будет стартовать renew через `--no-deps`. |
| B12 | high | patch | Self-signed files занимают Certbot `live/bi.kitexp.ru`; при переходе на public это может заблокировать managed lineage. Режимы будут разведены по каталогам с миграцией legacy files. |
| B13 | medium | patch | `DNS_PROPAGATION_WAIT_SECONDS` не передаётся в initial `cert-setup`, поэтому operator override игнорируется. |
| B14 | false | reject | `HUP` отправляется master-процессу Nginx; сам master перечитывает и валидирует config/certificate до замены workers и сохраняет старых workers при ошибке. Отдельный pre-check из certbot container не является отсутствующим guard. |
| B15 | medium | patch | Compose имеет известный default Grafana password, а deployment не отклоняет placeholder из example config. |
| B16 | medium | patch | `test_renew.py` проверяет несвязанный fixture и не доказывает сохранение Certbot lineage; тест будет проверять failure/no-reload и отдельный success/reload path без ложного claim. |
| V1 | medium | patch | Edge test сам создаёт `tls.conf` и обходит proxy startup branch из Compose; общий startup script станет единственным исполняемым путём для Compose и теста. |
| V2 | medium | patch | Нет успешного renewal test, который доказывает вызов reload hook; добавляется управляемый HUP test. |
| V3 | medium | patch | Public `certbot certonly` command не исполняется с fake Certbot; добавляется проверка apex/wildcard/hooks и exit propagation. |
| V4 | medium | patch | Backend tests проверяют только JVM metric и не защищают HTTP histogram/common application tag, используемые dashboard и alert. |
| V5 | medium | patch | Одиннадцать alert rules имеют только syntax-check; добавляются promtool firing/non-firing cases для каждого distinct rule. |
| V6 | medium | patch | Grafana provisioning проверяет только количество JSON dashboards; smoke test будет отправлять все panel expressions в Prometheus API и проверять runtime series. |
| V7 | medium | patch | Yandex tests полностью mock-ят token/API/polling; добавляются tests JWT request, pagination, polling success/error/timeout и HTTP error. |
| V8 | medium | patch | Повторно подтверждён пропущенный `DNS_PROPAGATION_WAIT_SECONDS` у initial setup; исправляется вместе с B13. |
| E1 | high | patch | Повторно подтверждён конфликт self-signed/public lineage; исправляется вместе с B12. |
| E2 | medium | patch | Self-signed setup принимает любые два non-empty файла, включая corrupt/mismatched pair; добавляется cryptographic validation и regeneration. |
| E3 | medium | patch | Повторно подтверждён ignored propagation override; исправляется вместе с B13/V8. |
| E4 | medium | patch | Yandex record listing читает только первую страницу до 1000 RRsets и может потерять существующий challenge RRset; добавляется pagination. |
| E5 | low | patch | Poll request с фиксированным 20-second timeout может выйти за общий 60-second deadline; remaining deadline будет передаваться в HTTP timeout. |
| E6 | low | reject | Race между освобождением ephemeral port и bind Grafana возможен, но крайне редок; retry-state добавляет непропорциональную сложность локальному smoke test. |
| E7 | false | reject | Loopback publication — прямо требуемая граница: host-local доступ допустим, внешний доступ закрыт bind на `127.0.0.1`. |
| B17 | medium | patch | Review diff включал только что созданные тестами `.pyc` файлы; это локальные артефакты, они удалены из рабочей копии. |
| B18 | medium | patch | Перемещение Certbot `live` каталога ломает относительные ссылки на `archive`; перед перемещением текущие certificate/key сохраняются как обычные файлы. |
| B19 | medium | patch | Self-signed certificate мог быть корректной парой, но с чужим SAN или истекшим сроком; setup теперь проверяет срок и оба требуемых hostname и пересоздаёт неподходящую пару. |
| B20 | false | reject | `scripts/validate.sh` делает дополнительную проверку TLS-конфига напрямую, но основной `scripts/test-edge-http.py` запускает общий `nginx/start.sh`, используемый Compose; startup mode покрыт. |
| B21 | false | reject | Probe `docker compose run cert-setup` с несуществующим key path создал и запустил контейнер; Compose не останавливается до TLS_MODE=off, отдельный runtime-дефект был в entrypoint и исправлен ниже. |
| B22 | false | reject | `analytics-bootstrap` включён только профилем `bootstrap`, поэтому обычный `docker compose up -d` его не запускает. |
| B23 | low | reject | Pull monitoring images может мешать редкому offline deploy, но обычный delivery ожидает получение обновляемых образов; управление registry cache добавило бы отдельную политику. |
| B24 | false | reject | План явно исключает Alertmanager и внешние уведомления; правило остаётся доступным в Prometheus UI и не обещает доставку alert. |
| B25 | medium | patch | Пока domain instrumentation отсутствует, пустые ingestion/generation панели могли выглядеть как idle data; dashboard теперь объясняет, что метрики относятся к будущим story и графики пока не показательны. |
| B26 | medium | patch | Проверка placeholder читала сырой `.env` и пропускала Compose-кавычки/interpolation; теперь сравнивается значение, разрешённое самим Compose. |
| B27 | high | patch | `certbot/certbot` задаёт ENTRYPOINT `certbot`, из-за чего `cert-setup` получал shell-команду как аргументы Certbot и deployment не мог завершить setup; Compose задаёт прямой shell entrypoint и проверяет его runtime-запуском. |
| V9 | medium | patch | Проверки публичных routes не запрашивали защищённые metrics URL через запущенный Nginx; edge test теперь проверяет HTTP 404 для обоих backend в HTTP и HTTPS TLS modes. |
| E8 | medium | patch | Валидная, совпадающая с ключом self-signed пара могла быть уже просроченной; setup теперь пересоздаёт сертификат с истечением менее чем через сутки. |
| E9 | medium | patch | `live` symlinks становятся broken при переносе; копирование resolved certificate/key в обычные backup-файлы до переноса сохраняет текущий материал. |
| E10 | false | reject | В non-public probe Compose создаёт контейнер и запускает команду даже с отсутствующим внешним key path; раннего отказа до обработки режима не наблюдалось. |
| E11 | medium | patch | Цитированный placeholder мог пройти проверку через literal grep; Compose теперь разрешает quoting и interpolation перед сравнением. |

## Design Notes

### Certbot DNS hook

Auth hook добавляет challenge TXT; cleanup удаляет только его значение. IAM token создаётся из внешнего service-account key; key/zone ID не встраиваются в image.

### Review hardening

Self-signed certificate хранится отдельно от Certbot public lineage; перед перемещением legacy unmanaged live-каталога текущие certificate/key сохраняются обычными backup-файлами. Certbot Compose services задают shell entrypoint явно; API 5xx alert использует minimum traffic gate 100 requests/5m. Monitoring services не имеют startup dependency на business services. Grafana deployment сравнивает password после Compose resolution.

## Verification

**Commands:**
- `./scripts/validate.sh` в `fkit-bi-infra` — успешная проверка Compose/config/scripts без deploy.
- `./mvnw -B verify` в Analytics и Generator — успешные tests; интеграционные тесты используют PostgreSQL Testcontainers.
- `promtool check config`, `promtool check rules`, `promtool test rules` — корректные конфиги и passing alert tests.

**Manual checks:** Compose setup entrypoint исполняется в `TLS_MODE=off`; edge test проверяет routes и закрытые metrics URLs во всех TLS modes; live Compose smoke подтверждает targets/dashboards и сохранение Analytics readiness/API во время остановки Prometheus и Grafana. Не выполнять live deploy/ACME.
