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
  Text,
  VStack,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";

type Value = Record<string, any>;
type Props = {
  isOpen: boolean;
  initialValue: Value;
  onClose: () => void;
  onSave: (value: Value) => void;
};
type Field = { key: string; label: string; kind?: "text" | "number" | "checkbox" | "select"; options?: string[]; placeholder?: string; };

const TYPES = ["dhcp", "fakeip", "h3", "hosts", "https", "local", "mdns", "openconnect", "openvpn", "quic", "resolved", "tailscale", "tcp", "tls", "udp"];
const FIELDS: Record<string, Field[]> = {
  dhcp: [{ key: "interface", label: "Interface" }, { key: "prefer_go", label: "Prefer Go resolver", kind: "checkbox" }, { key: "neighbor_domain", label: "Neighbor domain" }],
  fakeip: [{ key: "inet4_range", label: "IPv4 range", placeholder: "198.18.0.0/15" }, { key: "inet6_range", label: "IPv6 range", placeholder: "fc00::/18" }],
  h3: [{ key: "server", label: "Server", placeholder: "dns.example.com" }, { key: "server_port", label: "Port", kind: "number" }, { key: "path", label: "Path", placeholder: "/dns-query" }, { key: "method", label: "HTTP method", kind: "select", options: ["GET", "POST"] }],
  hosts: [{ key: "path", label: "Hosts file path", placeholder: "/etc/hosts" }],
  https: [{ key: "server", label: "Server", placeholder: "dns.example.com" }, { key: "server_port", label: "Port", kind: "number" }, { key: "path", label: "Path", placeholder: "/dns-query" }, { key: "method", label: "HTTP method", kind: "select", options: ["GET", "POST"] }],
  local: [{ key: "prefer_go", label: "Prefer Go resolver", kind: "checkbox" }, { key: "neighbor_domain", label: "Neighbor domain" }],
  mdns: [{ key: "interface", label: "Interface" }, { key: "prefer_go", label: "Prefer Go resolver", kind: "checkbox" }, { key: "neighbor_domain", label: "Neighbor domain" }],
  openconnect: [{ key: "endpoint", label: "Endpoint tag" }, { key: "accept_default_resolvers", label: "Accept default resolvers", kind: "checkbox" }, { key: "accept_search_domain", label: "Accept search domain", kind: "checkbox" }],
  openvpn: [{ key: "endpoint", label: "Endpoint tag" }, { key: "accept_default_resolvers", label: "Accept default resolvers", kind: "checkbox" }, { key: "accept_search_domain", label: "Accept search domain", kind: "checkbox" }],
  quic: [{ key: "server", label: "Server", placeholder: "dns.example.com" }, { key: "server_port", label: "Port", kind: "number" }],
  resolved: [{ key: "service", label: "Service", placeholder: "org.freedesktop.resolve1" }, { key: "accept_default_resolvers", label: "Accept default resolvers", kind: "checkbox" }],
  tailscale: [{ key: "endpoint", label: "Endpoint tag" }, { key: "accept_default_resolvers", label: "Accept default resolvers", kind: "checkbox" }, { key: "accept_search_domain", label: "Accept search domain", kind: "checkbox" }],
  tcp: [{ key: "server", label: "Server", placeholder: "1.1.1.1" }, { key: "server_port", label: "Port", kind: "number" }],
  tls: [{ key: "server", label: "Server", placeholder: "1.1.1.1" }, { key: "server_port", label: "Port", kind: "number" }],
  udp: [{ key: "server", label: "Server", placeholder: "1.1.1.1" }, { key: "server_port", label: "Port", kind: "number" }],
};
const SERVER_TYPES = new Set(["h3", "https", "quic", "tcp", "tls", "udp"]);
const TLS_TYPES = new Set(["h3", "https", "quic", "tls"]);
const ALL_KEYS = new Set(["tag", "detour", "tls", "headers", ...Object.values(FIELDS).flat().map((field) => field.key)]);

