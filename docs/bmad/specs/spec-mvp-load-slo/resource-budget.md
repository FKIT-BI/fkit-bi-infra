# Ресурсный бюджет минимального стенда

## Память

Значения являются целевым working-set бюджетом и основой для container limits после измерения, а не обещанием равномерного потребления.

| Участник | Целевой бюджет RAM |
|---|---:|
| PostgreSQL 16 | 2.25–2.75 GB |
| `fkit-bi-analytics`, Java heap | 1.5 GB |
| `fkit-bi-generator`, Java heap | 512–640 MB |
| Prometheus | до 512 MB |
| Grafana | до 256 MB |
| postgres_exporter + node_exporter | до 128 MB суммарно |
| Web + nginx | до 256 MB |
| OS, filesystem cache, Docker и запас | не менее 1.5 GB |

Java heap задаётся явно. Native memory JVM, connection buffers и page cache учитываются общим запасом. На 8 GB не запускаются Loki, Tempo, cAdvisor, Alertmanager или дополнительные копии приложений.

## CPU и параллелизм

- Analytics: 2–3 calculation workers и 1–2 ingestion workers.
- Пользовательский тяжёлый recalculation: один одновременно; второй допускается только для другой машины после benchmark.
- Historical generator не занимает все worker threads и использует throttling.
- CPU limits не должны создавать искусственное throttling в nominal test; приоритет задаётся bounded concurrency, connection budgets и batch size.

## PostgreSQL connections

| Клиент | Максимум |
|---|---:|
| Analytics суммарно | 14–16 |
| Generator | 2–3 |
| postgres_exporter и обслуживание | 2–3 |
| Резерв PostgreSQL | не менее 4 |

Внутри analytics query path сохраняет собственный резерв; ingestion и calculation не могут занять все доступные соединения. Точная реализация может использовать отдельные pools или общий pool с отдельными concurrency semaphores, если benchmark доказывает ту же изоляцию.

## Диск

- SSD обязателен; 100 GB — нижняя граница, 150 GB — рекомендуемый объём.
- Суточные raw partitions и основной индекс `(signal_id, observed_at)` контролируются по фактическому размеру.
- Предупреждение создаётся при свободном месте менее 20%, критический сигнал — менее 10%.
- Рост БД измеряется после nominal и 20-million historical benchmark; если прогноз 90-дневного retention не помещается с 20% запасом, увеличивается диск, а не добавляются синхронные операции очистки в ingestion.
