- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-1-4-public-edge-and-observability.md`
  summary: Инструментировать и проверить domain metrics ingestion, generation, projections и calculation jobs после появления соответствующих runtime operations.
  evidence: Story 1.4 создаёт их dashboards и alerts, но текущие приложения ещё не реализуют telemetry/calculation capabilities, поэтому live batch и рост custom series станут проверяемыми в последующих domain stories.
- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-2-1-enterprise-and-shift-calendar.md`
  summary: При реализации telemetry first-use writer и analytics projection writer согласовать их транзакции с блокировкой строки Enterprise, используемой timezone- и shift-lock проверками.
  evidence: Текущие writers ещё не реализованы; спецификация ingestion задаёт advisory lock на signal, но не подтверждает сериализацию по Enterprise, а projection writer пока отсутствует. Проверить обе транзакционные последовательности при появлении writers и добавить конкурентные проверки timezone/shift usage.
- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-epic-2-equipment-configuration.md`
  summary: Web owner должен завершить story 2.5: при открытии существующей машины загружать сохранённую MachineStateConfig, чтобы повторное сохранение не затирало её дефолтным черновиком.
  evidence: Review обнаружил, что текущий Web flow получает readiness/components/signals, но не вызывает документированный `GET /machines/{machineId}/state-configuration`; backend API и OpenAPI уже предоставляют чтение.
- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-epic-2-equipment-configuration.md`
  summary: Web owner должен предоставить по AC-1 создание двух смен предприятия до завершения setup journey.
  evidence: Acceptance Catalog AC-1 требует создать Enterprise с двумя непересекающимися shift definitions; существующий UI показывает выбор timezone, но не вызывает `POST /enterprises/{enterpriseId}/shifts`, хотя Analytics API/OpenAPI поддерживают создание смен.
- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-epic-2-equipment-configuration.md`
  summary: Web owner должен дать оператору возможность задавать собственный `customSemanticCode` для Signal с `semanticCode=CUSTOM`.
  evidence: Текущая форма жёстко отправляет `CUSTOM_VALUE`; Analytics валидирует стабильный код от клиента и контракт уже публикует поле.
- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-epic-2-equipment-configuration.md`
  summary: Web owner должен решить и реализовать редактирование/отключение существующих конфигурационных объектов в UX.
  evidence: Текущий интерфейс сценария настройки содержит создание объектов, но не редактирование и смену статусов, хотя Analytics API предоставляет соответствующие CRUD/status операции; ответственность за UI закреплена за Web-разработчиком.
- source_spec: none
  summary: Story 1.5 «Backup and restore operations» отложена до отдельного решения о сроках резервного копирования.
  evidence: Пользователь попросил пока отложить резервное копирование и продолжить дальнейшие работы; ежедневные dumps, retention, age monitoring и restore drill не входят в текущую итерацию.
# Epic 4 review follow-ups
- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-epic-4-historical-projections-and-query-api.md`
  summary: Проверить fallback gaps для timeline, где присутствует только часть effective state intervals.
  evidence: Текущий fallback подавляется при наличии любого effective interval; подтвердить влияние после появления Epic 5 manual overlays тестом смешанной timeline.
- source_spec: `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-epic-4-historical-projections-and-query-api.md`
  summary: Объединить автоматические loss facts с ручными причинами/classifications в read-моделях.
  evidence: Epic 4 rollups описывают вычисляемые факты, а ручные incident overlays реализуются в Epic 5; проверить Pareto и chronometry после добавления overlays.