export const SingBoxDnsDialog = ({ isOpen, initialValue, onClose, onSave }: Props) => {
  const [value, setValue] = useState<Value>(initialValue || {});
  const [tls, setTls] = useState<Value>({});
  const [headers, setHeaders] = useState<Array<{ name: string; value: string }>>([]);
  const [error, setError] = useState("");
  const type = String(value.type || "local");
  const fields = FIELDS[type] || [];

  useEffect(() => {
    if (!isOpen) return;
    const next = initialValue || {};
    setValue(next);
    setTls(next.tls && typeof next.tls === "object" ? next.tls : {});
    setHeaders(Object.entries(next.headers || {}).map(([name, headerValue]) => ({ name, value: String(headerValue) })));
    setError("");
  }, [initialValue, isOpen]);

  const update = (key: string, next: unknown) => setValue((current) => ({ ...current, [key]: next }));
  const renderField = (field: Field) => {
    const current = value[field.key];
    if (field.kind === "checkbox") return <Checkbox isChecked={current === true} onChange={(event) => update(field.key, event.target.checked)}>{field.label}</Checkbox>;
    if (field.kind === "select") return <FormControl><FormLabel fontSize="xs" mb="1">{field.label}</FormLabel><Select size="sm" value={String(current || "")} onChange={(event) => update(field.key, event.target.value)}><option value="">Default</option>{(field.options || []).map((option) => <option key={option} value={option}>{option}</option>)}</Select></FormControl>;
    return <FormControl><FormLabel fontSize="xs" mb="1">{field.label}</FormLabel><Input size="sm" type={field.kind === "number" ? "number" : "text"} fontFamily="mono" value={current === undefined ? "" : String(current)} placeholder={field.placeholder} onChange={(event) => update(field.key, event.target.value === "" && field.kind === "number" ? undefined : field.kind === "number" ? Number(event.target.value) : event.target.value)} /></FormControl>;
  };

  const save = () => {
    if (!String(value.tag || "").trim()) return setError("Tag is required");
    if (SERVER_TYPES.has(type) && (!value.server || !value.server_port)) return setError("Server and port are required");
    if (type === "fakeip" && !value.inet4_range && !value.inet6_range) return setError("At least one FakeIP range is required");
    const result: Value = { type, tag: String(value.tag).trim() };
    fields.forEach((field) => {
      const item = value[field.key];
      if (field.kind === "checkbox" ? item === true : item !== undefined && item !== null && item !== "") result[field.key] = item;
    });
    if (TLS_TYPES.has(type) && Object.keys(tls).some((key) => tls[key] !== undefined && tls[key] !== "")) result.tls = { enabled: true, ...tls };
    const headerObject = Object.fromEntries(headers.filter((item) => item.name.trim()).map((item) => [item.name.trim(), item.value]));
    if (Object.keys(headerObject).length) result.headers = headerObject;
    onSave(result);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="3xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg="terminal.bg" border="1px solid" borderColor="terminal.border">
        <ModalHeader fontFamily="mono">DNS server</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {error && <Alert status="error" mb="4"><AlertIcon />{error}</Alert>}
          <VStack align="stretch" spacing="4">
            <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
              <FormControl isRequired><FormLabel>Type</FormLabel><Select value={type} onChange={(event) => setValue((current) => ({ type: event.target.value, tag: current.tag }))}>{TYPES.map((item) => <option key={item} value={item}>{item}</option>)}</Select></FormControl>
              <FormControl isRequired><FormLabel>Tag</FormLabel><Input fontFamily="mono" value={String(value.tag || "")} onChange={(event) => update("tag", event.target.value)} placeholder="dns-cloudflare" /></FormControl>
            </Grid>
            <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="3">{fields.map((field) => <Box key={field.key}>{renderField(field)}</Box>)}</Grid>
            {TLS_TYPES.has(type) && <Box borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3"><Text fontWeight="bold" mb="3">TLS</Text><Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3"><FormControl><FormLabel fontSize="xs" mb="1">Server name</FormLabel><Input size="sm" fontFamily="mono" value={String(tls.server_name || "")} onChange={(event) => setTls((current) => ({ ...current, server_name: event.target.value }))} /></FormControl><Checkbox isChecked={tls.insecure === true} onChange={(event) => setTls((current) => ({ ...current, insecure: event.target.checked }))}>Insecure TLS</Checkbox></Grid></Box>}
            {(type === "h3" || type === "https") && <Box borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3"><HStack justify="space-between" mb="3"><Text fontWeight="bold">HTTP headers</Text><Button size="sm" variant="outline" onClick={() => setHeaders((current) => [...current, { name: "", value: "" }])}>Add header</Button></HStack><VStack align="stretch">{headers.map((header, index) => <HStack key={index}><Input size="sm" placeholder="Header" value={header.name} onChange={(event) => setHeaders((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item))} /><Input size="sm" placeholder="Value" value={header.value} onChange={(event) => setHeaders((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, value: event.target.value } : item))} /><Button size="sm" variant="ghost" colorScheme="red" onClick={() => setHeaders((current) => current.filter((_, itemIndex) => itemIndex !== index))}>Remove</Button></HStack>)}</VStack></Box>}
          </VStack>
        </ModalBody>
        <ModalFooter gap="2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button colorScheme="primary" onClick={save}>Save DNS server</Button></ModalFooter>
      </ModalContent>
    </Modal>
  );
};