import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormHelperText,
  FormLabel,
  Grid,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
  VStack,
} from "@chakra-ui/react";
import { fetch } from "service/http";
import { useEffect, useMemo, useState } from "react";

type JsonObject = Record<string, any>;
type Props = {
  isOpen: boolean;
  initialValue: JsonObject;
  onClose: () => void;
  onSave: (value: JsonObject) => void;
};
type FieldKind = "text" | "password" | "number" | "checkbox" | "select" | "csv";
type FieldSpec = {
  key: string;
  label: string;
  kind?: FieldKind;
  options?: string[];
  placeholder?: string;
  helper?: string;
};

const PROTOCOLS = [
  "anytls", "cloudflared", "direct", "http", "hysteria", "hysteria2",
  "mixed", "naive", "redirect", "shadowsocks", "shadowtls", "snell",
  "socks", "tproxy", "trojan", "tuic", "tun", "vless", "vmess",
];
const NETWORKS = ["raw", "ws", "grpc", "http", "httpupgrade", "quic"];
const SECURITIES = ["none", "tls", "reality"];
const TLS_PROTOCOLS = ["anytls", "http", "hysteria", "hysteria2", "mixed", "naive", "trojan", "tuic", "vless", "vmess"];
const TRANSPORT_PROTOCOLS = ["trojan", "vless", "vmess"];
const USER_PROTOCOLS = ["anytls", "http", "hysteria", "hysteria2", "mixed", "naive", "shadowsocks", "shadowtls", "snell", "socks", "trojan", "tuic", "vless", "vmess"];

const COMMON_FIELDS: FieldSpec[] = [
  { key: "bind_interface", label: "Bind interface", placeholder: "eth0" },
  { key: "detour", label: "Detour inbound tag", placeholder: "another-inbound" },
  { key: "reuse_addr", label: "Reuse address", kind: "checkbox" },
  { key: "tcp_fast_open", label: "TCP fast open", kind: "checkbox" },
  { key: "tcp_multi_path", label: "TCP multipath", kind: "checkbox" },
  { key: "disable_tcp_keep_alive", label: "Disable TCP keep-alive", kind: "checkbox" },
  { key: "tcp_keep_alive", label: "TCP keep-alive", placeholder: "5m" },
  { key: "udp_timeout", label: "UDP timeout", placeholder: "5m" },
  { key: "udp_fragment", label: "UDP fragment", kind: "checkbox" },
];

