# Hysteria 2: пакеты исправлений 01 + 02 + 03

## Область изменений пакета 01
Генерация Xray JSON в app/subscription/v2ray.py и изолированные тесты.
Серверная конфигурация, база данных, интерфейс и другие форматы подписок не изменены.

- settings теперь содержит version: 2, address и port вместо servers/password.
- Добавлен streamSettings с method: hysteria, security: tls и hysteriaSettings.auth.
- Сохранены SNI, ALPN и явная настройка allowInsecure; проверка сертификата по умолчанию включена.
- Obfs из существующих метаданных перенесён в streamSettings.finalmask.udp.
- Пароль пользователя переопределяет пароль из шаблона, не изменяя сам шаблон.

## Проверки
Команда из корня проекта:

    python -m unittest discover -s tests -p test_hysteria2_xray_json.py -v

До исправления: 2 assertion failures, 7 errors (нет streamSettings), 1 passed (VLESS).
После исправления: 10/10 passed.

Тесты исполняют реальный класс генератора, извлечённый через AST, без запуска
app/__init__.py. Инициализация заменена минимальными шаблонами. Это НЕ проверка
импортов всего приложения, штатных шаблонов, API, БД или сетевого соединения.

python -m compileall -q app cli xray_api завершился успешно, с существующим
SyntaxWarning об escape-последовательности в xray_api/proto/compile.py.
Полный pytest не запускался: pytest и зависимости приложения не установлены.

## Совместимость и ограничения
Формат сверён с актуальной официальной документацией:
- https://xtls.github.io/en/config/outbounds/hysteria.html
- https://xtls.github.io/en/config/transports/hysteria.html
- https://xtls.github.io/en/config/transports/finalmask.html

В Dockerfile закреплён Xray v26.7.11. Исходники этого тега получить не удалось;
бинарник Xray в тестовом окружении отсутствует. Проверка через xray run -test
и реальное подключение НЕ выполнены. Этот пакет нельзя считать подтверждением
полной работоспособности Hysteria на сервере.

## Статус подозрительных мест
1. Исправлено в пакете 02: чтение Salamander из finalmask.udp и передача
   в метаданные подписок (подробности ниже).
2. Исправлено в пакете 03: обход общего Mux и неподключённого fragment/noise dialer.
3. Проверить создание/отзыв пользователя через gRPC и учёт трафика.
4. Проверить схемы inbound и обязательные поля version/users на закреплённом ядре.

## Применение
Архив содержит проект целиком. Для выборочного применения достаточно заменить
app/subscription/v2ray.py и добавить tests/test_hysteria2_xray_json.py.
Для пакета 02 также заменить app/xray/config.py и добавить
 tests/test_hysteria2_inbound.py. Архив 02 накопительный, включает пакет 01.
Сначала проверить в тестовом окружении. Для отката использовать исходный архив.

## Пакет 02: inbound -> obfs -> подписка
Изменён только участок Hysteria в app/xray/config.py:
- Salamander и пароль читаются из streamSettings.finalmask.udp[].settings.password.
- При наличии finalmask он имеет приоритет над legacy obfs/obfsPassword.
- Пустой finalmask не восстанавливает старые пароли из hysteriaSettings.
- Старые поля читаются только при отсутствии ключа finalmask. Это совместимость
  извлечения метаданных, НЕ автоматическая миграция серверного конфига.
- TCP-маски и неподходящие типы данных не принимаются за UDP Salamander.
- Настройки хоста по-прежнему могут переопределять пароль obfs.
- Исходный finalmask не изменяется.

Проверка:

    python -m unittest discover -s tests -p test_hysteria2_inbound.py -v
    python -m unittest discover -s tests -p test_hysteria2_xray_json.py -v

До пакета 02 не проходили 8 из 14 новых тестов из-за отсутствующих либо устаревших
метаданных obfs. После: 14/14 новых + 10/10 предыдущих тестов проходят.
Компиляция app, cli, xray_api также успешна.

Тесты выполняют реальные XRayConfig, process_inbounds_and_tags и генераторы
ссылок/Xray JSON/sing-box через AST, с тестовыми контекстом и шаблонами.
Это НЕ полная интеграция приложения и НЕ тест подключения к Xray.

Границы поддержки: проверен обычный Salamander с одним паролем. Экспорт всей
цепочки произвольных finalmask, Gecko/packetSize и нескольких Salamander-масок
этим пакетом не реализован: извлекается первый Salamander с непустым строковым
паролем. Для таких расширенных конфигураций нельзя считать полученную подписку
эквивалентом серверной конфигурации. Некорректные элементы пропускаются при
извлечении метаданных; проверять корректность исходного конфига должно ядро.


## Пакет 03: Mux / fragment / noise
Архив marzban-hysteria2-fix-03.zip накопительный: содержит пакеты 01, 02 и 03.

Подтверждено по коду генератора:
- Для Hysteria создавался Freedom outbound `dialer` с fragment/noises, но ссылка
  sockopt.dialerProxy в её streamSettings отсутствовала. Этот outbound не был
  подключён к транспорту Hysteria и мог приводить к конфликтам тегов с шаблоном.
- Общий mux_enable добавлял Mux.Cool поверх native Hysteria без проверки протокола.
- До завершения экспорта разбирались ненужные Hysteria параметры fragment/noise
  и JSON общего Mux-шаблона. Некорректные значения могли прерывать генерацию.

Исправление:
Ветка protocol=hysteria теперь сохраняет готовую конфигурацию и возвращается
до общего кода Freedom dialer/Mux. Шаблон подписки по-прежнему обрабатывается
через add_config. TLS, auth, Salamander из пакетов 01/02 сохранены.

Это намеренная политика экспортера для native Hysteria2: общие опции хоста
mux_enable, fragment_setting и noise_setting не применяются к её Xray JSON.
Она согласуется с уже существующими ранними возвратами Hysteria в генераторах
Clash Meta и sing-box. UI и БД не менялись: опции могут оставаться видимыми и
сохранёнными, но при экспорте Hysteria игнорируются. Другие протоколы сохраняют
прежний код генерации. VLESS поверх Hysteria-транспорта отдельно не изменялся.

Важно: fragment — TCP-фрагментация; Freedom noises — именно UDP-шум, а не
TCP-функция. Фикс НЕ утверждает, что UDP-шум принципиально невозможен с QUIC.
Он убирает неподключённый Freedom dialer в текущем генераторе; поддержку
UDP-шумов через согласованный finalmask нужно проектировать отдельно.
Документация:
- https://xtls.github.io/en/config/outbound.html (Mux.Cool / XUDP)
- https://xtls.github.io/en/config/outbounds/freedom.html (fragment / noises)
- https://xtls.github.io/en/config/transports/hysteria.html (QUIC transport)

Проверки пакета 03:
Добавлено 9 регрессионных тестов (7 проверок Hysteria, 2 контрольных VLESS).
До исправления не проходили 7 новых проверок, после — все проходят.
Итого: 19 тестов Xray JSON + 14 тестов inbound = 33 успешных теста.
Компиляция app, cli, xray_api успешна.
Ограничения из предыдущих пакетов остаются: это изолированные тесты через AST,
без штатной инициализации приложения, БД, pytest и запуска бинарника Xray.

Если пакет 02 уже установлен, для пакета 03 заменить только:
- app/subscription/v2ray.py
- tests/test_hysteria2_xray_json.py
- HYSTERIA2_FIX_NOTES.md (эти примечания)

Предлагаемый коммит:
fix(hysteria2): skip generic mux and unused fragment/noise dialers
