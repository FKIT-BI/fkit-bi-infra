# Dashboards и alerts

## Provisioned dashboards

| Dashboard | Основные панели |
|---|---|
| System overview | Target health, CPU/RAM/disk, service uptime, 5xx, общий projection lag |
| Ingestion & generator | Generated/accepted/dropped rate, batch size/commit, buffer, write errors, sequence gaps |
| Calculations & projections | Current/state/rollup lag, dirty backlog/age, active jobs, duration и failures |
| API | Request rate, p50/p95/p99, status codes, slow routes, in-flight/Hikari pressure |
| PostgreSQL & storage | Connections, transactions, locks/deadlocks, database size, disk free, partition horizon |
| Recalculation & jobs | Runs by type/outcome, duration, active work, last failures и recovery trend |

Dashboards operational, а не business-facing: они не заменяют frontend analytics и не требуют machine/signal labels.

Некоторые provisioned панели зависят от метрик будущих stories (расчёты,
recalculation и projection backlog). Пока соответствующая instrumentation не
попала в сервисы, такие панели могут быть пустыми; это само по себе не означает
неисправность Prometheus или Grafana. Сверяйте наличие метрик с
`/actuator/prometheus` соответствующего сервиса.

## Alert rules MVP

| Условие | Уровень | For |
|---|---|---:|
| Prometheus target down | warning | 2 min |
| `increase(dropped measurements[5m]) > 0` | warning | 0 min |
| Current/state projection lag > 30 s | warning | 5 min |
| Minute rollup lag > 180 s | warning | 5 min |
| Oldest dirty window > 300 s | warning | 5 min |
| API 5xx ratio > 1% при достаточном traffic | warning | 5 min |
| API p95 > 1 s для current/overview | warning | 5 min |
| Hikari active/max > 80% или pending > 0 | warning | 5 min |
| PostgreSQL connections > 80% лимита | warning | 5 min |
| Рост deadlocks или failed calculation jobs | warning | 0 min |
| Free filesystem < 20% | warning | 10 min |
| Free filesystem < 10% | critical | 5 min |
| Raw partition horizon < 2 days | critical | 0 min |

Alert rules хранятся в Prometheus rules и видны в Prometheus/Grafana. В MVP они не отправляют внешние уведомления; оператор проверяет firing rules на dashboard. Тест запуска должен уметь безопасно воспроизвести как минимум target-down, dropped-measurements и projection-lag alert.