const PROTOCOL_FIELDS: Record<string, FieldSpec[]> = {
  anytls: [{ key: "padding_scheme", label: "Padding scheme", kind: "csv", placeholder: "stop=1-5, 0=30-60" }],
  cloudflared: [
    { key: "token", label: "Tunnel token", kind: "password" },
    { key: "ha_connections", label: "HA connections", kind: "number", placeholder: "4" },
    { key: "protocol", label: "Cloudflare protocol", kind: "select", options: ["auto", "quic", "http2", "h2mux"] },
    { key: "post_quantum", label: "Post-quantum", kind: "checkbox" },
    { key: "edge_ip_version", label: "Edge IP version", kind: "select", options: ["0", "4", "6"] },
    { key: "datagram_version", label: "Datagram version", kind: "select", options: ["v2", "v3"] },
    { key: "grace_period", label: "Grace period", placeholder: "30s" },
    { key: "region", label: "Region", placeholder: "auto" },
  ],
  direct: [
    { key: "network", label: "Network", kind: "select", options: ["tcp", "udp", "tcp, udp"] },
    { key: "override_address", label: "Override address" },
    { key: "override_port", label: "Override port", kind: "number" },
  ],
  http: [{ key: "set_system_proxy", label: "Set system proxy", kind: "checkbox" }],
  hysteria: [
    { key: "up_mbps", label: "Upload Mbps", kind: "number" },
    { key: "down_mbps", label: "Download Mbps", kind: "number" },
    { key: "obfs", label: "Obfuscation password", kind: "password" },
    { key: "idle_timeout", label: "Idle timeout", placeholder: "30s" },
    { key: "keep_alive_period", label: "Keep-alive period", placeholder: "10s" },
    { key: "max_concurrent_streams", label: "Max concurrent streams", kind: "number" },
    { key: "disable_path_mtu_discovery", label: "Disable path MTU discovery", kind: "checkbox" },
  ],
  hysteria2: [
    { key: "up_mbps", label: "Upload Mbps", kind: "number" },
    { key: "down_mbps", label: "Download Mbps", kind: "number" },
    { key: "ignore_client_bandwidth", label: "Ignore client bandwidth", kind: "checkbox" },
    { key: "idle_timeout", label: "Idle timeout", placeholder: "30s" },
    { key: "keep_alive_period", label: "Keep-alive period", placeholder: "10s" },
    { key: "max_concurrent_streams", label: "Max concurrent streams", kind: "number" },
    { key: "disable_path_mtu_discovery", label: "Disable path MTU discovery", kind: "checkbox" },
    { key: "bbr_profile", label: "BBR profile", kind: "select", options: ["standard", "conservative", "aggressive"] },
    { key: "brutal_debug", label: "Brutal debug", kind: "checkbox" },
  ],
  mixed: [{ key: "set_system_proxy", label: "Set system proxy", kind: "checkbox" }],
  naive: [
    { key: "network", label: "Network", kind: "select", options: ["tcp", "udp", "tcp, udp"] },
    { key: "quic_congestion_control", label: "QUIC congestion control", kind: "select", options: ["bbr", "cubic", "reno"] },
  ],
  shadowsocks: [
    { key: "network", label: "Network", kind: "select", options: ["tcp", "udp", "tcp, udp"] },
    { key: "method", label: "Cipher", kind: "select", options: ["none", "aes-128-gcm", "aes-192-gcm", "aes-256-gcm", "chacha20-ietf-poly1305", "xchacha20-ietf-poly1305", "2022-blake3-aes-128-gcm", "2022-blake3-aes-256-gcm", "2022-blake3-chacha20-poly1305"] },
    { key: "password", label: "Server password", kind: "password" },
    { key: "managed", label: "Managed mode", kind: "checkbox" },
  ],
  shadowtls: [
    { key: "version", label: "ShadowTLS version", kind: "select", options: ["1", "2", "3"] },
    { key: "password", label: "Server password", kind: "password" },
    { key: "strict_mode", label: "Strict mode", kind: "checkbox" },
    { key: "wildcard_sni", label: "Wildcard SNI mode", kind: "select", options: ["", "off", "authed", "all"] },
  ],
  snell: [
    { key: "version", label: "Snell version", kind: "select", options: ["5", "6"] },
    { key: "psk", label: "PSK", kind: "password" },
    { key: "obfs_mode", label: "Obfuscation mode", kind: "select", options: ["none", "http", "tls"] },
  ],
  tproxy: [
    { key: "network", label: "Network", kind: "select", options: ["tcp", "udp", "tcp, udp"] },
    { key: "udp_mapping", label: "UDP mapping", kind: "select", options: ["", "endpoint_independent", "address_dependent", "address_and_port_dependent"] },
    { key: "udp_filtering", label: "UDP filtering", kind: "select", options: ["", "endpoint_independent", "address_dependent", "address_and_port_dependent"] },
    { key: "udp_nat_max", label: "UDP NAT max", kind: "number" },
  ],
  tuic: [
    { key: "congestion_control", label: "Congestion control", kind: "select", options: ["cubic", "new_reno", "bbr"] },
    { key: "auth_timeout", label: "Auth timeout", placeholder: "3s" },
    { key: "zero_rtt_handshake", label: "0-RTT handshake", kind: "checkbox" },
    { key: "heartbeat", label: "Heartbeat", placeholder: "10s" },
    { key: "idle_timeout", label: "Idle timeout", placeholder: "30s" },
    { key: "keep_alive_period", label: "Keep-alive period", placeholder: "10s" },
    { key: "max_concurrent_streams", label: "Max concurrent streams", kind: "number" },
    { key: "disable_path_mtu_discovery", label: "Disable path MTU discovery", kind: "checkbox" },
  ],
  tun: [
    { key: "interface_name", label: "Interface name", placeholder: "singtun0" },
    { key: "mtu", label: "MTU", kind: "number", placeholder: "9000" },
    { key: "address", label: "Interface addresses", kind: "csv", placeholder: "172.19.0.1/30, fdfe:dcba::1/126" },
    { key: "dns_mode", label: "DNS mode", kind: "select", options: ["disabled", "native", "hijack"] },
    { key: "dns_address", label: "DNS addresses", kind: "csv", placeholder: "1.1.1.1, 2606:4700:4700::1111" },
    { key: "auto_route", label: "Auto route", kind: "checkbox" },
    { key: "strict_route", label: "Strict route", kind: "checkbox" },
    { key: "route_address", label: "Route addresses", kind: "csv", placeholder: "0.0.0.0/0, ::/0" },
    { key: "route_exclude_address", label: "Exclude addresses", kind: "csv" },
    { key: "stack", label: "Stack", kind: "select", options: ["system", "gvisor", "mixed"] },
    { key: "udp_mapping", label: "UDP mapping", kind: "select", options: ["", "endpoint_independent", "address_dependent", "address_and_port_dependent"] },
    { key: "udp_filtering", label: "UDP filtering", kind: "select", options: ["", "endpoint_independent", "address_dependent", "address_and_port_dependent"] },
    { key: "udp_nat_max", label: "UDP NAT max", kind: "number" },
  ],
};

