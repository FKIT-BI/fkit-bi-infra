---
title: '1.1 — Основа приложений Analytics и Generator'
type: 'feature'
created: '2026-10-10'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'f9dac3359f7abaa33b5b761ae924dcefd7703f6f'
context:
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/epic-1-context.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-mvp-acceptance-strategy/operations-decisions.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Analytics и Generator пока минимальны: у них нет согласованных версий Spring Boot, общего формата API-ошибок, request trace ID и health probes.

**Approach:** Подготовить обе службы к следующим историям: выровнять принятый Java/Spring baseline, сохранить JDBC/Ports-and-Adapters и реализовать общие health probes, `ErrorResponse` и bounded `X-Trace-Id` на успехе и ошибке. Миграции, JWT и Nginx forwarding остаются вне этой истории.

## Boundaries & Constraints

**Always:** Java 21, Spring Boot 3.5.16 и JDBC; `ErrorResponse` содержит `code`, `message`, `traceId`, `fieldErrors[]`, `details`; корректный ограниченный входной `X-Trace-Id` сохраняется, иначе создаётся UUID; тот же ID возвращается в заголовке каждого ответа и в error body. Не логировать секреты или request payload; сохранять package boundaries и не вводить JPA.

**Never:** Не менять бизнес-контракты/БД, не реализовывать Liquibase, JWT, TLS или metrics stack и не менять публичный Dev. Передача trace header proxy настраивается в 1.4.

## I/O & Edge-Case Matrix

| Сценарий | Вход/состояние | Ожидаемое поведение | Ошибка |
|---|---|---|---|
| Корреляция | Валидный, отсутствующий, некорректный или oversized `X-Trace-Id` | Валидный bounded ID сохраняется, иначе генерируется UUID; он возвращается в header и error body | Некорректный ID заменяется, чувствительный input не логируется |
| Ошибка/health | Malformed JSON, validation/500 или startup failure | Общая ошибка и Actuator liveness/readiness отражают итоговое состояние | Не выдавать stack trace/секреты; сломанное приложение не готово |

</frozen-after-approval>

## Code Map

- `fkit-bi-analytics/pom.xml`, `src/main/resources/application.yml`, `AnalyticsApplication.java`, `AnalyticsApplicationTest.java` — текущие версии 3.5.0, datasource, Actuator и H2 smoke test.
- `fkit-bi-generator/pom.xml`, `src/main/resources/application.yml`, `GeneratorApplication.java`, `GeneratorApplicationTest.java` — второй skeleton; не менять `telemetry/JdbcTelemetrySink`.
- `fkit-bi-infra/docs/bmad/specs/spec-analytics-api-contract/api-conventions.md`, `spec-generator-api-contract/api-conventions.md`, `spec-mvp-acceptance-strategy/operations-decisions.md` — нормативные ErrorResponse, trace и logging rules.
- `fkit-bi-infra/scripts/validate.sh` и service `.github/workflows/ci.yml` — проверки сборки/delivery. Сохранить guarded deployment; не изменять/повторять ранее завершённые delivery-intents.

## Tasks & Acceptance

**Execution:**

- [x] Оба backend `pom.xml` и `application.yml` — выровнять Spring Boot 3.5.16 и probes, сохранив Java 21, JDBC и ownership миграций.
- [x] Оба backend — реализовать ErrorResponse/trace filter и тесты success, malformed JSON, validation, sanitized 5xx, liveness/readiness; записать evidence в `docs/tasks/`.
- [x] Прогнать обе Maven verify и infra validation; проверки прошли.

**Acceptance Criteria:**

- Given чистый checkout, when обе службы собраны, then Java 21/Spring Boot 3.5.16 и `./mvnw verify` проходят без изменения TelemetrySink/API boundaries.
- Given HTTP success либо malformed/invalid/failed request, when Analytics или Generator отвечает, then `X-Trace-Id` bounded и одинаков в response/error; body имеет общий контракт, корректный статус, без stack trace/секретов.
- Given успешный startup либо его сбой, when проверяется Actuator, then liveness/readiness отражают состояние процесса; неготовая служба не проходит Compose healthcheck.

