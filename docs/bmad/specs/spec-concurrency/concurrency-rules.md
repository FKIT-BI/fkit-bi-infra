# Правила конкурентности

## Приоритет и ожидаемый риск

Главный operational приоритет MVP — короткое время ответа и отсутствие длительных блокировок. PostgreSQL locks полностью не исключаются: они нужны для атомарности ограниченного набора multi-row invariants. Их область и время удержания минимальны; при contention пользовательская команда быстро завершается без partial writes, а internal worker пропускает или откладывает занятую работу.

Обычные независимые configuration updates не имеют версии/ETag: последовательность определяется порядком commit. Параллельный полный `PUT` может затереть более ранние поля. Это осознанно принято для MVP; уникальность, ownership и прочие структурные ограничения при этом сохраняются.

## Владельцы данных и сериализация

| Конкурентная операция | Механизм | Что предотвращает |
| --- | --- | --- |
| Обычный полный update конфигурации | Короткий write transaction; last-committed-write-wins; SQL constraints | Частичные изменения и нарушение локальной целостности; не предотвращает stale overwrite |
| Назначение набора Machines линии | Conditional `UPDATE` только при `line_id IS NULL`; выбранные Machine блокируются по UUID в стабильном порядке; одна transaction | Двойное назначение и частичный batch |
| Component tree change | Lock owning Machine; затем проверка циклов и write | Параллельные изменения дерева одной машины |
| Shift schedule change | Lock owning Enterprise; затем проверка пересечений и write | Write-skew параллельных изменений одного расписания |
| Первое использование/семантическое изменение Signal | Уже заданные shared/exclusive transaction advisory locks по Signal ID | Изменение семантики одновременно с принятием первого raw |
| Calculation work | Durable per-machine lease; queue claim с `FOR UPDATE SKIP LOCKED`; повторная проверка claim перед publication | Два concurrent publisher одной Machine; позволяет разным машинам идти параллельно |
| Current signal upsert | Условный upsert по event-time ordering tuple | Более старое измерение не затирает более новое |
| Generator Run ownership | Условный DB status transition и execution lease/heartbeat на Run | Два instances не исполняют один Run одновременно |
| Generator machine reservation | Durable reservation rows; lock-claim по каждому Machine ID в стабильном порядке; validate overlap и insert в одной транзакции | Дублирующие realtime/scheduled/history reservations и частичный multi-machine start |
| Historical execution capacity | Одна durable slot row в `generator`; атомарный claim до начала выполнения и освобождение в terminal/recovery transaction | Более одного одновременного historical Run на минимальном host |

`SKIP LOCKED` используется только для queue-like claim операций. Это не способ получить согласованный пользовательский список: пропущенные locked rows являются ожидаемой семантикой очереди. Transaction-level advisory locks автоматически освобождаются при завершении или rollback той транзакции, которая их взяла.

## Generator reservations и несколько instances

Generator хранит reservations в принадлежащей ему schema. Создание Run, его immutable snapshot, резервирование полного набора машин и, если требуется, historical capacity slot фиксируются атомарно. Если одна машина или слот не может быть быстро зарезервирован, вся команда завершается без частичного старта; конфликт не повторяется автоматически без изменения условий.

Reservation проверяется под коротким transaction-scoped claim для всех machine IDs в сортированном порядке. Для каждого Run сохраняется тип и ограниченный event interval; `NULL` end у немедленного unbounded realtime означает reservation до terminal status. Исторические coverage overlap проверяются под тем же per-Machine protocol. Scheduled request остаётся ограниченным обязательными `durationMs` или `eventTo`.

На одной Machine разрешён максимум один `RUNNING|STOP_REQUESTED` realtime Run. Future reservations одной машины не пересекаются; historical Run не пересекает уже подтверждённую historical coverage. Historical Run может сосуществовать с realtime Run, но глобально на минимальном стенде в historical slot помещается только один.

Каждый владелец `RUNNING` Run обновляет `leaseUntil` heartbeat-ом. Другой instance не присваивает себе живую lease. После истечения lease recovery worker условно переводит Run в `FAILED` с `retryable=true`, освобождает активные reservations/slot и сохраняет checkpoint. Дальнейший запуск — существующий explicit retry; realtime gap остаётся видимым. Scheduled Run продолжает подчиняться уже принятому 30-second misfire rule.

`STOP_REQUESTED` удерживает reservations до завершения текущего batch/ограниченного flush и terminal transition. Stop, retry, expiry recovery и completion используют условное обновление ожидаемого статуса; проигравшая команда читает текущее состояние Run и не делает второй transition.

## Быстрый contention, deadlocks и retry

- Read API не берёт explicit row/advisory locks на read models и не читает staging; PostgreSQL MVCC показывает committed версию проекций.
- Queue claim использует `SKIP LOCKED`; один занятый work item не задерживает claim независимых строк.
- Для reservation claim используется transaction-level try-lock. Для необходимых row-lock операций задаётся короткий локальный `lock_timeout`; конкретное значение устанавливается нагрузочным тестом исходя из API SLO.
- При невозможности сразу получить user-facing resource lock приложение возвращает стабильную conflict/error envelope без commit. Internal worker безопасно откладывает или ограниченно повторяет работу.
- Перед получением нескольких locks применяются stable order и сортировка UUID. Owner/aggregate проверяется до child; набор Machine и Signal IDs блокируется детерминированно.
- Deadlock/serialization retry допускается только ограниченное число раз и только для идемпотентной транзакции. Validation, ownership, already-reserved и stale-update outcomes не повторяются автоматически.
- Raw telemetry batches и read pools уже имеют собственные connection/quota limits. Locks аналитической проекции не распространяются на append-only raw measurement table.
- Не вводятся глобальный mutex, application-wide single leader, `SERIALIZABLE` на всех запросах, бесконечное ожидание lock или автоматический retry пользовательской команды без ключа идемпотентности.

## Приёмочные проверки

1. Два независимых configuration PUT фиксируются по очереди; повтор stale body может победить, но каждая транзакция полностью валидна и атомарна.
2. Два параллельных batch assignment одной Machine не назначают её двум Lines; один конфликт завершается быстро и не оставляет частичный пакет.
3. Несколько Analytics instances заявляют work через `SKIP LOCKED`; одна Machine не получает двух active publishers, разные Machine рассчитываются параллельно.
4. Два Generator instances одновременно создают Runs с общей Machine: только один получает reservation, все machine rows multi-machine Run либо записаны, либо отсутствуют.
5. Одновременно запускаются два historical Run: только один получает capacity slot; realtime Run продолжает использовать свою квоту.
6. При двух командах `stop/retry` для одного Run фиксируется один допустимый status transition.
7. Падение владельца Run приводит после lease expiry к retryable failure; explicit retry продолжает с checkpoint и не дублирует committed batches.
8. Во время длительного расчёта current/history read возвращает последнюю committed проекцию; задержка и ошибки contention наблюдаемы по метрикам.

## Справка PostgreSQL

- [`SELECT` locking clause: `SKIP LOCKED`](https://www.postgresql.org/docs/16/sql-select.html) — применяется для queue consumer, поскольку locked строки пропускаются и результат не является обычным согласованным выбором.
- [Explicit locking и advisory locks](https://www.postgresql.org/docs/16/explicit-locking.html) — transaction-level advisory lock автоматически освобождается при завершении transaction; advisory protocol соблюдается приложением.
