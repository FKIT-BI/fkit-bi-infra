# Примеры evaluation

## 1. Числовой threshold и activation delay

Rule `RUN`: `speed GTE 100`, activation 3 s. Speed становится `120` в `10:00:00` и остаётся usable. До `10:00:03` rule не активно; с `10:00:03` результат `RUN`, `effectiveFrom=10:00:03`.

## 2. Hysteresis и release delay

Активное `RUN`: enter `speed GTE 100`, exit `speed LT 70`, release 5 s. Значение `80` не освобождает rule. Speed падает до `60` в `10:05:00` и остаётся ниже 70; выход effective в `10:05:05`.

## 3. DOUBLE equality с tolerance

Condition: `vibration EQ 0.0`, tolerance `0.01`. Значение `0.008` даёт `TRUE`, `0.011` даёт `FALSE`. То же значение с `STALE` freshness даёт `UNKNOWN`, а не `FALSE`.

## 4. String IN

Rule `SETUP`: `mode IN [MANUAL, MAINTENANCE]`. Точные values `MANUAL` и `MAINTENANCE` дают `TRUE`; `manual` даёт `FALSE`; отсутствие usable mode даёт `UNKNOWN`.

## 5. Priority conflict

Rules `DOWN priority=200` по `alarm EQ true` и `RUN priority=100` по `speed GTE 100` одновременно готовы. После выполнения activation delay выбирается `DOWN`. После его release evaluator может выбрать уже активированный `RUN`.

## 6. UNKNOWN и default

Rule `RUN` зависит от stale speed и возвращает `UNKNOWN`; `DOWN` возвращает `FALSE`. System offline не выполняется, потому что другая telemetry машины поступает. Результат `defaultState=IDLE`, `matchedRuleId=null`, `evaluationQuality=DEGRADED`.

## 7. System OFFLINE

`offlineAfterMs=60_000`; после `12:00:00` ни одного accepted measurement машины нет. До истечения timeout сохраняется user evaluation, с `12:01:00` результат `OFFLINE` независимо от conditions и priorities.
