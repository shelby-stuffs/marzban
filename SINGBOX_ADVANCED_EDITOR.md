# Расширенный редактор sing-box

Раздел `sing-box` содержит Monaco JSON-редактор для верхнеуровневых секций:
`log`, `dns`, `ntp`, `certificate`, `endpoints`, `outbounds`, `route`, `services`
и `experimental`.

`inbounds` зарезервирован: Hysteria 2 и пользователи продолжают автоматически
генерироваться Marzban. Редактор не может перезаписать их или раскрыть auth.

Конфиг хранится в `/var/lib/marzban/sing-box-advanced.json`. При проверке или
сохранении он объединяется с управляемым inbound и проходит `sing-box check`.
Только после успешной проверки файл атомарно заменяется и runtime применяется.

Минимальный пример:

```json
{
  "outbounds": [
    { "type": "direct", "tag": "direct" },
    { "type": "block", "tag": "block" }
  ],
  "route": {
    "rules": [
      { "ip_is_private": true, "outbound": "block" }
    ],
    "final": "direct"
  }
}
```

API: `GET/PUT /api/singbox/advanced-config` и
`POST /api/singbox/advanced-config/check`.
