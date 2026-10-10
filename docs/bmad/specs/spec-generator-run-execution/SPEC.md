---
id: SPEC-generator-run-execution
companions:
  - execution-modes.md
  - progress-and-checkpoints.md
  - commands-and-recovery.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт времени, progress, stop, retry и восстановления GenerationRun.

# Выполнение GenerationRun

## Why

Realtime, historical и будущая генерация используют разные часы, границы и способы восстановления, но должны публиковать одинаково объяснимую raw telemetry. Однозначная execution-модель нужна, чтобы generator не создавал future data, duplicate measurements или burst после задержки, а frontend мог отличить завершение записи raw от готовности аналитики.

## Capabilities

- **CAP-1**
  - **intent:** Realtime Run может следовать реальному времени без перегрузки после задержки процесса.
  - **success:** Просроченные ticks пропускаются и учитываются, catch-up burst отсутствует, а новый `observedAt` не опережает допустимый realtime skew.

- **CAP-2**
  - **intent:** Historical Run может воспроизводимо заполнить заданный прошлый диапазон.
  - **success:** UTC-диапазон до 90 суток выполняется virtual clock с deterministic phases и throttling 1000–2000 measurements/s.

- **CAP-3**
  - **intent:** Пользователь может создать одноразовый будущий realtime-запуск.
  - **success:** Timestamp с offset нормализуется в UTC, до срока raw отсутствует, readiness повторно проверяется, а опоздание больше 30 seconds завершает Run с `SCHEDULE_MISSED`.

- **CAP-4**
  - **intent:** Frontend может одинаково показывать состояние и прогресс любого режима.
  - **success:** Run detail содержит timestamps, phase/cycle, `generatedThrough`, nullable `progressPercent`, counters, last write и bounded failure data.

- **CAP-5**
  - **intent:** Historical Run может восстановиться после сбоя без двойной записи.
  - **success:** Пятиминутные event-time chunks получают checkpoint только после подтверждения всех batches, а retry повторяет deterministic batch IDs и продолжает тот же Run.

- **CAP-6**
  - **intent:** Пользователь может безопасно и повторно запросить остановку Run.
  - **success:** Scheduled/queued Run отменяется, running Run проходит `STOP_REQUESTED`, текущая запись и flush ограничены timeout, остаток учитывается как dropped, а повторный stop возвращает текущее состояние.

- **CAP-7**
  - **intent:** Повтор HTTP-команды создания Run не создаёт второй запуск.
  - **success:** Одинаковые `Idempotency-Key` и body возвращают исходный Run, а изменённый body с тем же ключом получает `409 IDEMPOTENCY_KEY_REUSED`.

- **CAP-8**
  - **intent:** Пользователь может перейти от завершённой генерации к соответствующей аналитике без ложной синхронизации сервисов.
  - **success:** `COMPLETED` означает окончание raw generation, Run возвращает analytics context, а frontend отдельно проверяет `dataThrough`, `stale` и `recalculating` Analytics API.

## Constraints

- Правила каждого режима определены в `execution-modes.md`; progress/checkpoint — в `progress-and-checkpoints.md`; команды и recovery — в `commands-and-recovery.md`.
- Все API timestamps содержат offset и сохраняются как UTC instant; локальное время без offset не принимается.
- Historical range не превышает 90 суток, целиком находится внутри активного raw-retention window по времени PostgreSQL и не пересекает уже опубликованное generator coverage той же Machine.
- Historical execution использует отдельную квоту и не вытесняет realtime, query или calculation workloads.
- Run completion не ожидает Analytics и не предоставляет `analyticsReady`.
- Polling используется вместо SSE/WebSocket: около 2 seconds для active detail и 10 seconds для списков.

## Non-goals

- Генерация будущих measurements заранее.
- Realtime catch-up/backfill пропущенных ticks.
- Автоматическая перезапись или удаление ранее сгенерированного historical range.
- Синхронный вызов Analytics после каждого batch или при завершении Run.
- Точный процент для unbounded realtime.
- Потоковые SSE/WebSocket обновления статуса.

## Success signal

Realtime, historical и scheduled Runs проходят start, progress, stop, failure и retry без duplicate raw, future telemetry или блокировки PostgreSQL; после `COMPLETED` frontend открывает правильный analytics context и показывает фактическую готовность по metadata Analytics API.
