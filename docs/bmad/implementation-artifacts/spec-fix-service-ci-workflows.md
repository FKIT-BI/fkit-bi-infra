---
title: 'Исправить CI delivery-workflow сервисов'
type: 'bugfix'
created: '2026-10-04'
status: 'in-progress'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** GitHub Actions трёх сервисов немедленно завершается с ошибкой разбора workflow, поэтому не публикует образы и не выполняет Dev-доставку.

**Approach:** Исправить синтаксис общего шага входа в GHCR, проверить YAML и запустить delivery из `develop` повторно.

</frozen-after-approval>

## Implementation Notes

- Исправлены три отсутствующие закрывающие фигурные скобки в inline-map `with` шага `docker/login-action`; именно они делали workflow непарсируемым GitHub Actions.
