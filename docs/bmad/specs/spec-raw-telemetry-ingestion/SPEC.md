---
id: SPEC-raw-telemetry-ingestion
companions:
  - telemetry-storage.md
  - writer-protocol.md
  - availability-policy.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт raw telemetry и её best-effort ingestion для MVP.

# Сырая телеметрия и ingestion

## Why

Realtime, historical и scheduled generator runs должны передавать исходные показания без остановки аналитического сервиса под нагрузкой. Для raw telemetry приоритетом является доступность: кратковременная потеря допустима, но вставка не должна удерживать пользовательское чтение, а расчёт не должен входить в транзакцию ingestion.

## Capabilities

- **CAP-1**
  - **intent:** Generator может передать типизированные измерения одним пакетом.
  - **success:** Валидный пакет целиком сохраняется как batch header и append-only measurement rows одной короткой транзакцией; невалидный пакет не оставляет частичных данных.

- **CAP-2**
  - **intent:** Generator может безопасно повторить пакет после неопределённого результата записи.
  - **success:** Повтор с теми же `producerId + producerBatchId` и payload hash не создаёт измерения повторно; другой payload под тем же ключом отклоняется.

- **CAP-3**
  - **intent:** Analytics может обрабатывать realtime, late, out-of-order и historical telemetry по времени события.
  - **success:** `observedAt` сохраняется независимо от порядка вставки; допустимое прошлое принимается, realtime-событие за future-skew отклоняется, а scheduled run не записывает будущие значения заранее.

- **CAP-4**
  - **intent:** Система может сохранить исходное качество и диагностические признаки измерения без потери аномального факта.
  - **success:** `GOOD`, `UNCERTAIN` и `BAD` сохраняются; out-of-range получает компактный flag, а `null`, `NaN`, infinity и несовместимый тип отклоняют пакет.

- **CAP-5**
  - **intent:** Realtime ingestion может деградировать без остановки приложения.
  - **success:** После ограниченного ожидания и retry переполненный или не записанный пакет отбрасывается, потеря наблюдаема, а query API и конфигурационные операции продолжают обслуживаться.

- **CAP-6**
  - **intent:** Frontend может читать последнюю готовую аналитику независимо от текущей raw-записи и перерасчёта.
  - **success:** Аналитический запрос не ожидает ingestion или worker, читает подготовленную проекцию и сообщает `dataThrough`, `calculatedAt` и признак устаревания.

## Constraints

- Логическая SQL-модель и индексы определены в `telemetry-storage.md`.
- Пакет, идемпотентность, event time, validation и режимы передачи определены в `writer-protocol.md`.
- Деградация, изоляция ресурсов и наблюдаемость определены в `availability-policy.md`.
- Best-effort и допустимая потеря применяются только к raw telemetry; конфигурация, правила, ручные инциденты и generator definitions остаются durable transactional data.
- Raw append-only: существующие измерения не обновляются и не исправляются на месте.
- Ingestion не рассчитывает state intervals, rollup или shift metrics.
- Raw не хранит `shiftId`, состояние машины или рассчитанные показатели.
- Raw retention равен 90 суткам; очистка целых UTC-day partitions выполняется вне ingestion transaction по правилам `telemetry-storage.md`.
- Raw transaction атомарно сохраняет durable first-use и recalculation hints, но не выполняет сами аналитические расчёты.

## Non-goals

- Exactly-once для каждого отдельного измерения.
- Гарантия отсутствия потерь raw telemetry при длительной недоступности PostgreSQL.
- Высокочастотные waveform и binary payload.
- Синхронная публикация готовой аналитики вместе с raw-пакетом.
- Вычисление аналитики из raw на frontend.
- Генерация historical data старше активного 90-дневного raw window.

## Success signal

Под нагрузкой или при временной ошибке PostgreSQL realtime generator продолжает работу с наблюдаемой потерей пакетов, query API возвращает последнюю готовую аналитику, а после восстановления новые пакеты и фоновые расчёты продолжаются без ручного восстановления таблиц.
