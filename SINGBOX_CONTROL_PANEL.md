# Панель управления sing-box

Раздел `Hysteria 2` переименован в `sing-box` и перенесён на маршрут
`#/singbox`. Старый `#/hysteria2` автоматически перенаправляет на новый адрес.

## Что находится в разделе

- состояние feature flag и процесса sing-box;
- PID работающего процесса;
- live stdout/stderr с обновлением раз в 3 секунды;
- ручное обновление, пауза и очистка кольцевого буфера логов;
- путь runtime-конфига;
- настройки Hysteria 2 как отдельного inbound sing-box;
- TLS, ALPN, Salamander, bandwidth и masquerade;
- обезличенный предпросмотр сгенерированного конфига.

Логи доступны только sudo-администраторам. В памяти хранится до 500 последних
строк. После перезапуска контейнера история начинается заново.

## API

Основные адреса:

```text
GET    /api/singbox
PUT    /api/singbox
POST   /api/singbox/generate
GET    /api/singbox/runtime-config
GET    /api/singbox/logs?limit=500
DELETE /api/singbox/logs
```

Старые адреса `/api/hysteria2...` сохранены как совместимые алиасы.

## Установка

Frontend нужно пересобрать, затем пересобрать и пересоздать контейнер:

```bash
cd app/dashboard
npm install --no-audit --no-fund
VITE_BASE_API=/api/ npm run build -- --outDir build --assetsDir statics
cp build/index.html build/404.html
cd ../..

docker compose -f docker-compose.yml -f compose.singbox-hysteria.yml build --no-cache marzban
docker compose -f docker-compose.yml -f compose.singbox-hysteria.yml up -d --no-deps --force-recreate marzban
```

Проверка API внутри браузера выполняется автоматически при открытии раздела.
В логах процесса должны появиться строки запуска и собственный вывод sing-box.
