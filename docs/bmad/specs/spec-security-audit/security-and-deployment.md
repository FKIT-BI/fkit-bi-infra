# Правила безопасности и развёртывания

## Аутентификация

- Analytics и Generator используют единую границу доверия JWT; каждая публичная операция требует `Authorization: Bearer <token>`.
- Все аутентифицированные пользователи имеют одинаковые права. В MVP не добавлять claims ролей и проверки RBAC.
- Первую базовую учётную запись создаёт оператор при развёртывании; только она может добавлять пользователей через минимальную форму. Это единственное выделенное право, не ролевая модель.
- Пароли хранятся как BCrypt-хэш; исходный пароль после создания не возвращается и не логируется.
- Analytics — единый issuer токенов для обоих приложений; login принимает `username/password`, JWT содержит `sub=userId`, `iss=fkit-bi`, `aud=fkit-bi-api`, `iat`, `exp` и не содержит role claims. Generator только проверяет токен.
- MVP подписывает JWT `HS256` одним случайным секретом не короче 256 бит; Analytics и Generator получают его из внешнего deployment secret. Секрет не хранится в БД, Liquibase, image или репозитории. При компрометации секрет заменяется с принудительным истечением всех токенов; key-id и параллельная ротация вне MVP.
- Access token действует 30 минут; refresh token отсутствует. Frontend держит access token в `sessionStorage`; logout очищает его на клиенте. После истечения пользователь входит снова.
- Первая bootstrap-учётная запись создаётся одноразовой deployment-командой только при пустой таблице users; секрет начального пароля поступает извне. При непустой таблице команда не изменяет учётные записи.
- Только bootstrap-user может вызвать `POST /api/v1/auth/users`; право проверяется по immutable bootstrap marker в БД, а не изменяемому JWT claim. Форма принимает `username`, `displayName`, `initialPassword`; username уникален без учёта регистра. Созданный пользователь получает обычные права.
- Login: `POST /api/v1/auth/login`; остальные business endpoints требуют Bearer. Request/response и abuse limits заданы в `fkit-bi-infra/docs/contracts/auth-api.yaml`.
- `author` в ManualIncident и ручных интервалах остаётся необязательным непроверенным display-полем; одна аутентификация не подтверждает его достоверность. Полный аудит исключён.

## Nginx и TLS

- Nginx — публичный reverse proxy и точка завершения TLS для `*.bi.kitexp.ru`; он передаёт Authorization обоим сервисам и перезаписывает client-IP forwarding header, используемый login rate limiter.
- На host публикуются TCP 80 и 443 для Nginx; во время перехода сохраняется существующий IP endpoint на настроенном `PUBLIC_PORT`. Nginx принимает запросы и по IP, и по доменному имени. Analytics и Generator (8080), web (80) и PostgreSQL (5432) доступны только внутри Compose network, без собственных host ports.
- Поддерживаются два явных режима: публичный сертификат, автоматически выпускаемый/обновляемый Certbot, и самоподписный режим для демонстрации/разработки. Режим выбирается конфигурацией deployment (`TLS_MODE=public|self-signed`); автоматизация не должна незаметно переключаться на self-signed при сбое public issuance. Самоподписный сертификат не является доверенным в публичных клиентах, пока его CA не установлен в trust store.
- Для wildcard Let’s Encrypt используется DNS-01, не HTTP-01. DNS управляется в Yandex Cloud DNS; Certbot автоматизируется auth/cleanup hooks, которые вызывают Yandex Cloud DNS API. Не закреплять старый/непроверенный plugin без проверки его совместимости и поддержки. Service account получает минимальный `dns.editor` на нужную зону; credential устанавливается как deployment secret.
- Основной публичный host MVP — `bi.kitexp.ru`; сертификат включает SAN `bi.kitexp.ru` и `*.bi.kitexp.ru`. Wildcard покрывает один уровень поддоменов, но не apex.
- IP остаётся доступен как дополнительный адрес приложения. Публичный сертификат для домена не подтверждает IP literal: до отдельного решения IP-вход доступен по HTTP, а HTTPS гарантируется для домена; TLS-запрос к IP может показать предупреждение о несовпадении сертификата.
- В публичном TLS-режиме домена порт 80 используется для ACME и/или перенаправления на HTTPS. При продлении сертификата deploy hook проверяет и перезагружает Nginx. Для self-signed режима сертификат создаётся автоматически при отсутствии persistent certificate, но клиентам потребуется доверие к нему; публичный режим не меняется автоматически при ошибке выпуска.
- Prometheus, Grafana, exporters и метрики остаются доступны только через loopback/SSH или Compose network и не публикуются маршрутами Nginx.

## Сохраняемые контроли

- В тестовом контуре использовать один общий PostgreSQL account для Analytics, Generator, Liquibase и postgres_exporter; отдельные DB roles отложены. Секрет account и остальные deployment secrets хранятся вне Git. Перед production или внешними данными требуется минимально привилегированное разделение.
- Сохранять ограничения диапазонов API и пагинации, лимиты DB pools и query timeout, параметризованный SQL и действующие контроли ingestion.
- Ошибки аутентификации используют общую структурированную форму API-ошибки. Пароли, bearer-токены, ключи подписи и DNS API credentials никогда не записываются в логи.

## Поставка DNS credentials

DNS service-account credentials поставляются как deploy-time secret mount/environment, имеют минимальные права на целевую DNS zone и не попадают в git, image layers, Compose logs или HTTP responses. Самоподписный режим от них не зависит.

Статус технических auth defaults: `DECIDED`. Отдельный Auth OpenAPI v1.0.0 фиксирует login, bootstrap-only user create и abuse limits; transport contract готов до реализации auth endpoints.
