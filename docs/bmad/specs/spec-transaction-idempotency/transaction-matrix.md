# Транзакционная модель и доступ к данным

## Выбранный persistence-подход

Оба Java-приложения используют Spring JDBC (`JdbcTemplate` или `NamedParameterJdbcTemplate`) через собственные persistence adapters/repositories. Application и domain модели не зависят от JDBC API и не являются ORM entities. Сервисный метод задаёт транзакционную границу с `@Transactional`; репозитории, участвующие в сценарии, используют тот же `DataSource` и transaction manager. Для методов чтения допускается read-only hint, но он не является блокировкой и не заменяет корректный SQL/query plan.

SQL параметризуется. Массовые вставки raw и bulk-обновления выполняются JDBC batch-операциями; размер пакета и длительность транзакции контролируются нагрузочным тестом. Текущие/исторические API используют явные read queries и mapper-ы в response/read models. JPA/Hibernate и PostgreSQL-specific `COPY` не входят в базовый путь MVP. `COPY` рассматривается только при доказанном benchmark bottleneck.

Не следует держать транзакцию открытой между HTTP-вызовами, во время ожидания ресурса, расчёта, внешнего запроса или логирования большого результата. Правила rollback должны учитывать Spring default: runtime exceptions откатывают по умолчанию; если сценарий допускает checked exceptions, rollback policy задаётся явно.

## Транзакционная матрица

| Сценарий | Одна атомарная транзакция | Вне транзакции / результат сбоя |
| --- | --- | --- |
| Полное изменение Machine/Component/Signal/StateRule | Проверенные изменения всей команды; если нужен replay — durable dirty work | Ошибка до commit откатывает все изменения; проекция обновляется фоново |
| Назначение нескольких Machines линии | Все проверки ownership/свободного назначения и все назначения | Любой конфликт откатывает весь пакет назначений |
| ManualIncident create/update/close/cancel | Для create: обязательный `Idempotency-Key`, request hash, incident и dirty range/job; для остальных команд — изменение инцидента и соответствующий dirty range/job | Повтор create с тем же key/body возвращает исходный результат; тот же key с иным body — `409`; перерасчёт асинхронный, до publication читается прежняя полная аналитика |
| Raw telemetry batch | Idempotency header/hash, raw rows, необходимые signal usage и durable recalculation hints | Пакет полностью принят или полностью отклонён; повтор с тем же ID/hash идемпотентен |
| Создание Generator Run | Idempotency key, canonical request hash, Run snapshot и reservations/status, требуемые контрактом генератора | Повтор key/body возвращает исходный Run; несовпадающий body конфликтует |
| Один исторический telemetry chunk | Стабильные batch IDs и checkpoint/run progress обновляются в отдельных коротких транзакциях | После сбоя chunk безопасно повторяется; checkpoint не утверждает незавершённую запись |
| Подготовка расчётного диапазона | Отдельными ограниченными операциями durable staging вне transaction активной проекции | При crash stage может быть очищен и построен заново из raw и durable work |
| Публикация расчётного диапазона | Валидированный range replace, current/currency fields, завершение work/job и checkpoint | Весь commit проходит или откатывается; MVCC показывает старую или новую версию целиком |
| Generator stop/retry/state transition | Guarded изменение Run и его attempt/status согласно Generator contract | Повтор команды возвращает текущее состояние либо стабильный conflict; текущий raw batch завершается или откатывается отдельно |

## Publication protocol

1. Worker получает durable work и machine lease короткой claim-транзакцией.
2. Raw читается, replay и вычисление выполняются вне транзакции замены опубликованных строк.
3. Валидированный вывод сохраняется в durable staging; до публикации проверяются coverage, отсутствие дыр/пересечений, бизнес-ключи и суммы длительностей.
4. Короткая транзакция сверяет актуальность work/checkpoint, заменяет только затронутый Machine/time range, обновляет current projection и currency metadata, фиксирует job/work/checkpoint outcome.
5. Commit атомарно открывает новую версию читателям. При rollback предыдущая версия остаётся доступной; повтор worker-а безопасен.
6. Staging удаляется bounded cleanup-ом после успеха/отмены. Незавершённые stage rows не читаются API.

Инцидентные перерасчёты меняют effective timeline и производные state/loss buckets, но не raw и не calculated state timeline. Telemetry перерасчёты обновляют рассчитанные интервалы и затронутые rollups. Current signal projection может обновляться отдельным условным idempotent upsert после commit ingestion и не ждёт исторической публикации.

## Идемпотентность и восстановление

- Telemetry idempotency обеспечивается `(producerId, producerBatchId)` и hash канонического `TELEMETRY_BATCH_V1`; равный ключ с иным hash отклоняется.
- ManualIncident create требует `Idempotency-Key`; ключ, canonical request hash и созданный incident сохраняются атомарно. Область ключа — authenticated user + operation.
- Dirty work и deadlines являются durable. Worker может выполнять работу повторно; публикация заменяет диапазон, не прибавляет агрегаты к прежним значениям.
- Успешная публикация и отметка работы/job завершённой фиксируются вместе. Если подтверждение commit потерялось, состояние durable work/job позволяет определить исход без второй partial publication.
- Сбой до публикации не меняет active projection. Истёкший lease возвращает незавершённое задание в обработку; staging можно ограниченно очистить и построить заново.
- Ошибка валидации/неисправимая ошибка сохраняет диагностируемое failed work согласно pipeline contract; ошибочная работа не удаляется как успешная.
- PostgreSQL rollback относится только к SQL изменениям текущей transaction. HTTP вызовы, метрики и логи выполняются вне предположения об атомарности с БД; сообщения/события для будущей интеграции потребуют отдельного durable delivery contract.

## Проверяемые сценарии

1. Ошибка после записи части полного machine update оставляет исходную конфигурацию без изменений.
2. Повтор одного telemetry batch с прежним payload не создаёт дополнительные measurements или hints.
3. Повтор того же batch ID с другим hash возвращает конфликт без частичной записи.
4. Ошибка в середине publication сохраняет прежние intervals и buckets; читатель не видит частичную замену.
5. Crash после заполнения staging, но до publication позволяет повторно собрать/опубликовать тот же диапазон.
6. Сбой после изменения incident, но до commit откатывает incident и dirty work вместе; ошибка последующего расчёта сохраняет incident, но оставляет старую committed аналитику с признаком пересчёта.
7. Повтор historical chunk не дублирует raw, а progress/checkpoint продвигается только после успешного batch commit.
