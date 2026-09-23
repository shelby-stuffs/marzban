# sing-box per-user traffic accounting

Marzban includes traffic from the local standalone sing-box process in the same
limits, hourly usage rows, admin usage, and online timestamps used by Xray
users. This works for the managed Hysteria 2 inbound and for custom sing-box
inbounds created in the GUI or advanced configuration.

## How it works

- The image builds `shtorm-7/sing-box-extended`
  `v1.14.1-extended-2.7.2` with `with_quic`, `with_grpc`, and
  `with_v2ray_api`.
- Marzban injects a protected `experimental.v2ray_api` block into the final config.
- For supported user inbounds such as `http`, `socks`, `mixed`, `anytls`,
  `naive`, `shadowtls`, `tuic`, `vmess`, `trojan`, `shadowsocks`, `hysteria`,
  `hysteria2`, and `vless`, active/on-hold Marzban users are automatically
  injected.
- When `SINGBOX_MANAGE_VLESS=true`, VLESS inbounds are converted from the
  legacy Xray configuration and Xray no longer starts those listeners.
- Existing credentials are converted to the native sing-box user shape.
  Users excluded from a specific inbound remain excluded.
- All configured inbound tags and Marzban-formatted user names are registered
  for statistics. Manually configured users must use the
  `<database id>.<username>` name format to be mapped to a Marzban user;
  unrelated names are left out of Marzban accounting.
- User names and HTTP/SOCKS usernames remain `<database id>.<username>`, so
  the existing Marzban usage recorder maps counters without a second identity
  store. Authentication passwords remain stable and are derived from the
  Marzban username and inbound tag.
- Every normal usage poll reads and resets the sing-box counters, then adds their uplink and downlink bytes to the existing main-server usage batch.
- The existing review job applies data limits and removes limited users from both Xray and sing-box.

The gRPC listener defaults to `127.0.0.1:10085` and is not published by Docker.
The `SINGBOX_ENABLED` feature flag starts the standalone sing-box runtime.
`SINGBOX_HYSTERIA_ENABLED` remains accepted as a legacy fallback.

## Environment

```env
SINGBOX_ENABLED=true
SINGBOX_TRAFFIC_ACCOUNTING_ENABLED=true
SINGBOX_TRAFFIC_API_HOST=127.0.0.1
SINGBOX_TRAFFIC_API_PORT=10085
SINGBOX_MANAGE_VLESS=true
```

If you change the port, rebuild and recreate the Marzban container. Do not define `experimental.v2ray_api` in the advanced editor; Marzban owns it to prevent accidentally disabling accounting or exposing the gRPC listener.

## Verification

```bash
docker compose -f docker-compose.yml -f compose.singbox-hysteria.yml exec marzban \
  sing-box version
```

The output must list `with_v2ray_api` in `Tags`. Generate traffic with one Hysteria user, wait approximately one `JOB_RECORD_USER_USAGES_INTERVAL`, and refresh that user in the dashboard.
