---
title: 'Публичный HTTPS и сервисные поддомены Dev'
type: 'feature'
created: '2026-10-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '763c2297b2c435f0af925bfdcdf5a461e3019640'
context:
  - 'fkit-bi-infra/docs/bmad/project-context.md'
  - 'fkit-bi-infra/docs/dev-deployment.md'
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/spec-1-4-public-edge-and-observability.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A-записи `bi.kitexp.ru`, `api.bi.kitexp.ru` и `generator.bi.kitexp.ru` уже указывают на Dev, но Nginx обслуживает их одним default vhost, поэтому API-поддомены показывают Web, а HTTPS не поднимается. Имеющаяся DNS-01 автоматизация требует Yandex Cloud DNS API, тогда как авторитетная зона размещена на `dns1/dns2.yandex.net` и нужных cloud credentials на сервере нет.

**Approach:** Добавить hostname-маршрутизацию и HTTP-01 режим Certbot с общим webroot, выпуская один сертификат с точными SAN для трёх имеющихся имён. Сохранить DNS-01/wildcard как опциональный режим, текущие path-based API на `bi.kitexp.ru` и HTTP-доступ по IP; после проверок доставить exact infra SHA, безопасно переключить private `.env` на public HTTP-01 и подтвердить живые HTTPS actuator endpoints.

## Boundaries & Constraints

**Always:** `bi.kitexp.ru` обслуживает Web и совместимые `/api/analytics/`, `/api/generator/`; `api.bi.kitexp.ru` проксирует корневые пути в Analytics, `generator.bi.kitexp.ru` — в Generator. Доменные HTTP-запросы перенаправляются на HTTPS, кроме `/.well-known/acme-challenge/`; IP остаётся доступен по HTTP. На прямых API-vhost закрыть `/actuator/prometheus`, сохранить Authorization, trace headers и исходный URI. Сертификат и ACME account живут в существующем `certbot-data`, challenge-файлы — в отдельном volume; renewal остаётся автоматическим. Переключение Dev выполняется без удаления volumes и с сохранением private secrets и application image SHA.

**Never:** Не открывать backend/DB/monitoring ports, не включать CORS-зависимый вызов API-поддоменов из Web, не удалять `certbot-data`/PostgreSQL data, не выполнять `compose down -v`, не выводить private `.env` или ключи. Ошибка выпуска сертификата не должна оставлять новый HTTPS как успешный и не должна уничтожать работающий HTTP-контур.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Web HTTPS | `https://bi.kitexp.ru/` | Web; path-based API остаются рабочими | TLS/route failure блокирует acceptance |
| Analytics hostname | `https://api.bi.kitexp.ru/actuator/health` | Analytics `200`, `status=UP` | Prometheus endpoint остаётся `404` |
| Generator hostname | `https://generator.bi.kitexp.ru/actuator/health` | Generator `200`, `status=UP` | Prometheus endpoint остаётся `404` |
| ACME bootstrap/renewal | HTTP-01 для трёх A-записей | Challenge доступен по HTTP без redirect; Certbot получает/обновляет exact-SAN cert | Certbot failure сохраняет имеющийся контур и завершается ошибкой |
| IP compatibility | `http://45.132.176.28/` и path API | HTTP `200`; HTTPS по IP не требуется | Не перенаправлять IP на домен |

</frozen-after-approval>

## Code Map

- `nginx/default.conf` — HTTP/IP fallback и ACME webroot; сохранить существующие path routes.
- `nginx/tls.conf.template` — доменный redirect, Web vhost и отдельные Analytics/Generator HTTPS vhosts.
- `nginx/start.sh` — выбирает TLS lineage; не допускать скрытого self-signed fallback.
- `compose.yaml` — передаёт challenge mode и монтирует persistent ACME webroot в proxy/setup/renew.
- `certbot/setup.sh`, `certbot/renew.sh` — существующие DNS-01 и renewal; добавить HTTP-01 exact-SAN issuance без Yandex credentials.
- `scripts/deploy-infra.sh` — exact-SHA delivery; безопасно подготовить HTTP challenge listener при первом public HTTP-01 выпуске и целево обновить TLS-настройки private `.env`.
- `.github/workflows/ci.yml` — передать несекретные Dev TLS mode/challenge/email variables в delivery.
- `scripts/test-edge-http.py`, `scripts/test-runtime-contracts.py`, `certbot/test_setup.py`, `scripts/test-delivery.sh` — зафиксировать hostname routes, ACME exception, issuance modes и delivery invariants.
- `.env.example`, `README.md`, `docs/dev-deployment.md`, `docs/bmad/project-context.md` — описать фактические URL, challenge modes и live evidence без секретов.

