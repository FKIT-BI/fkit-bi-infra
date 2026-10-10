# Нормативный каталог состояний

| State | Бизнес-смысл | Класс |
| --- | --- | --- |
| `RUN` | Machine выполняет производственный цикл | Productive и operating time |
| `IDLE` | Machine доступна, но не выпускает продукцию | Operating time; performance loss |
| `DOWN` | Machine незапланированно неработоспособна | Unplanned availability loss |
| `SETUP` | Переналадка, смена инструмента, подготовка, калибровка | Planned operational availability loss |
| `PLANNED_STOP` | Заранее известная остановка, исключённая из производственного плана | Visible excluded time |
| `OFFLINE` | Телеметрии недостаточно для достоверного user state | Data gap |

`OFFLINE` не означает физическую остановку оборудования, не является `DOWN`, не создаёт automatic loss reason и не должен маскироваться manual overlay в data-quality представлении.

## Transitions

Жёсткой матрицы user transitions нет: rules могут перевести `RUN`, `IDLE`, `DOWN`, `SETUP` и `PLANNED_STOP` в любое другое user state. `OFFLINE` назначается и снимается только system freshness policy.

Производственные события:

```text
failure = transition from any different state into DOWN
recovery = transition from DOWN into any state except DOWN or OFFLINE
```

Переход в `OFFLINE` не является stop/failure. Переход `OFFLINE -> DOWN` показывает обнаруженный `DOWN`; downstream MTBF/MTTR обязаны учитывать data coverage, потому что фактическое начало отказа могло находиться внутри gap.

Manual `SETUP/PLANNED_STOP` изменяет effective business state, но underlying calculated state остаётся доступным.