## Implementation Notes

- Both services use a 1–128 character ASCII allowlist for incoming `X-Trace-Id`; invalid or oversized values are replaced with a UUID. The response header is set by the ingress filter; API errors repeat the same value in `ErrorResponse`.
- Common errors do not include exception messages, stack traces, submitted field values, or request payloads. Unexpected failures log only the stable error code and trace ID.
- Liveness/readiness groups expose Spring process state; readiness is verified as `OUT_OF_SERVICE`/503 when the application refuses traffic. Compose healthchecks call `/actuator/health/readiness`; database/schema readiness is deferred to Story 1.2.

## Spec Change Log

## Review Triage Log

| Находка | Вердикт и свидетельство | Маршрут |
|---|---|---|
| Blind Hunter: framework-ошибки неизвестного маршрута/метода попадают в общий handler | medium — общий `@ExceptionHandler(Exception.class)` превращал достижимые HTTP 404/405 в 500, нарушая API-конвенции; проверено запросами. | patch |
| Blind Hunter: нет отдельного покрытия неизвестного маршрута и неподдерживаемого метода | medium — покрытие действительно отсутствовало; оба сценария воспроизводят неверный статус из предыдущей находки и будут закреплены тестами после исправления. | patch; сгруппировано с находкой выше по общей причине |
| Blind Hunter: method-parameter validation может стать 500 | medium — Spring `HandlerMethodValidationException` не обрабатывался узким validation handler и попадал в общий 500; проверено тестом с ограничением параметра. | patch |
| Edge Case Hunter: тот же пробел для `HandlerMethodValidationException` | medium — подтверждает ту же причину и результат, что находка Blind Hunter; отдельный тест и исправление закрепят 422. | patch; сгруппировано с находкой о method validation |
| Blind Hunter: нет проверки совпадения сгенерированного trace ID в error header/body | low — реализация использует один request attribute, но сочетание отсутствующего входного ID и error response не было напрямую проверено; добавлен тест этого контракта. | patch |
| Blind Hunter: readiness refusal не проверяет независимость liveness | low — состояние `REFUSING_TRAFFIC` меняет readiness, но liveness должен оставаться UP; ранее такой инвариант не был проверен. | patch |
| Blind Hunter: полное тело 500 не проверяется на текст секрета | false — handler строит body только из фиксированных `code/message`, trace ID, пустых `fieldErrors/details`; исключение и его текст в сериализуемую модель не передаются. | reject |
| Blind Hunter: нет multi-field validation test | low — mapper обходит все `FieldError` через stream, но тест проверял только один; покрытие нескольких путей добавлено. | patch |
| Edge Case Hunter: нет теста ровно 128 символов `X-Trace-Id` | low — regex явно допускает до 128, однако верхняя включительная граница не была закреплена тестом; добавлена проверка точной границы. | patch |
| Verification Gap Reviewer: нет теста ровно 128 символов `X-Trace-Id` | low — подтверждённый пробел покрытия той же границы, что и предыдущая находка; учтён отдельной строкой, исправляется тем же тестом. | patch; сгруппировано с находкой выше |

## Verification

**Commands and results (2026-10-10):**

- Both services: `./mvnw verify -q` in the Java 21 Maven container — passed; thirteen application/HTTP tests each.
- Infra: `./scripts/validate.sh` — passed; Compose, delivery stubs, shell/workflow checks completed without deployment.
- HTTP coverage includes success, valid/missing/invalid/128-character/oversized trace IDs, generated trace equality in error header/body, malformed JSON, single-/multi-field and parameter validation, sanitized 5xx, 404/405 framework errors, successful and refusing liveness/readiness. Liquibase/schema readiness is deferred to Story 1.2.
- Detailed evidence is recorded in each repository's `docs/tasks/1-1-application-foundations.md`.
