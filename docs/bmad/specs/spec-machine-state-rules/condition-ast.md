# Condition AST

## Узлы

| `type` | Поля | Правило |
| --- | --- | --- |
| `ALL` | `conditions[1..N]` | Логическое AND |
| `ANY` | `conditions[1..N]` | Логическое OR |
| `NOT` | `condition` | Ровно один дочерний узел |
| `COMPARE` | `signalId`, `operator`, operand | Сравнение usable signal value с literal |

Ограничения одной MachineStateConfig: максимум 20 rules, глубина AST 10 и суммарно 100 nodes. Пустые `ALL/ANY`, лишние поля оператора и межмашинные signal references отклоняются.

## Операторы и operands

| Operator | Operand | Семантика |
| --- | --- | --- |
| `EQ` | `value`, для DOUBLE также `tolerance` | Равенство |
| `NE` | `value`, для DOUBLE также `tolerance` | Неравенство |
| `GT` | `value` | `actual > value` |
| `GTE` | `value` | `actual >= value` |
| `LT` | `value` | `actual < value` |
| `LTE` | `value` | `actual <= value` |
| `BETWEEN` | `lower`, `upper` | Включительно: `lower <= actual <= upper` |
| `IN` | `values[1..50]` | Точное попадание в набор уникальных literals |

Отрицательные set/range условия выражаются через `NOT`, отдельные `NOT_IN` и `NOT_BETWEEN` не вводятся. Строгий диапазон выражается `ALL` с `GT` и `LT`.

## Совместимость типов

| Signal `valueType` | Operators |
| --- | --- |
| `DOUBLE` | `EQ`, `NE`, `GT`, `GTE`, `LT`, `LTE`, `BETWEEN` |
| `LONG` | `EQ`, `NE`, `GT`, `GTE`, `LT`, `LTE`, `BETWEEN`, `IN` |
| `BOOLEAN` | `EQ`, `NE` |
| `STRING` | `EQ`, `NE`, `IN` |

Literal должен иметь соответствующий тип; string/boolean/number coercion отсутствует. Для DOUBLE допустим конечный JSON number; целый JSON literal нормализуется в DOUBLE. Для LONG требуется целое в диапазоне BIGINT.

String comparison регистрозависимо, без trim и normalization. Все literals интерпретируются в текущем `unitCode` сигнала; evaluator не преобразует единицы и не округляет actual value.

## DOUBLE equality

Для `DOUBLE + EQ/NE` обязателен конечный `tolerance > 0` в единицах сигнала:

```text
EQ = abs(actual - value) <= tolerance
NE = abs(actual - value) > tolerance
```

Для других операторов tolerance запрещён. `NaN` и infinity не проходят ingestion и configuration validation.

## UNKNOWN до сравнения

Если usable value отсутствует или stale, любой COMPARE, включая `NE`, возвращает `UNKNOWN`. Отсутствие данных никогда не трактуется как неравенство.

## Исключённые выражения

MVP не поддерживает signal-to-signal comparison, арифметику, aggregates/windows, rate/delta, changed-within, regex, SQL, SpEL, JavaScript или иной исполняемый текст.
