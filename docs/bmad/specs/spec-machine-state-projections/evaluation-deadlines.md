# Evaluation deadlines

## Назначение

State transition может наступить без нового measurement:

- `lastUsableObservedAt + staleAfterMs`;
- `conditionTrueSince + activationDelayMs`;
- `exitConditionTrueSince + releaseDelayMs`;
- `lastTelemetryObservedAt + offlineAfterMs`.

Поэтому ingest-driven pipeline дополняется небольшой PostgreSQL delayed-work таблицей, а не внешним broker.

## `machine_evaluation_deadline`

На Machine хранится максимум одна ближайшая строка:

```text
machineId
deadlineAt
reason: SIGNAL_STALE | RULE_ACTIVATION | RULE_RELEASE | MACHINE_OFFLINE
leaseOwner?
leaseUntil?
updatedAt
```

После каждого evaluation backend вычисляет минимальную будущую границу и upsert-ит её. Новое measurement может перенести, заменить или удалить ранее запланированный deadline.

## Выполнение

Worker забирает due rows ограниченным batch:

```sql
SELECT ...
FROM machine_evaluation_deadline
WHERE deadline_at <= now()
ORDER BY deadline_at
FOR UPDATE SKIP LOCKED
LIMIT :limit
```

После lease он:

1. оценивает Machine в `deadlineAt`;
2. публикует переход с `effectiveFrom=deadlineAt` и фактическим `detectedAt`;
3. рассчитывает и сохраняет следующий deadline либо удаляет строку.

Если worker опоздал, event-time переход остаётся на `deadlineAt`. Истёкший lease разрешает recovery другим instance. Отдельные scheduler jobs на signals не создаются.

## Последовательность примера

При measurement в `12:00:00`, activation delay 3 s, stale timeout 30 s, release delay 5 s и offline timeout 60 s возможна цепочка:

```text
12:00:03 RULE_ACTIVATION
12:00:30 SIGNAL_STALE
12:00:35 RULE_RELEASE
12:01:00 MACHINE_OFFLINE
```

Каждая обработка сохраняет только следующую ближайшую строку. Measurement в `12:00:20` пересчитывает будущие deadlines из нового snapshot.
