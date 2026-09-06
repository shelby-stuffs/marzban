# Hysteria 2 / sing-box: отдельные настройки

## Что изменилось

В панели появился самостоятельный маршрут `#/hysteria2`. Его настройки
сохраняются в `/var/lib/marzban/hysteria2-settings.json` и являются источником
для server-конфига sing-box. Xray-конфиг больше не является runtime-источником
после первого сохранения этой страницы.

Раздел содержит:
- включение inbound;
- тег, listen address и UDP-порт;
- upload/download bandwidth и ignore_client_bandwidth;
- Salamander и генератор серверного пароля;
- пути к TLS certificate/key внутри контейнера;
- ALPN;
- masquerade URL;
- обезличенный предпросмотр итогового sing-box JSON и число пользователей.

## Автозаполнение

Кнопка «Автозаполнение» сначала ищет старый Hysteria inbound в
`xray_config.json` и переносит из него порт, listen, сертификаты, ALPN,
Salamander и bandwidth. Если старого inbound нет, используются безопасные
значения по умолчанию и пути `UVICORN_SSL_CERTFILE`/`UVICORN_SSL_KEYFILE`, если
они заданы. Случайный Salamander-пароль создаётся только когда старого пароля
нет.

Автозаполнение не сохраняет значения автоматически. Администратор видит и
проверяет пути сертификатов перед нажатием «Сохранить и применить».

## Применение

1. API валидирует типы и конфликты параметров.
2. Из активных пользователей собираются только `proxies.hysteria.auth`.
3. Формируется native `type: hysteria2` конфиг sing-box.
4. Выполняется `sing-box check` во временном файле.
5. Отдельные настройки сохраняются атомарно.
6. Обновляются виртуальные Hysteria metadata для Hosts и подписок.
7. Очищается кэш подписок.
8. Runtime-конфиг сохраняется атомарно и sing-box перезапускается.

В предпросмотре пользовательские auth и Salamander-пароль заменяются на `***`.

## Docker

```bash
docker compose -f docker-compose.yml -f compose.singbox-hysteria.yml build marzban
docker compose -f docker-compose.yml -f compose.singbox-hysteria.yml up -d marzban
```

Пути сертификата и ключа должны существовать внутри контейнера. Каталог
`/var/lib/marzban` уже примонтирован, поэтому практичный вариант:

```text
/var/lib/marzban/certs/hysteria2-fullchain.pem
/var/lib/marzban/certs/hysteria2-privkey.pem
```

## Граница этапа

Старый Hysteria inbound может оставаться в `xray_config.json` как материал для
первого автозаполнения, но при включённом feature flag он удаляется из runtime
Xray. После сохранения отдельного файла sing-box использует только его.
Автоматическое физическое удаление старого JSON пока не выполняется, чтобы не
делать необратимую миграцию без подтверждения.

Учёт Hysteria-трафика по пользователям и Hysteria на нодах в этот этап не входят.

Коммит:

`feat(hysteria2): add dedicated sing-box settings and config generator`
