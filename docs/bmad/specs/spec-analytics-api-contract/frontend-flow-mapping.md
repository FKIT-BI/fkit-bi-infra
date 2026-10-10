# Сопоставление frontend flow и API

| Пользовательский шаг | Основные operations | Правило запросов |
| --- | --- | --- |
| Открыть навигацию | `equipment-tree` + `operations/overview` | Структура кешируется отдельно, current cards poll; frontend объединяет по `machineId` |
| Найти машину | `equipment-tree?search=` | Backend возвращает совпавшие Machines с родительской Line; локальная фильтрация допустима после полной загрузки |
| Открыть карточку | `operations/current` + `analytics/summary` | Current не подчиняется историческому периоду; summary подчиняется глобальному context |
| Посмотреть телеметрию | featured values из `operations/current`, затем `telemetry/series` | Исторический signal graph загружается lazy по выбранному `signalId` |
| Изменить период/смену | summary, metric/loss series, Pareto | Один общий historical context; previous period вычисляет backend |
| Открыть хронометраж даты | `chronometry?shiftDate=` | Один ответ возвращает все Shift occurrences этой local date; optional `shiftId` сужает |
| Кликнуть loss bucket | chronometry выбранной local date | Frontend переносит context, но backend не хранит UI navigation state |
| Кликнуть Pareto reason | `state-intervals?lossReasonId=` | Таблица получает серверный filter, а не фильтрует только загруженную страницу |
| Зарегистрировать простой | `POST /machines/{id}/incidents` | Form может предзаполнить boundaries/state/reason из segment; сервер повторно валидирует |
| Проверить результат incident | incident response, затем poll affected analytics | Mutation не обещает немедленно обновлённые aggregates; `recalculating` объясняет задержку |
| Открыть журнал | enterprise cursor `incidents` | Filters line/machine/time/effect/reason/ongoing/includeCancelled применяет backend; строки уже содержат machine reference |
| Настроить предприятие | Enterprise → Shift/LossReason → Line | Вкладки загружаются отдельно; Shift не вложен в Enterprise update |
| Создать машины | create with optional `lineId`; batch assignments | Свободные Machines показываются отдельной группой и назначаются all-or-nothing |
| Настроить машину | Machine → Components → Signals → StateConfiguration | Каждая вкладка сохраняется независимо; giant configuration request отсутствует |
| Активировать машину | readiness → status ACTIVE | Status command атомарно повторяет readiness, поэтому состояние между запросами безопасно |
| Пересчитать историю | create recalculation → poll job | UI не держит HTTP открытым и продолжает показывать старую committed analytics |

## Context boundaries

| UI context | Затронутые blocks |
| --- | --- |
| Current moment | Overview, current state, latest signals; обновляется polling независимо |
| Historical range + optional Shift | Summary, metrics, losses, Pareto |
| Telemetry window | Один signal graph; собственные from/to/resolution |
| Chronometry local date | Все occurrences, начинающиеся в эту дату |
| Interval table filters | Собственный cursor и server filters; не обязан совпадать с global page pagination |

При переходе между Machines frontend сохраняет historical range и shift filter, если они допустимы для того же Enterprise. Response старой Machine не должен перезаписать новый selected context.

## Refresh и UI states

- Auto-refresh poll выполняется только для `operations/overview`, `operations/current` и при необходимости `telemetry/current`; historical endpoints перезапрашиваются после изменения context либо завершения затрагивающей mutation/recalculation.
- Рекомендуемый default poll — 5 секунд с отменой предыдущего запроса и паузой для невидимой вкладки; ручное обновление использует те же endpoints и сохраняет выбранный context.
- Initial loading показывает skeleton без данных предыдущей Machine. Background refresh сохраняет последний успешный ответ до получения нового.
- `200` с пустым `items/points` означает корректное отсутствие данных; `404` — отсутствующий ресурс; `partial/stale/recalculating` — готовый, но ограниченный результат; transport error не подменяется пустым ответом.
- После transport error frontend может оставить последнее успешное значение только с явной отметкой ошибки и времени последнего обновления.
