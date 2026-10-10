---
id: SPEC-machine-state-rules
companions:
  - configuration-model.md
  - condition-ast.md
  - evaluator-semantics.md
  - evaluation-examples.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт декларативной конфигурации и вычисления состояния машины.

# Декларативные правила состояния машины

## Why

Генератор передаёт сырые сигналы, но официальное операционное состояние должна одинаково восстанавливать analytics для realtime и history. Нужна безопасная типизированная DSL без исполняемого пользовательского кода, с детерминированными priority, delay, hysteresis, quality и event-time semantics.

## Capabilities

- **CAP-1**
  - **intent:** Пользователь может атомарно настроить одну текущую конфигурацию расчёта состояния машины.
  - **success:** Backend принимает только полностью валидные `defaultState`, `offlineAfterMs` и rules либо не изменяет сохранённую конфигурацию.

- **CAP-2**
  - **intent:** Пользователь может выразить условия над сигналами типизированным декларативным AST.
  - **success:** `ALL`, `ANY`, `NOT` и `COMPARE` принимают только разрешённые signal-to-literal операции, а исполняемый код и межмашинные ссылки отклоняются.

- **CAP-3**
  - **intent:** Система может детерминированно выбрать состояние при одновременных, дребезжащих или пересекающихся условиях.
  - **success:** `OFFLINE` проверяется первым, затем unique priority, activation/release delay и hysteresis дают единственный результат либо `defaultState`.

- **CAP-4**
  - **intent:** Система может оценить неполный или недостоверный snapshot без фиксации ложного правила.
  - **success:** Трёхзначная логика не активирует rule по `UNKNOWN`, освобождает активное правило после release delay и маркирует результат `DEGRADED`.

- **CAP-5**
  - **intent:** Система может отличить фактическое event time перехода от момента его обнаружения.
  - **success:** `effectiveFrom` учитывает непрерывное условие и delay, `detectedAt` фиксирует обработку, а late data может исправить прошлый переход без изменения семантики evaluator.

- **CAP-6**
  - **intent:** Frontend может проверить конфигурацию до сохранения и объяснить текущий результат.
  - **success:** Validate API возвращает структурированные ошибки, а результат оценки содержит `matchedRuleId` и `evaluationQuality`.

## Constraints

- Модель конфигурации, атомарное изменение и API определены в `configuration-model.md`.
- Нормативный AST, операторы и validation определены в `condition-ast.md`.
- Порядок, delay, hysteresis, priority и трёхзначная логика определены в `evaluator-semantics.md`.
- Сквозные критерии приведены в `evaluation-examples.md`.
- `OFFLINE` является системным состоянием и не может быть target пользовательского rule.
- Конфигурация не версионируется; хранится и исполняется только текущая.
- Каждый referenced signal принадлежит той же Machine и имеет `staleAfterMs`.
- AST не содержит скрипты, SQL, regex, арифметику, signal-to-signal сравнения и оконные операции.

## Non-goals

- Пользовательское состояние `UNKNOWN`.
- История версий MachineStateConfig и StateRule.
- Арифметические формулы и временные функции внутри AST.
- Межмашинные правила.
- Автоматический incident по переходу состояния.
- Политика автоматического исторического перерасчёта после изменения rules.

## Success signal

Одинаковый snapshot сигналов и одна MachineStateConfig всегда дают одинаковые state, matched rule, evaluation quality и event-time transition независимо от realtime или historical режима; невалидная конфигурация не сохраняется.