const TRANSPORT_FIELDS: Record<string, FieldSpec[]> = {
  ws: [
    { key: "path", label: "Path", placeholder: "/edge" },
    { key: "host", label: "Host", placeholder: "edge.example.com" },
    { key: "max_early_data", label: "Max early data", kind: "number" },
    { key: "early_data_header_name", label: "Early data header", placeholder: "Sec-WebSocket-Protocol" },
  ],
  grpc: [
    { key: "service_name", label: "Service name", placeholder: "grpc-service" },
    { key: "idle_timeout", label: "Idle timeout", placeholder: "15s" },
    { key: "ping_timeout", label: "Ping timeout", placeholder: "15s" },
    { key: "permit_without_stream", label: "Permit without stream", kind: "checkbox" },
  ],
  http: [
    { key: "host", label: "Host names", kind: "csv", placeholder: "edge.example.com" },
    { key: "path", label: "Path", placeholder: "/edge" },
    { key: "method", label: "Method", kind: "select", options: ["GET", "POST"] },
  ],
  httpupgrade: [
    { key: "host", label: "Host", placeholder: "edge.example.com" },
    { key: "path", label: "Path", placeholder: "/edge" },
  ],
};

const USER_FIELDS: Record<string, FieldSpec[]> = {
  anytls: [{ key: "name", label: "Name" }, { key: "password", label: "Password", kind: "password" }],
  http: [{ key: "Username", label: "Username" }, { key: "Password", label: "Password", kind: "password" }],
  hysteria: [{ key: "name", label: "Name" }, { key: "auth", label: "Auth", kind: "password" }],
  hysteria2: [{ key: "name", label: "Name" }, { key: "password", label: "Password", kind: "password" }],
  mixed: [{ key: "Username", label: "Username" }, { key: "Password", label: "Password", kind: "password" }],
  naive: [{ key: "Username", label: "Username" }, { key: "Password", label: "Password", kind: "password" }],
  shadowsocks: [{ key: "name", label: "Name" }, { key: "password", label: "Password", kind: "password" }],
  shadowtls: [{ key: "name", label: "Name" }, { key: "password", label: "Password", kind: "password" }],
  snell: [{ key: "name", label: "Name" }, { key: "userkey", label: "User key", kind: "password" }],
  socks: [{ key: "Username", label: "Username" }, { key: "Password", label: "Password", kind: "password" }],
  trojan: [{ key: "name", label: "Name" }, { key: "password", label: "Password", kind: "password" }],
  tuic: [{ key: "name", label: "Name" }, { key: "uuid", label: "UUID" }, { key: "password", label: "Password", kind: "password" }],
  vless: [{ key: "name", label: "Name" }, { key: "uuid", label: "UUID" }, { key: "flow", label: "Flow", placeholder: "xtls-rprx-vision" }],
  vmess: [{ key: "name", label: "Name" }, { key: "uuid", label: "UUID" }, { key: "alterId", label: "Alter ID", kind: "number" }],
};

const ALL_MANAGED_KEYS = Array.from(new Set([
  ...COMMON_FIELDS.map((field) => field.key),
  ...Object.values(PROTOCOL_FIELDS).flat().map((field) => field.key),
  "transport", "tls", "users", "multiplex", "obfs", "masquerade", "realm", "handshake",
]));

