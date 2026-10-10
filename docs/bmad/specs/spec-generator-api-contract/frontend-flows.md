# Frontend flows

## Generator workspace

При уже выбранном Enterprise frontend параллельно вызывает:

1. Analytics `GET /enterprises/{enterpriseId}/equipment-tree`.
2. Generator `GET /scenarios?enterpriseId=...`.
3. Generator `GET /runs?enterpriseId=...&status=SCHEDULED&status=QUEUED&status=RUNNING&status=STOP_REQUESTED`.

Signals не загружаются для всего предприятия: при добавлении Machine в Scenario frontend лениво вызывает Analytics signal/component endpoints этой Machine. Generator не выдаёт альтернативный equipment catalog.

## Scenario editor

1. Выбрать Machines из equipment tree.
2. Настроить base behaviors и phase overrides.
3. Вызвать draft validation по требованию пользователя либо перед save.
4. Создать disabled Scenario или полностью update существующий.
5. Показать validation из response без дополнительного GET.
6. Активировать отдельной status command; при `422` связать issues с полями по path.

UI визуально различает inherited base, `REPLACE` и `DISABLE`. Effective preview вычисляется frontend для удобства, но backend validation/snapshot остаётся authority.

## Run dialog и monitor

1. Открыть active Scenario detail.
2. Выбрать mode и заполнить mode-specific fields.
3. Для historical/scheduled предложить optional validate/estimate.
4. Создать Run с новым `Idempotency-Key`; повтор сетевого запроса использует тот же key.
5. Poll detail около каждых 2 seconds, пока status active; уважать `Retry-After`.
6. Stop повторяемой command; retry показывать только для `FAILED` и `retryable=true`.

## Analytics handoff

После появления meaningful `generatedThrough` frontend может открыть Analytics route для `enterpriseId`, `machineIds` и фактического range. Analytics response определяет readiness своими `dataThrough`, `stale` и `recalculating`. Generator status не заменяет эти признаки.
