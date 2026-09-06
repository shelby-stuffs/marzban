# sing-box Rule sets

Страница sing-box разделена на вкладки `JSON + Logs`, `Inbound`, `Subscription` и `Rule sets`.
Rule sets хранятся отдельно в `/var/lib/marzban/sing-box-rule-sets.json`, а
скачанные remote-наборы кэшируются в `/var/lib/marzban/sing-box-cache.db`.

Поддерживаются remote/local источники и inline IP/CIDR-наборы и форматы binary (`.srs`) и source.
Для remote доступны URL, `download_detour` и `update_interval`. Поле outbound
добавляет приоритетное правило с `action: route`; пустое поле только объявляет
rule set. Пользовательские `route.rule_set` и `route.rules` из JSON сохраняются.
Коллизия тегов между двумя редакторами отклоняется.

Перед сохранением полный объединённый конфиг проходит `sing-box check`. Кнопка
принудительного обновления перезапускает sing-box, поэтому активные Hysteria
соединения кратковременно обрываются.

API:
- `GET/PUT /api/singbox/rule-sets`
- `POST /api/singbox/rule-sets/check`
- `POST /api/singbox/rule-sets/reload`

## Inline IP/CIDR

Для `type: inline` панель принимает IPv4, IPv6 и CIDR по одному на строку.
Одиночные адреса нормализуются в `/32` и `/128`, а runtime получает нативную
структуру sing-box 1.13: `rules: [{"ip_cidr": [...]}]`. Опция source IP
добавляет `rule_set_ip_cidr_match_source` в route-правило.
