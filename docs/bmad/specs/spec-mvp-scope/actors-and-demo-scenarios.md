# Акторы и демонстрационные сценарии

## Человеческие акторы

| UX-персона | Основные действия | Реальное разрешение MVP |
|---|---|---|
| Конфигуратор | Предприятие, смены, линии, машины, компоненты, сигналы, правила | Любой аутентифицированный пользователь |
| Оператор | Текущий статус, состояние машины, ручной SETUP/PLANNED_STOP и инциденты | Любой аутентифицированный пользователь |
| Аналитик | Периоды, смены, summary, timeseries, Pareto, chronometry | Любой аутентифицированный пользователь |
| Пользователь генерации | Scenario, validate, realtime/history/scheduled Run, stop/retry | Любой аутентифицированный пользователь |
| Bootstrap account | Добавление пользователей | Только начальная базовая учётная запись |

Имена UX-персон не превращаются в JWT roles. Один человек может выполнять все производственные сценарии. Enterprise ownership разделяет предметные данные, но не является пользовательской ACL.

## Системные акторы

| Actor | Ответственность |
|---|---|
| Scheduler | Запуск одноразовых scheduled runs и периодической обработки |
| Generator service | Воспроизводимая запись raw telemetry по неизменяемому snapshot Run |
| Telemetry writer | Короткая пакетная вставка, идемпотентность и best-effort realtime availability |
| State/calculation worker | Вычисление состояний, интервалов и агрегатов с атомарной публикацией |
| Maintenance worker | Создание partitions заранее и удаление истёкших raw partitions |

## Обязательная демонстрационная цепочка

1. Создать Enterprise, Shift, ProductionLine, Machine, Component и Signals; проверить readiness и активировать оборудование.
2. Создать Scenario на существующей Machine и запустить ограниченную realtime генерацию.
3. Убедиться, что Generator записывает raw values, а Analytics независимо публикует current state и текущие сигналы.
4. Запустить исторический Run и прочитать подготовленные summary, series, Pareto и chronometry для выбранных `shiftId`/периода.
5. Добавить ручной incident или интервал SETUP/PLANNED_STOP, дождаться фоновой публикации и проверить изменённые read models.
6. Проверить scheduled Run, конфликты дублирующего запуска и видимость lag/error/drop в мониторинге.

## Явные границы demo

- История ограничена 90 сутками raw; realtime потеря отдельных буферизованных пакетов допустима и наблюдаема.
- Один historical execution на минимальном стенде; аналитическое чтение всегда использует последнюю committed projection.
- Полностью автоматический DNS certificate renewal зависит от Yandex Cloud DNS service-account credentials; секреты задаются только на deployment host.
