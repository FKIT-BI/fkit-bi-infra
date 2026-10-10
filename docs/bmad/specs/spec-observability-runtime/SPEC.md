---
id: SPEC-observability-runtime
companions:
  - runtime-topology.md
  - metrics-catalog.md
  - dashboards-and-alerts.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт запуска, метрик, dashboard и alerts demo MVP.

# Observability и запуск demo MVP

## Why

Приём телеметрии, фоновые расчёты и чтение готовых проекций могут деградировать независимо, поэтому одного health endpoint недостаточно. Обязательный, воспроизводимо запускаемый observability stack должен показать потери, lag, backlog, API latency и исчерпание PostgreSQL/host ресурсов, не превращаясь в точку отказа минимального стенда.

## Capabilities

- **CAP-1**
  - **intent:** Оператор может одной стандартной командой запустить полный demo-стенд вместе с observability.
  - **success:** `docker compose up -d` запускает Prometheus, Grafana, postgres_exporter и node_exporter вместе с приложениями; все контейнеры имеют проверяемое состояние запуска.

- **CAP-2**
  - **intent:** Prometheus может собирать системные и прикладные метрики всех критичных участников.
  - **success:** Targets analytics, generator, PostgreSQL и host находятся в состоянии `UP` и обновляются каждые 15 seconds.

- **CAP-3**
  - **intent:** Команда может открыть готовые operational dashboards без настройки через UI.
  - **success:** Grafana автоматически получает Prometheus datasource и шесть versioned dashboards после первого запуска.

- **CAP-4**
  - **intent:** Оператор может заметить деградацию ingestion, расчётов, API, PostgreSQL и диска до остановки стенда.
  - **success:** Согласованные alert rules переходят в `firing` на тестовых порогах и видны в Prometheus/Grafana.

- **CAP-5**
  - **intent:** Business services продолжают работу при недоступности observability.
  - **success:** Остановка Prometheus или Grafana не меняет readiness analytics, generator и PostgreSQL и не блокирует публикацию telemetry или HTTP-ответы.

- **CAP-6**
  - **intent:** Метрики позволяют проверить SLO без неконтролируемого роста series и диска.
  - **success:** Предметные идентификаторы не используются как labels, scrape interval равен 15 seconds, а Prometheus retention ограничен 7 days и 1 GB.

## Constraints

- Обязательный MVP stack состоит из Prometheus, Grafana, postgres_exporter и node_exporter.
- Analytics и generator публикуют Micrometer Prometheus endpoint, стандартные JVM/process/HTTP/Hikari и согласованные custom metrics.
- Grafana datasource, dashboards и Prometheus rules provisioned из versioned файлов `fkit-bi-infra`; ручная настройка не является частью запуска.
- Metrics collection и exporter failures не входят в транзакции ingestion, calculation или API.
- Observability входит в общий бюджет 4 vCPU/8 GB, описанный в `../spec-mvp-load-slo/resource-budget.md`.
- Метрики, topology, dashboard и alerts определены в companion-файлах.

## Non-goals

- Loki, Tempo, distributed tracing, cAdvisor и отдельный metrics cluster.
- Alertmanager, email, Telegram, PagerDuty или другие внешние уведомления.
- Использование Prometheus как хранилища business analytics или per-machine telemetry.
- Публичный анонимный доступ к Grafana, Prometheus и actuator metrics.

## Success signal

После стандартного запуска оператор открывает provisioned Grafana, видит живые данные приложений, PostgreSQL и host, может воспроизвести alert на lag или dropped telemetry, а остановка observability не влияет на основные пользовательские потоки.