## Tasks & Acceptance

**Execution:**
- [x] `nginx/`, `compose.yaml` — реализовать host routing, ACME webroot и HTTP→HTTPS с IP/path compatibility.
- [x] `certbot/` — добавить проверяемый HTTP-01 exact-SAN setup, сохранив DNS-01/wildcard и renewal.
- [x] `scripts/deploy-infra.sh`, `.github/workflows/ci.yml` — сделать первый public cutover воспроизводимым и безопасно управлять только разрешёнными TLS-полями.
- [x] Infra tests — покрыть маршруты, закрытые metrics, оба challenge mode, bootstrap и отказ Certbot.
- [x] Docs/config — обновить операторский контракт и адреса.
- [x] Dev — выполнить проверки, commit/push `develop`, дождаться CI/CD, выпустить сертификат и проверить Web/actuators по HTTPS.

**Acceptance Criteria:**
- Given три опубликованные A-записи и закрытые backend ports, when exact infra SHA доставлен с public HTTP-01, then браузерно-доверенный сертификат покрывает все три имени, Web и оба actuator отвечают по целевым HTTPS URL.
- Given старый Web использует относительные API paths, when включены сервисные vhost, then `/api/analytics/` и `/api/generator/` на `bi.kitexp.ru` продолжают работать без CORS-изменений.
- Given initial issuance или renewal завершается ошибкой, when delivery/renewal обрабатывает отказ, then secrets не выводятся, volumes не удаляются, а ошибка видима и не маскируется ложным healthcheck success.

## Implementation Notes

Авторитетные NS и live DNS проверены 2026-10-11: все три имени резолвятся в `45.132.176.28`; HTTP path-based health возвращает `200/UP`. Для HTTP-01 порт 80 уже публичен. Контакт Certbot берётся из deployment variable, не коммитится.

Локальная реализация завершена: Nginx поддерживает exact-host HTTPS и совместимые path routes, Certbot — HTTP-01 exact SAN и прежний DNS-01 wildcard, delivery — целевое обновление TLS-полей и безопасный initial HTTP listener. Во время live rollout обнаружено, что BuildKit мог забрать оставшуюся часть remote Bash heredoc из stdin после `docker compose build`; сборка завершалась успешно, но команды reconcile не выполнялись. Build и listener probe теперь отсоединены от heredoc stdin; delivery test моделирует это поведение.

