# Hysteria 2 / Xray: первый этап переработки

Новый app/subscription/hysteria2.py задаёт общую модель клиентского профиля.
Ссылки, Xray JSON, sing-box и Clash Meta используют общие правила и сериализаторы.
Проверяются TLS, transport/version, порт, auth и Salamander. Исправлены IPv6 URI,
кодирование credentials, строковые boolean и ALPN. Общий Mux/dialer не возвращён.

## Совместимость
Для совместимости пользовательские obfs/obfs_password являются overlay над
host/inbound во ВСЕХ форматах. Непустой пользовательский пароль может заменить
унаследованный пароль, сохранив режим Salamander. Значение obfs=none явно
отключает obfs для экспортируемого профиля. Эти значения обязаны совпадать с
фактическим сервером; панель не меняет transport finalmask при правке пользователя.
БД и серверный конфиг не изменены. Перед установкой проверить пользователей
с индивидуальным obfs и перенести намеренные параметры в host/inbound.

## Ограничения — не готовая production-переработка
Валидация пока выполняется при экспорте, не при сохранении через API.
Новый ValueError может прервать генерацию всей подписки при неверном профиле.
Сначала проверить существующие параметры в тестовой копии. Миграция, API-ошибки,
серверная модель, отдельная форма Hysteria, gRPC и реальное подключение — следующие этапы.
Произвольные finalmask, Gecko, bandwidth/quicParams и port hopping не реализованы.
Пул портов через запятую выбирает один порт, как раньше.

## Проверки
17 новых тестов профиля + 19 Xray JSON + 14 inbound = 50 успешных локальных тестов.
Тесты профиля используют реальный независимый модуль; старые тесты извлекают
классы через AST и подставляют реальный новый модуль, не его заглушку.
Полный pytest, запуск приложения с БД, xray run -test и сетевое подключение не выполнены.

Из корня проекта:
python -m unittest discover -s tests -p test_hysteria2_profile.py -v
python -m unittest discover -s tests -p test_hysteria2_xray_json.py -v
python -m unittest discover -s tests -p test_hysteria2_inbound.py -v

## Архив и применение
Накопительный архив на основе marzban-terminal-ui-01.zip, с тремя предыдущими
исправлениями Hysteria. Исходники оформления сохранены; их production-сборка
по-прежнему не выполнена, см. TERMINAL_UI_NOTES.md.
Для выборочного применения: новый app/subscription/hysteria2.py, генераторы
v2ray.py/singbox.py/clash.py и три test_hysteria2_{profile,xray_json,inbound}.py.
Схема БД не меняется. Для отката восстановить файлы из предыдущего архива.

Коммит: refactor(hysteria2): unify client profiles and subscription exporters
