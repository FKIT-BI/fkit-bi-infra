# Runtime topology и запуск

## Состав

| Компонент | Источник данных | Хранение/доступ |
|---|---|---|
| Prometheus | Micrometer endpoints, postgres_exporter, node_exporter | Local volume, 7 days, 1 GB |
| Grafana | Prometheus datasource | Provisioned datasource и dashboards; отдельный volume только для runtime state |
| postgres_exporter | PostgreSQL monitoring user | Только read-only monitoring queries |
| node_exporter | Host CPU, memory, filesystem | Read-only host mounts, необходимые collector'ам |

Analytics и generator добавляют `micrometer-registry-prometheus` и публикуют `health`, `info`, `prometheus`. Nginx продолжает отдавать наружу только требуемые API и health routes; metrics endpoint доступен Prometheus внутри Compose network.

## Стандартный запуск

Из deployment-каталога `fkit-bi-infra` одна команда запускает весь стенд:

```bash
docker compose up -d
```

Observability services входят в default Compose project и не требуют отдельного profile. Приложения не имеют `depends_on` на Prometheus или Grafana. Grafana может зависеть от готовности Prometheus только для собственного старта; её ошибка не должна перезапускать business services.

Versioned configuration размещается под `fkit-bi-infra/observability/`:

```text
observability/
  prometheus/prometheus.yml
  prometheus/rules/*.yml
  grafana/provisioning/datasources/*.yml
  grafana/provisioning/dashboards/*.yml
  grafana/dashboards/*.json
```

## Сеть и секреты

- Prometheus и exporters не публикуются в public interface.
- Grafana по умолчанию привязывается к loopback host и доступна через SSH tunnel; публикация через защищённый reverse proxy является отдельным deployment решением.
- Admin user/password Grafana и PostgreSQL exporter credentials поступают из private `.env`; значения не коммитятся.
- Для exporter создаётся отдельный минимально привилегированный PostgreSQL monitoring user; application credentials не переиспользуются.
- Prometheus scrape timeout меньше scrape interval, а недоступный target не задерживает другие scrape jobs.

## Health и smoke test

После запуска автоматическая проверка подтверждает:

1. Compose services запущены, business health endpoints отвечают.
2. Prometheus health endpoint готов и targets `analytics`, `generator`, `postgres`, `node` имеют `UP`.
3. Grafana health endpoint отвечает, datasource доступен, шесть dashboards загружены provisioning-механизмом.
4. После тестового telemetry batch растут accepted counters и обновляются projection lag/backlog metrics.
5. После остановки Prometheus или Grafana analytics, generator, API и ingestion продолжают работу.
