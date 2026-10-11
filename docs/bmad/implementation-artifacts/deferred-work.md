- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-1-4-public-edge-and-observability.md`
  summary: Инструментировать и проверить domain metrics ingestion, generation, projections и calculation jobs после появления соответствующих runtime operations.
  evidence: Story 1.4 создаёт их dashboards и alerts, но текущие приложения ещё не реализуют telemetry/calculation capabilities, поэтому live batch и рост custom series станут проверяемыми в последующих domain stories.
- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-2-1-enterprise-and-shift-calendar.md`
  summary: При реализации telemetry first-use writer и analytics projection writer согласовать их транзакции с блокировкой строки Enterprise, используемой timezone- и shift-lock проверками.
  evidence: Текущие writers ещё не реализованы; спецификация ingestion задаёт advisory lock на signal, но не подтверждает сериализацию по Enterprise, а projection writer пока отсутствует. Проверить обе транзакционные последовательности при появлении writers и добавить конкурентные проверки timezone/shift usage.
