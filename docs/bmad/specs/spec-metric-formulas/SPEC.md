---
id: SPEC-metric-formulas
companions:
  - metrics-catalog.md
  - aggregation-and-comparison.md
  - numeric-examples.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт формул производственных показателей demo MVP.

# Формулы производственных показателей

## Why

Machine, line и enterprise должны показывать одинаково рассчитанные показатели независимо от периода и количества минутных buckets. Формулы должны сохранять согласованный смысл состояний, не скрывать отсутствие исходных данных и не усреднять готовые проценты.

## Capabilities

- **CAP-1**
  - **intent:** Analytics может однозначно вычислить временные показатели оборудования.
  - **success:** State durations без double count раскладываются в covered, planned production, operating и productive time и дают согласованные Availability и data coverage.

- **CAP-2**
  - **intent:** Analytics может вычислить производительность и качество из выпуска и настроек машины.
  - **success:** Output, ideal output, Performance, Quality и OEE имеют однозначные формулы, единицы и null semantics и не требуют сохранения готовых ratios.

- **CAP-3**
  - **intent:** Analytics может отдельно показывать остановки, отказы и восстановления.
  - **success:** Один state timeline детерминированно даёт `stopCount`, `failureCount`, `recoveryCount`, MTBF и MTTR.

- **CAP-4**
  - **intent:** Пользователь может получить показатели линии и предприятия.
  - **success:** API сначала суммирует совместимые additive facts машин, затем вычисляет ratios и не складывает выпуск несовместимых production units.

- **CAP-5**
  - **intent:** Пользователь может сравнить выбранный период с непосредственно предшествующим сопоставимым периодом.
  - **success:** Обычный период сравнивается с равным предыдущим интервалом, а экземпляр смены — с предыдущим occurrence той же Shift; каждый результат ограничен своими закрытыми минутами.

## Constraints

- Нормативный каталог формул и null semantics находятся в `metrics-catalog.md`.
- Правила scope aggregation и previous period находятся в `aggregation-and-comparison.md`.
- Проверочные расчёты находятся в `numeric-examples.md`.
- Хранятся только additive durations, quantities и event counts; ratios вычисляются при чтении.
- Отсутствующее исходное значение не подменяется нулём.
- Ratio с отсутствующим или неположительным denominator равен `null`.
- Performance не ограничивается значением 100%.
- Низкий data coverage не переписывает автоматически бизнес-показатели.

## Non-goals

- Отраслевые варианты OEE и пользовательские формулы показателей.
- Коррекция выпуска по рецептам, партиям, продуктам или весовым коэффициентам.
- Попарное связывание каждого failure с отдельным repair event.
- Автоматическое исправление неверного nominal rate или аномальных COUNTER-значений.
- Окончательные DTO аналитического API и визуальное форматирование процентов.

## Success signal

Для одного набора минутных machine facts backend получает одинаковые показатели во всех API: машинные значения совпадают с проверочными примерами, line/enterprise ratios выводятся из суммарных numerators и denominators, а отсутствие счётчика, норматива или совместимой единицы возвращает `null`, не ложный ноль.