const textValue = (value: unknown, kind: FieldKind = "text") => (
  kind === "csv" ? (Array.isArray(value) ? value.join(", ") : String(value ?? "")) :
    value === undefined || value === null ? "" : String(value)
);
const listValue = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);
const getObject = (value: unknown): JsonObject => value && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : {};
const normalizeNetwork = (value: unknown) => typeof value === "string" && value.includes(",") ? listValue(value) : value;
const randomSecret = (size = 24) => {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789-_";
  const bytes = crypto.getRandomValues(new Uint8Array(size));
  return Array.from(bytes, (byte) => alphabet[byte % alphabet.length]).join("");
};
const randomUuid = () => {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
};
const randomShortId = () => Array.from(crypto.getRandomValues(new Uint8Array(4)), (byte) => byte.toString(16).padStart(2, "0")).join("");
const cleanUser = (user: JsonObject, fields: FieldSpec[]) => Object.fromEntries(
  fields.map((field) => [field.key, user[field.key]]).filter(([, value]) => value !== undefined && value !== null && value !== ""),
);

export const SingBoxInboundDialog = ({ isOpen, initialValue, onClose, onSave }: Props) => {
  const [value, setValue] = useState<JsonObject>(initialValue || {});
  const [network, setNetwork] = useState("raw");
  const [security, setSecurity] = useState("none");
  const [transport, setTransport] = useState<JsonObject>({});
  const [tls, setTls] = useState<JsonObject>({});
  const [reality, setReality] = useState<JsonObject>({});
  const [users, setUsers] = useState<JsonObject[]>([]);
  const [obfsType, setObfsType] = useState("");
  const [obfs, setObfs] = useState<JsonObject>({});
  const [realityPublicKey, setRealityPublicKey] = useState("");
  const [generatingKeypair, setGeneratingKeypair] = useState(false);
  const [masqueradeType, setMasqueradeType] = useState("none");
  const [masqueradeValue, setMasqueradeValue] = useState("");
  const [masqueradeRewriteHost, setMasqueradeRewriteHost] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) return;
    const next = initialValue || {};
    const nextTransport = getObject(next.transport);
    const nextTls = getObject(next.tls);
    const nextObfs = getObject(next.obfs);
    const nextMasquerade = next.masquerade;
    setValue(next);
    setNetwork(String(nextTransport.type || "raw"));
    setSecurity(nextTls.reality?.enabled ? "reality" : nextTls.enabled ? "tls" : "none");
    setTransport({ ...nextTransport, type: undefined });
    setTls({ ...nextTls, reality: undefined });
    setReality(getObject(nextTls.reality));
    setRealityPublicKey(String(nextTls.reality?.public_key || ""));
    setUsers(Array.isArray(next.users) ? next.users.filter((item): item is JsonObject => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : []);
    setObfsType(String(nextObfs.type || ""));
    setObfs(nextObfs);
    if (typeof nextMasquerade === "string" && nextMasquerade) {
      setMasqueradeType("string");
      setMasqueradeValue(nextMasquerade);
    } else if (getObject(nextMasquerade).type === "file" || getObject(nextMasquerade).type === "proxy") {
      setMasqueradeType(getObject(nextMasquerade).type);
      setMasqueradeValue(String(getObject(nextMasquerade).directory || getObject(nextMasquerade).url || ""));
      setMasqueradeRewriteHost(Boolean(getObject(nextMasquerade).rewrite_host));
    } else {
      setMasqueradeType("none");
      setMasqueradeValue("");
      setMasqueradeRewriteHost(false);
    }
    setError("");
  }, [initialValue, isOpen]);

  const protocol = String(value.type || "vless");
  const requiresPort = !["cloudflared", "tun"].includes(protocol);
  const usersSupported = USER_PROTOCOLS.includes(protocol);
  const tlsSupported = TLS_PROTOCOLS.includes(protocol);
  const transportSupported = TRANSPORT_PROTOCOLS.includes(protocol);
  const title = useMemo(() => `${initialValue?.tag || "New"} — sing-box inbound`, [initialValue]);
  const protocolFields = PROTOCOL_FIELDS[protocol] || [];
  const userFields = USER_FIELDS[protocol] || [];

  const update = (key: string, next: unknown) => setValue((current) => ({ ...current, [key]: next }));
  const updateUser = (index: number, key: string, next: unknown) => setUsers((current) => current.map((user, userIndex) => userIndex === index ? { ...user, [key]: next } : user));
  const addUser = () => setUsers((current) => [...current, { [userFields[0]?.key || "name"]: `client-${current.length + 1}` }]);
  const removeUser = (index: number) => setUsers((current) => current.filter((_, userIndex) => userIndex !== index));
  const generateFieldValue = (field: FieldSpec) => {
    if (field.key === "uuid") return randomUuid();
    if (field.key === "short_id") return randomShortId();
    return randomSecret();
  };
  const generateRealityKeypair = async () => {
    setGeneratingKeypair(true);
    try {
      const keypair = await fetch<{ private_key: string; public_key: string }>("/singbox/generate/reality-keypair", { method: "POST" });
      setReality((current) => ({ ...current, private_key: keypair.private_key }));
      setRealityPublicKey(keypair.public_key);
    } catch (generationError) {
      setError(generationError instanceof Error ? generationError.message : "Unable to generate Reality key pair");
    } finally {
      setGeneratingKeypair(false);
    }
  };

  const fieldControl = (
    field: FieldSpec,
    source: JsonObject,
    onChange: (key: string, next: unknown) => void,
  ) => {
    const kind = field.kind || "text";
    const current = source[field.key];
    const change = (raw: string | boolean) => {
      let next: unknown = raw;
      if (kind === "number") next = raw === "" ? undefined : Number(raw);
      if (kind === "csv") next = listValue(String(raw));
      onChange(field.key, next);
    };
    if (kind === "checkbox") return <Checkbox isChecked={Boolean(current)} onChange={(event) => change(event.target.checked)}>{field.label}</Checkbox>;
    if (kind === "select") return <FormControl><FormLabel fontSize="xs" mb="1">{field.label}</FormLabel><Select size="sm" value={textValue(current)} onChange={(event) => change(event.target.value)}><option value="">Default</option>{(field.options || []).map((option) => <option key={option} value={option}>{option}</option>)}</Select>{field.helper && <FormHelperText>{field.helper}</FormHelperText>}</FormControl>;
    const canGenerate = kind === "password" || field.key === "uuid" || field.key === "userkey" || field.key === "auth";
    return <FormControl><FormLabel fontSize="xs" mb="1">{field.label}</FormLabel><HStack><Input size="sm" type={kind === "password" ? "password" : kind === "number" ? "number" : "text"} fontFamily={kind === "password" ? undefined : "mono"} value={textValue(current, kind)} placeholder={field.placeholder} onChange={(event) => change(event.target.value)} />{canGenerate && <Button size="sm" variant="outline" flexShrink={0} onClick={() => change(generateFieldValue(field))}>Generate</Button>}</HStack>{field.helper && <FormHelperText>{field.helper}</FormHelperText>}</FormControl>;
  };

  const save = () => {
    if (!String(value.tag || "").trim()) return setError("Tag is required");
    if (requiresPort && (!value.listen_port || Number(value.listen_port) < 1 || Number(value.listen_port) > 65535)) return setError("Listen port must be between 1 and 65535");
    if (protocol === "shadowsocks" && !value.method) return setError("Cipher is required for Shadowsocks");
    if (security === "reality" && (!reality.private_key || !reality.handshake?.server || !reality.handshake?.server_port)) return setError("Reality requires private key, handshake server and handshake port");
    if (protocol === "hysteria2" && obfsType === "salamander" && !obfs.password) return setError("Salamander password is required");

    const result: JsonObject = { ...value, type: protocol, tag: String(value.tag).trim() };
    ALL_MANAGED_KEYS.forEach((key) => delete result[key]);
    result.type = protocol;
    result.tag = String(value.tag).trim();
    if (value.listen) result.listen = value.listen;
    if (requiresPort) result.listen_port = Number(value.listen_port);
    else delete result.listen_port;

    [...COMMON_FIELDS, ...protocolFields].forEach((field) => {
      const item = value[field.key];
      if (field.kind === "checkbox") {
        if (item === true) result[field.key] = true;
      } else if (field.kind === "csv") {
        if (Array.isArray(item) && item.length) result[field.key] = item;
      } else if (item !== undefined && item !== null && item !== "") {
        result[field.key] = field.key === "network"
          ? normalizeNetwork(item)
          : ["version", "edge_ip_version"].includes(field.key)
            ? Number(item)
            : item;
      }
    });
    if (transportSupported && network !== "raw") {
      const nextTransport: JsonObject = { type: network };
      (TRANSPORT_FIELDS[network] || []).forEach((field) => {
        const item = transport[field.key];
        if (field.kind === "checkbox") {
          if (item === true) nextTransport[field.key] = true;
        } else if (field.kind === "csv") {
          if (Array.isArray(item) && item.length) nextTransport[field.key] = item;
        } else if (item !== undefined && item !== null && item !== "") {
          nextTransport[field.key] = item;
        }
      });
      result.transport = nextTransport;
    }
    if (tlsSupported && security !== "none") {
      const nextTls: JsonObject = { enabled: true };
      [
        { key: "server_name", kind: "text" as FieldKind },
        { key: "certificate_path", kind: "text" as FieldKind },
        { key: "key_path", kind: "text" as FieldKind },
        { key: "insecure", kind: "checkbox" as FieldKind },
        { key: "alpn", kind: "csv" as FieldKind },
        { key: "min_version", kind: "text" as FieldKind },
        { key: "max_version", kind: "text" as FieldKind },
      ].forEach((field) => {
        const item = tls[field.key];
        if (field.kind === "checkbox") {
          if (item === true) nextTls[field.key] = true;
        } else if (field.kind === "csv") {
          if (Array.isArray(item) && item.length) nextTls[field.key] = item;
        } else if (item !== undefined && item !== null && item !== "") {
          nextTls[field.key] = item;
        }
      });
      if (security === "reality") {
        const nextReality: JsonObject = { enabled: true };
        ["private_key", "short_id", "max_time_difference"].forEach((key) => {
          if (reality[key] !== undefined && reality[key] !== "") nextReality[key] = reality[key];
        });
        if (reality.handshake?.server && reality.handshake?.server_port) nextReality.handshake = { server: reality.handshake.server, server_port: Number(reality.handshake.server_port) };
        nextTls.reality = nextReality;
      }
      result.tls = nextTls;
    }
    if (usersSupported) result.users = users.map((user) => cleanUser(user, userFields));
    if (protocol === "shadowtls" && value.handshake?.server && value.handshake?.server_port) {
      result.handshake = { server: value.handshake.server, server_port: Number(value.handshake.server_port) };
    }
    if (protocol === "hysteria2" && obfsType) result.obfs = { ...obfs, type: obfsType };
    if (protocol === "hysteria2" && masqueradeType !== "none" && masqueradeValue) {
      result.masquerade = masqueradeType === "string" ? masqueradeValue : masqueradeType === "file" ? { type: "file", directory: masqueradeValue } : { type: "proxy", url: masqueradeValue, rewrite_host: masqueradeRewriteHost };
    }
    onSave(result);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg="terminal.bg" border="1px solid" borderColor="terminal.border">
        <ModalHeader fontFamily="mono">{title}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {error && <Alert status="error" mb="4"><AlertIcon />{error}</Alert>}
          <Tabs colorScheme="primary" isLazy>
            <TabList overflowX="auto"><Tab>General</Tab><Tab>Protocol</Tab><Tab>Transport</Tab><Tab>Security</Tab><Tab isDisabled={!usersSupported}>Clients</Tab></TabList>
            <TabPanels>
              <TabPanel px="0">
                <VStack align="stretch" spacing="4">
                  <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
                    <FormControl isRequired><FormLabel>Protocol</FormLabel><Select value={protocol} onChange={(event) => update("type", event.target.value)}>{PROTOCOLS.map((item) => <option key={item} value={item}>{item}</option>)}</Select></FormControl>
                    <FormControl isRequired><FormLabel>Tag</FormLabel><Input fontFamily="mono" value={String(value.tag || "")} onChange={(event) => update("tag", event.target.value)} /></FormControl>
                    <FormControl><FormLabel>Listen address</FormLabel><Input fontFamily="mono" placeholder="::" value={String(value.listen || "")} onChange={(event) => update("listen", event.target.value)} /></FormControl>
                    <FormControl isRequired={requiresPort}><FormLabel>Listen port</FormLabel><Input type="number" value={value.listen_port === undefined ? "" : String(value.listen_port)} onChange={(event) => update("listen_port", event.target.value ? Number(event.target.value) : "")} /><FormHelperText>{requiresPort ? "Required for network inbounds." : "This protocol does not listen on a local port."}</FormHelperText></FormControl>
                  </Grid>
                  <Text color="gray.500" fontSize="sm">The next tabs change automatically for the selected protocol. Marzban users with a matching proxy are injected at runtime.</Text>
                  <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="3">{COMMON_FIELDS.map((field) => <Box key={field.key}>{fieldControl(field, value, (key, next) => update(key, next))}</Box>)}</Grid>
                </VStack>
              </TabPanel>
              <TabPanel px="0">
                <VStack align="stretch" spacing="4">
                  <Text color="gray.500" fontSize="sm">Only options supported by <b>{protocol}</b> are shown.</Text>
                  <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="3">{protocolFields.map((field) => <Box key={field.key}>{fieldControl(field, value, (key, next) => update(key, next))}</Box>)}</Grid>
                  {protocol === "hysteria2" && <Box borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3"><Text fontWeight="bold" mb="3">Obfuscation</Text><Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3"><FormControl><FormLabel fontSize="xs" mb="1">Type</FormLabel><Select size="sm" value={obfsType} onChange={(event) => setObfsType(event.target.value)}><option value="">Disabled</option><option value="salamander">Salamander</option><option value="gecko">Gecko</option></Select></FormControl>{obfsType && <FormControl><FormLabel fontSize="xs" mb="1">Password</FormLabel><HStack><Input size="sm" type="password" value={String(obfs.password || "")} onChange={(event) => setObfs((current) => ({ ...current, password: event.target.value }))} /><Button size="sm" variant="outline" onClick={() => setObfs((current) => ({ ...current, password: randomSecret() }))}>Generate</Button></HStack></FormControl>}</Grid></Box>}
                  {protocol === "hysteria2" && <Box borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3"><Text fontWeight="bold" mb="3">Masquerade</Text><Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3"><FormControl><FormLabel fontSize="xs" mb="1">Mode</FormLabel><Select size="sm" value={masqueradeType} onChange={(event) => setMasqueradeType(event.target.value)}><option value="none">Disabled</option><option value="string">URL / string</option><option value="file">Static file directory</option><option value="proxy">Proxy URL</option></Select></FormControl>{masqueradeType !== "none" && <FormControl><FormLabel fontSize="xs" mb="1">{masqueradeType === "file" ? "Directory" : "Value"}</FormLabel><Input size="sm" fontFamily="mono" value={masqueradeValue} onChange={(event) => setMasqueradeValue(event.target.value)} /></FormControl>}{masqueradeType === "proxy" && <Checkbox isChecked={masqueradeRewriteHost} onChange={(event) => setMasqueradeRewriteHost(event.target.checked)}>Rewrite host</Checkbox>}</Grid></Box>}
                  {protocol === "shadowtls" && <Box borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3"><Text fontWeight="bold" mb="3">Handshake</Text><Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3"><FormControl><FormLabel fontSize="xs" mb="1">Server</FormLabel><Input size="sm" fontFamily="mono" value={String(value.handshake?.server || "")} onChange={(event) => update("handshake", { ...(value.handshake || {}), server: event.target.value })} /></FormControl><FormControl><FormLabel fontSize="xs" mb="1">Server port</FormLabel><Input size="sm" type="number" value={value.handshake?.server_port || ""} onChange={(event) => update("handshake", { ...(value.handshake || {}), server_port: event.target.value ? Number(event.target.value) : undefined })} /></FormControl></Grid></Box>}
                </VStack>
              </TabPanel>
              <TabPanel px="0">
                {!transportSupported ? <Alert status="info"><AlertIcon />This protocol has no separate V2Ray transport. Its network is configured in the Protocol tab.</Alert> : <VStack align="stretch" spacing="4"><FormControl><FormLabel>Transport</FormLabel><Select value={network} onChange={(event) => setNetwork(event.target.value)}>{NETWORKS.map((item) => <option key={item} value={item}>{item}</option>)}</Select><FormHelperText>Transport-specific fields appear automatically.</FormHelperText></FormControl><Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="3">{(TRANSPORT_FIELDS[network] || []).map((field) => <Box key={field.key}>{fieldControl(field, transport, (key, next) => setTransport((current) => ({ ...current, [key]: next })))}</Box>)}</Grid></VStack>}
              </TabPanel>
              <TabPanel px="0">
                {!tlsSupported ? <Alert status="info"><AlertIcon />This protocol does not use TLS in the inbound schema.</Alert> : <VStack align="stretch" spacing="4"><FormControl><FormLabel>Security</FormLabel><Select value={security} onChange={(event) => setSecurity(event.target.value)}>{SECURITIES.map((item) => <option key={item} value={item}>{item}</option>)}</Select></FormControl>{security !== "none" && <><Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="3">{[{ key: "server_name", label: "Server name", placeholder: "edge.example.com" }, { key: "certificate_path", label: "Certificate path", placeholder: "/etc/ssl/fullchain.pem" }, { key: "key_path", label: "Private key path", kind: "password" as FieldKind }, { key: "insecure", label: "Insecure", kind: "checkbox" as FieldKind }, { key: "alpn", label: "ALPN", kind: "csv" as FieldKind, placeholder: "h2, http/1.1" }, { key: "min_version", label: "Minimum TLS version" }, { key: "max_version", label: "Maximum TLS version" }].map((field) => <Box key={field.key}>{fieldControl(field, tls, (key, next) => setTls((current) => ({ ...current, [key]: next })))}</Box>)}</Grid>{security === "reality" && <Box borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3"><HStack justify="space-between" mb="3"><Text fontWeight="bold">Reality</Text><Button size="sm" variant="outline" isLoading={generatingKeypair} onClick={() => void generateRealityKeypair()}>Generate key pair</Button></HStack><Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="3"><FormControl><FormLabel fontSize="xs" mb="1">Private key</FormLabel><Input size="sm" type="password" value={String(reality.private_key || "")} onChange={(event) => setReality((current) => ({ ...current, private_key: event.target.value }))} /></FormControl><FormControl><FormLabel fontSize="xs" mb="1">Public key</FormLabel><Input size="sm" fontFamily="mono" value={realityPublicKey} isReadOnly /></FormControl><FormControl><FormLabel fontSize="xs" mb="1">Short ID</FormLabel><HStack><Input size="sm" fontFamily="mono" value={String(reality.short_id || "")} onChange={(event) => setReality((current) => ({ ...current, short_id: event.target.value }))} /><Button size="sm" variant="outline" onClick={() => setReality((current) => ({ ...current, short_id: randomShortId() }))}>Generate</Button></HStack></FormControl><FormControl><FormLabel fontSize="xs" mb="1">Handshake server</FormLabel><Input size="sm" fontFamily="mono" value={String(reality.handshake?.server || "")} onChange={(event) => setReality((current) => ({ ...current, handshake: { ...(current.handshake || {}), server: event.target.value } }))} /></FormControl><FormControl><FormLabel fontSize="xs" mb="1">Handshake port</FormLabel><Input size="sm" type="number" value={reality.handshake?.server_port || ""} onChange={(event) => setReality((current) => ({ ...current, handshake: { ...(current.handshake || {}), server_port: event.target.value ? Number(event.target.value) : undefined } }))} /></FormControl><FormControl><FormLabel fontSize="xs" mb="1">Max time difference</FormLabel><Input size="sm" fontFamily="mono" value={String(reality.max_time_difference || "")} placeholder="1m" onChange={(event) => setReality((current) => ({ ...current, max_time_difference: event.target.value }))} /></FormControl></Grid></Box>}</>}</VStack>}
              </TabPanel>
              <TabPanel px="0">
                <VStack align="stretch" spacing="3">
                  <HStack justify="space-between" flexWrap="wrap" gap="2"><Text color="gray.500" fontSize="sm">Client fields also change with the selected protocol.</Text><Button size="sm" variant="outline" onClick={addUser}>Add client</Button></HStack>
                  {users.length === 0 && <Alert status="info" py="2"><AlertIcon />No manual clients yet.</Alert>}
                  {users.map((user, index) => <Box key={`${String(user.name || user.Username || "client")}-${index}`} borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3"><Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="3">{userFields.map((field) => <Box key={field.key}>{fieldControl(field, user, (key, next) => updateUser(index, key, next))}</Box>)}</Grid><HStack justify="flex-end" mt="3"><Button size="xs" variant="ghost" colorScheme="red" onClick={() => removeUser(index)}>Remove</Button></HStack></Box>)}
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </ModalBody>
        <ModalFooter gap="2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button colorScheme="primary" onClick={save}>Save inbound</Button></ModalFooter>
      </ModalContent>
    </Modal>
  );
};