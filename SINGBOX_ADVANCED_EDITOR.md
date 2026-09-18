# Расширенный редактор sing-box

Раздел `sing-box` содержит Monaco JSON-редактор для верхнеуровневых секций:
`log`, `dns`, `ntp`, `certificate`, `endpoints`, `outbounds`, `route`, `services`
`inbounds` и `experimental`.

`inbounds` больше не зарезервирован. Можно использовать любые протоколы,
которые поддерживает установленная версия sing-box. Если `inbounds` отсутствует,
для обратной совместимости используется автоматически сгенерированный inbound
Hysteria 2. Если `inbounds` указан, он полностью заменяет автоматически
сгенерированный inbound.

В dashboard есть schema-driven конструкторы inbounds, outbounds, DNS-серверов,
endpoints и services. Каждый объект создаётся в отдельном окне: тип выбирается
из официального списка, обязательные поля помечаются и проверяются до
сохранения, а protocol-specific поля (`users`, TLS, transport, peers и т. п.)
открываются в том же окне как JSON-поля. После сохранения объект добавляется в
этот же конфиг.

Редактор подключает официальную JSON Schema sing-box `1.14.0`, поэтому
поддерживает автодополнение и диагностику для всех актуальных верхнеуровневых
секций: `log`, `dns`, `ntp`, `certificate`, `certificate_providers`,
`http_clients`, `network_namespaces`, `endpoints`, `inbounds`, `outbounds`,
`route`, `services` и `experimental`.

Конфиг хранится в `/var/lib/marzban/sing-box-advanced.json`. При проверке или
сохранении он объединяется с настройками rule sets и проходит `sing-box check`.
Только после успешной проверки файл атомарно заменяется и runtime применяется.

Минимальный пример:

```json
{
  "inbounds": [
    {
      "type": "vless",
      "tag": "vless-in",
      "listen": "::",
      "listen_port": 8443,
      "users": [
        { "name": "demo", "uuid": "00000000-0000-0000-0000-000000000001" }
      ]
    }
  ],
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
