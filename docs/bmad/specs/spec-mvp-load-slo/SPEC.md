---
id: SPEC-mvp-load-slo
companions:
  - load-profile.md
  - resource-budget.md
  - slo-and-benchmarks.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт минимальной нагрузки, ресурсов и SLO demo MVP.

# Нагрузочный профиль и SLO demo MVP

## Why

Demo MVP должен одновременно принимать телеметрию, считать готовые проекции и быстро обслуживать frontend на одном доступном стенде. Зафиксированный профиль отделяет достаточную для демонстрации конфигурацию от промышленного масштаба и даёт проверяемую границу для решений по PostgreSQL, workers, retention и observability.

## Capabilities

- **CAP-1**
  - **intent:** Стенд может непрерывно обслуживать номинальный realtime-профиль оборудования.
  - **success:** 20 машин по 15 активных сигналов со средним периодом 10 секунд работают в пределах согласованных SLO.

- **CAP-2**
  - **intent:** Ingestion может принять резервную длительную и кратковременную пиковую нагрузку без блокировки чтения.
  - **success:** Стенд выдерживает 200 measurements/s длительно и 1000 measurements/s в течение 60 секунд, не создавая resource-exhaustion ошибок query API.

- **CAP-3**
  - **intent:** Frontend может получать готовые текущие и исторические данные с предсказуемой задержкой.
  - **success:** При номинальном профиле p95 current API не превышает 500 ms, overview — 1 s, аналитики за 30 дней — 2 s, за 90 дней — 5 s.

- **CAP-4**
  - **intent:** Фоновые расчёты могут догонять realtime, не монополизируя PostgreSQL.
  - **success:** При номинальном профиле current signal готов не позднее 15 s, machine state — 20 s, minute aggregates — 120 s от `observedAt`.

- **CAP-5**
  - **intent:** Историческая генерация и полный перерасчёт могут использовать свободную ёмкость стенда управляемо.
  - **success:** Historical writer поддерживает 1000–2000 measurements/s с throttling, а прогон 20 млн measurements завершается ориентировочно за 3–5 часов без нарушения защитного SLO query API.

- **CAP-6**
  - **intent:** Команда может до реализации полного расчётного контура доказать достаточность минимального стенда.
  - **success:** Воспроизводимый benchmark проходит на 4 vCPU, 8 GB RAM и SSD не менее 100 GB при raw retention 90 дней.

## Constraints

- Минимальный стенд: 4 vCPU, 8 GB RAM и SSD 100 GB; рекомендуется SSD 150 GB.
- Расширенный профиль 8 vCPU/16 GB RAM не является условием приёмки MVP, но используется при росте данных или параллелизма.
- Все сервисы, PostgreSQL и обязательный observability stack работают на одном минимальном host.
- Query, ingestion и calculation получают раздельные connection budgets; тяжёлый historical/recalculation workload подчинён интерактивному чтению.
- Raw telemetry хранится 90 дней и удаляется целыми UTC-day partitions только после закрытия зависимых dirty windows.
- Значения и методика измерения определены в `load-profile.md` и `slo-and-benchmarks.md`; ресурсный бюджет — в `resource-budget.md`.

## Non-goals

- Производственная высокая доступность, горизонтальное масштабирование и zero-loss ingestion.
- Гарантия 200 measurements/s как штатного business profile: это резервный sustained benchmark.
- Высокочастотные waveform, Kafka, ETL и отдельный time-series storage.
- Неограниченный параллельный backfill или перерасчёт нескольких машин.

## Success signal

Полный стенд с приложениями и observability проходит benchmark на 4 vCPU/8 GB: realtime не отстаёт за заданные пределы, frontend читает готовую аналитику в пределах SLO, а burst и historical workload не блокируют API или PostgreSQL.

## Assumptions

- Фактический размер raw row и индексов будет измерен на PostgreSQL 16: оценка диска до benchmark остаётся диапазоном, а не гарантированным числом байт на measurement.
