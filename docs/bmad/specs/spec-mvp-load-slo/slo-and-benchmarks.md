# SLO и нагрузочные проверки

## SLO

| Объект | Номинальный предел |
|---|---:|
| Current signal API p95 | 500 ms |
| Current machine state API p95 | 500 ms |
| Enterprise/line overview API p95 | 1 s |
| Analytics API за период до 30 суток p95 | 2 s |
| Analytics API за период до 90 суток p95 | 5 s |
| Current signal projection lag | 15 s |
| Machine state projection lag | 20 s |
| Minute rollup publication lag | 120 s |

HTTP latency измеряется на сервере от приёма запроса до готового ответа и не включает внешний WAN. Projection lag — разница между текущим временем и `dataThrough` соответствующей готовой проекции при поступающей realtime telemetry.

Во время sustained/historical workload защитный SLO для current/overview API — p95 не более 1 s, отсутствие resource-exhaustion 5xx и отсутствие ожидания завершения расчёта. Краткий burst может увеличить lag, но после его окончания current/state должны вернуться в номинальный предел за 2 минуты, minute rollups — за 5 минут.

## Обязательный benchmark

1. Запустить полный Compose stack, включая Prometheus и Grafana, на 4 vCPU/8 GB.
2. Создать nominal inventory и прогреть систему не менее 15 минут.
3. Выполнять nominal realtime 30 minutes вместе с пятью read clients: current, overview, 30-day analytics и 90-day analytics.
4. Повторить 30-minute run при 200 measurements/s.
5. Подать 1000 measurements/s в течение 60 seconds и измерить восстановление lag.
6. Импортировать 20 million historical measurements при работающем nominal realtime и read clients.
7. Выполнить полный перерасчёт одной машины и проверить, что чтение использует предыдущую опубликованную версию до атомарной подмены.
8. Зафиксировать p50/p95/p99 API latency, accepted/dropped measurements, projection lag, dirty backlog, PostgreSQL connections/locks, CPU, RAM и disk growth.

## Критерии прохождения

- Все nominal SLO выполнены после прогрева.
- Sustained и historical tests соблюдают защитный SLO чтения.
- Burst не вызывает deadlock, unbounded queue, OOM или ручное восстановление; потеря raw допустима только как наблюдаемый dropped count.
- Historical 20-million run завершается ориентировочно за 3–5 hours; выход за диапазон не является автоматическим провалом, если realtime и API SLO сохранены и причина задокументирована.
- После каждого теста система самостоятельно возвращается к стабильному lag и не оставляет зависшие jobs или dirty windows.