Live Dev подтверждён 2026-10-12: CI run [38198454137](https://github.com/FKIT-BI/fkit-bi-infra/actions/runs/38198454137) завершил verify и exact-SHA delivery успешно для `913ab9f06d10e3471f95f1fb2674519cb40f2aa3`. Сертификат выпущен в CI run [38164570249, attempt 3](https://github.com/FKIT-BI/fkit-bi-infra/actions/runs/38164570249/attempts/3). Let’s Encrypt SAN: `bi.kitexp.ru`, `api.bi.kitexp.ru`, `generator.bi.kitexp.ru`; срок действия до 2027-01-10. Web и все path/direct Analytics/Generator health endpoints возвращают `200`, actuator — `status=UP`; доменные HTTP URL возвращают `301`, IP HTTP — `200`, прямые Prometheus actuator URL — `404`. На сервере `TLS_MODE=public`, cert-renew запущен, application image SHA сохранены.

## Spec Change Log

## Review Triage Log

| ID | Finding | Verdict | Disposition |
|---|---|---|---|
| VG1 | Тест не доказывал `TLS_MODE=off` у bootstrap proxy | medium / patch | Delivery stub фиксирует окружение обоих запусков proxy; проверены `off` и финальный `public`. |
| VG2 | Одинаковые mock-ответы не выявляли перепутанные upstream | medium / patch | Mock Analytics/Generator получили разные `service`, маршруты проверяют ожидаемый сервис. |
| VG3 | HTTP-01 тест всё ещё передавал Yandex credentials | medium / patch | HTTP-01 запускается с очищенными DNS/Yandex переменными. |
| VG4 | Не проверялась связь trusted proxy CIDR с IP proxy | medium / patch | Runtime contract сравнивает CIDR Analytics с Compose IP proxy `/32`. |
| VGO1 | Non-public delivery безусловно проверял direct HTTPS | medium / patch | Direct HTTPS healthchecks выполняются только для `TLS_MODE=public`. |
| EH1 | Certbot challenge/email требовались в `off`/`self-signed` | medium / patch | Валидация и обновление этих полей ограничены public mode; добавлен preflight test. |
| EH2 | `off`/`self-signed` завершались проверкой HTTPS hostnames | medium / patch | Для non-public выполняется только базовый healthcheck public URL. |
| EH3 | Старый proxy без ACME listener мог сохраниться при готовом сертификате | medium / patch | Перед Certbot выполняется живой webroot probe; при несовпадении proxy пересоздаётся с `TLS_MODE=off`. |
| EH4 | Public mode принимал некорректный base URL | medium / patch | Public delivery требует `https://bi.kitexp.ru`. |
| EH5 | Healthcheck молча принимал два или лишние аргументы | low / patch | Разрешены только формы с 1 или 3 аргументами; malformed invocation тестируется. |
| EH6 | Exact metrics block пропускал slash/path variants | medium / patch | Блокировка сделана prefix и покрыта вариантами с завершающим `/`. |
| EH7 | Любой HTTP 2xx actuator считался healthy | medium / patch | Actuator response обязан содержать `"status":"UP"`; `DOWN` покрыт тестом. |
| BH1 | Non-public режим зависел от public-only Certbot inputs | medium / patch | Дубликат EH1; исправление и regression test применены. |
| BH2 | Non-public режим зависел от exact public HTTPS hosts | medium / patch | Дубликат EH2; проверки теперь зависят от TLS mode. |
| BH3 | Direct health URLs захардкожены и не следуют произвольному staging target | false / reject | Три exact hostname — утверждённый frozen intent; public base URL теперь также строго зафиксирован. |
| BH4 | Healthcheck мог принять redirect/не-UP payload | medium / patch | Public URL закреплён на HTTPS, curl требует успешный статус, actuator payload — `UP`. |
| BH5 | Marker SHA записывается до внешнего healthcheck | false / reject | Marker означает применённую ревизию; успешность delivery публикуется workflow только после внешнего healthcheck. Семантика существующего контракта не меняется. |
| BH6 | Проверка наличия сертификата не гарантировала живой ACME listener | medium / patch | Вместо проверки файлов используется активный challenge probe через работающий proxy. |
| BH7 | Fresh host может не иметь application images/upstreams | low / reject | Workflow предназначен для существующего Dev cutover с уже запущенными приложениями; bootstrap нового хоста вне scope. Pull образа Nginx выполняется до listener bootstrap. |
| BH8 | В `TLS_MODE=off` API hostnames не маршрутизируются напрямую | false / reject | Direct hostname API — часть public HTTPS контракта; off mode намеренно сохраняет Web/IP и path compatibility. |
| BH9 | Metrics block не покрывал дополнительные path variants | medium / patch | Дубликат EH6; prefix block и route tests добавлены. |
| BH10 | Spec якобы объявлял live rollout завершённым | false / reject | Dev task остаётся незакрытым, а Implementation Notes явно отмечают pending review/commit/push. |
| BH11 | Recovery ссылался на удаляемый `cert-setup` container log | medium / patch | Runbook направляет к Actions output и controlled `docker compose run --rm -T cert-setup`. |

## Design Notes

HTTP-01 выбран для текущих точных hostnames, потому что wildcard требует DNS-01, а существующий Yandex hook рассчитан на другую DNS API-плоскость. Режим DNS-01 остаётся доступным для будущей миграции зоны или делегирования `_acme-challenge`; текущий rollout не зависит от этого.

## Verification

**Commands:**
- `./scripts/validate.sh` — все static/runtime, Nginx, Certbot и delivery tests проходят.
- `git diff --check` — нет whitespace/errors.
- GitHub Infra CI run 38198454137 — verify и exact-SHA Dev delivery успешны; сертификат выпущен предшествующим run 38164570249 attempt 3.
- `curl`/`openssl s_client` — redirects, Let’s Encrypt issuer, все три SAN, `200/UP` на Web и четырёх path/direct actuator URL, `404` на Prometheus и `200` по IP HTTP подтверждены.
