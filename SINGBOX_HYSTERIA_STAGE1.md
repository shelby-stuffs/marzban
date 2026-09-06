# Hysteria2 → sing-box: stage 1

This stage separates Hysteria2 at runtime while preserving the current Marzban
control-plane metadata and subscription model. It is opt-in.

## Runtime boundary

- Xray never receives a Hysteria inbound or Hysteria user when
  `SINGBOX_HYSTERIA_ENABLED=true`.
- A standalone sing-box process in the same container receives native
  `type: hysteria2` inbounds and `{name,password}` users.
- User password is `proxies.hysteria.auth`. Salamander is server-wide and comes
  only from the inbound `finalmask`. Legacy user obfs values are not copied to
  the server config.
- User changes are coalesced for 750 ms; the generated config is checked before
  atomic replacement and process restart. A health job reconciles every 5 s.
- Only the main server is implemented. Hysteria is removed from configs sent to
  Xray nodes, so do not enable Hysteria hosts on nodes in this stage.

## Enable

```bash
docker compose -f docker-compose.yml -f compose.singbox-hysteria.yml build marzban
docker compose -f docker-compose.yml -f compose.singbox-hysteria.yml up -d marzban
```

The existing Xray-shaped Hysteria inbound is temporarily retained as migration
metadata in `xray_config.json`; it is filtered from the actual Xray runtime. This
avoids a database/UI migration in the same release. A later stage should move
this metadata into a dedicated sing-box settings document and remove Xray proto
classes and Xray-specific Hysteria validation/export code.

## Important limitation

Per-user sing-box traffic accounting has not been wired into Marzban. Do not use
this stage in production when data limits must be enforced. Reloading sing-box
can interrupt active Hysteria connections. Test on a copy first.

Suggested commit:

`feat(hysteria2): run main inbound on standalone sing-box core`
