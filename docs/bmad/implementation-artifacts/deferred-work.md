- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-1-4-public-edge-and-observability.md`
  summary: Инструментировать и проверить domain metrics ingestion, generation, projections и calculation jobs после появления соответствующих runtime operations.
  evidence: Story 1.4 создаёт их dashboards и alerts, но текущие приложения ещё не реализуют telemetry/calculation capabilities, поэтому live batch и рост custom series станут проверяемыми в последующих domain stories.
