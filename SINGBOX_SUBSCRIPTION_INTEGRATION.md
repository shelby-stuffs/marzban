# Hysteria 2 в подписках

Раздел `sing-box` содержит отдельный блок `endpoint подписки`. Он является
источником публичного адреса Hysteria 2 для всех форматов подписки и больше не
зависит от старого Hysteria inbound в Xray или записи Hosts.

Поля:
- публичный домен/IP или шаблон `{SERVER_IP}`;
- внешний UDP-порт (если пусто — listen port);
- SNI;
- allow insecure;
- шаблон названия узла;
- выключатель публикации Hysteria 2.

Один профиль на базе индивидуального `proxies.hysteria.auth` сериализуется в:
- `hysteria2://`;
- Clash Meta `type: hysteria2`;
- sing-box outbound `type: hysteria2`;
- Xray JSON/Happ.

Salamander и ALPN наследуются из серверных настроек sing-box. Пользовательский
пароль Salamander не используется; индивидуальным остаётся только auth.

После сохранения раздела кэш подписок очищается. Для корректной TLS-проверки
публичный адрес/SNI должны входить в SAN сертификата sing-box.

## Custom inbounds

Custom `vless`, `vmess`, `trojan`, `shadowsocks` и `hysteria2` inbounds из
`sing-box-advanced.json` также добавляются в sing-box-подписку пользователя.
Они экспортируются как client outbounds с адресом `SERVER_IP`, `listen_port`,
TLS/transport из inbound и credentials соответствующего proxy пользователя
Marzban.

Пользователь должен иметь соответствующий proxy в Marzban. Для custom inbound
используется его database credential, поэтому отдельное ручное дублирование
пароля или UUID в подписке не требуется.
