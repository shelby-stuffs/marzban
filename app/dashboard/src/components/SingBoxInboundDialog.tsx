import {
  Alert,
  AlertIcon,
  Box,
  Button,
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
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { useEffect, useMemo, useState } from "react";

type JsonObject = Record<string, any>;

type Props = {
  isOpen: boolean;
  initialValue: JsonObject;
  onClose: () => void;
  onSave: (value: JsonObject) => void;
};

const PROTOCOLS = ["anytls", "cloudflared", "direct", "http", "hysteria", "hysteria2", "mixed", "naive", "redirect", "shadowsocks", "shadowtls", "socks", "tproxy", "trojan", "tuic", "tun", "vless", "vmess"];
const NETWORKS = ["raw", "ws", "grpc", "http", "httpupgrade", "quic"];
const SECURITIES = ["none", "tls", "reality"];

const jsonText = (value: unknown) => JSON.stringify(value ?? [], null, 2);
const parseJson = (value: string, fallback: unknown) => {
  if (!value.trim()) return fallback;
  return JSON.parse(value);
};

const getTransport = (value: JsonObject) => value.transport && typeof value.transport === "object" ? value.transport : {};
const getTls = (value: JsonObject) => value.tls && typeof value.tls === "object" ? value.tls : {};

export const SingBoxInboundDialog = ({ isOpen, initialValue, onClose, onSave }: Props) => {
  const [value, setValue] = useState<JsonObject>(initialValue || {});
  const [network, setNetwork] = useState("raw");
  const [security, setSecurity] = useState("none");
  const [transportJson, setTransportJson] = useState("{}");
  const [tlsJson, setTlsJson] = useState("{}");
  const [users, setUsers] = useState<JsonObject[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) return;
    const transport = getTransport(initialValue || {});
    const tls = getTls(initialValue || {});
    setValue(initialValue || {});
    setNetwork(String(transport.type || "raw"));
    setSecurity(tls.reality?.enabled ? "reality" : tls.enabled ? "tls" : "none");
    setTransportJson(jsonText(transport));
    setTlsJson(jsonText(tls));
    setUsers(Array.isArray(initialValue?.users)
      ? initialValue.users.filter((item): item is JsonObject => Boolean(item) && typeof item === "object" && !Array.isArray(item))
      : []);
    setError("");
  }, [initialValue, isOpen]);

  const protocol = String(value.type || "vless");
  const requiresPort = !["direct", "tun", "cloudflared"].includes(protocol);
  const usersSupported = ["anytls", "hysteria", "hysteria2", "http", "mixed", "naive", "shadowsocks", "socks", "trojan", "tuic", "vless", "vmess"].includes(protocol);
  const title = useMemo(() => `${initialValue?.tag || "New"} — sing-box inbound`, [initialValue]);
  const update = (key: string, next: unknown) => setValue((current) => ({ ...current, [key]: next }));
  const updateUser = (index: number, key: string, next: unknown) => {
    setUsers((current) => current.map((user, userIndex) => userIndex === index ? { ...user, [key]: next } : user));
  };
  const addUser = () => setUsers((current) => [...current, { name: `client-${current.length + 1}` }]);
  const removeUser = (index: number) => setUsers((current) => current.filter((_, userIndex) => userIndex !== index));

  const save = () => {
    if (!value.tag || !String(value.tag).trim()) return setError("Tag is required");
    if (requiresPort && (!value.listen_port || Number(value.listen_port) < 1 || Number(value.listen_port) > 65535)) return setError("Listen port must be between 1 and 65535");
    try {
      const result: JsonObject = { ...value, type: protocol, tag: String(value.tag).trim() };
      if (value.listen) result.listen = value.listen;
      if (requiresPort) result.listen_port = Number(value.listen_port);
      else delete result.listen_port;
      if (usersSupported) result.users = users;
      else delete result.users;
      const transport = parseJson(transportJson, {});
      if (network === "raw") delete result.transport;
      else result.transport = { ...transport, type: network };
      const tls = parseJson(tlsJson, {});
      if (security === "none") delete result.tls;
      else result.tls = { ...tls, enabled: true, ...(security === "reality" ? { reality: { ...(tls.reality || {}), enabled: true } } : {}) };
      onSave(result);
      onClose();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Invalid JSON field");
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="3xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg="terminal.bg" border="1px solid" borderColor="terminal.border">
        <ModalHeader fontFamily="mono">{title}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {error && <Alert status="error" mb="4"><AlertIcon />{error}</Alert>}
          <Tabs colorScheme="primary" isLazy>
            <TabList overflowX="auto"><Tab>General</Tab><Tab>Transport</Tab><Tab>Security</Tab><Tab isDisabled={!usersSupported}>Clients</Tab></TabList>
            <TabPanels>
              <TabPanel px="0">
                <VStack align="stretch" spacing="4">
                  <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
                    <FormControl isRequired><FormLabel>Protocol</FormLabel><Select value={protocol} onChange={(event) => update("type", event.target.value)}>{PROTOCOLS.map((item) => <option key={item} value={item}>{item}</option>)}</Select></FormControl>
                    <FormControl isRequired><FormLabel>Tag</FormLabel><Input fontFamily="mono" value={String(value.tag || "")} onChange={(event) => update("tag", event.target.value)} /></FormControl>
                    <FormControl><FormLabel>Listen address</FormLabel><Input fontFamily="mono" placeholder="::" value={String(value.listen || "")} onChange={(event) => update("listen", event.target.value)} /></FormControl>
                    <FormControl isRequired={requiresPort}><FormLabel>Listen port</FormLabel><Input type="number" value={value.listen_port === undefined ? "" : String(value.listen_port)} onChange={(event) => update("listen_port", event.target.value ? Number(event.target.value) : "")} /><FormHelperText>Required for network inbounds.</FormHelperText></FormControl>
                  </Grid>
                  <Text color="gray.500" fontSize="sm">Marzban users with a matching proxy are injected automatically at runtime. Manual clients can be added below.</Text>
                </VStack>
              </TabPanel>
              <TabPanel px="0">
                <VStack align="stretch" spacing="4">
                  <FormControl><FormLabel>Network</FormLabel><Select value={network} onChange={(event) => setNetwork(event.target.value)}>{NETWORKS.map((item) => <option key={item} value={item}>{item}</option>)}</Select><FormHelperText>Use raw for direct TCP. Protocol-specific transport options are available as JSON below.</FormHelperText></FormControl>
                  {network !== "raw" && <FormControl><FormLabel>Transport options (JSON)</FormLabel><Textarea minH="220px" fontFamily="mono" value={transportJson} onChange={(event) => setTransportJson(event.target.value)} placeholder={'{"path": "/edge"}'} /></FormControl>}
                </VStack>
              </TabPanel>
              <TabPanel px="0">
                <VStack align="stretch" spacing="4">
                  <FormControl><FormLabel>Security</FormLabel><Select value={security} onChange={(event) => setSecurity(event.target.value)}>{SECURITIES.map((item) => <option key={item} value={item}>{item}</option>)}</Select></FormControl>
                  {security !== "none" && <FormControl><FormLabel>TLS / Reality options (JSON)</FormLabel><Textarea minH="260px" fontFamily="mono" value={tlsJson} onChange={(event) => setTlsJson(event.target.value)} placeholder={'{"certificate_path": "/etc/ssl/fullchain.pem", "key_path": "/etc/ssl/privkey.pem"}'} /><FormHelperText>For Reality provide the official sing-box Reality fields in this object.</FormHelperText></FormControl>}
                </VStack>
              </TabPanel>
              <TabPanel px="0">
                <VStack align="stretch" spacing="3">
                  <HStack justify="space-between" flexWrap="wrap" gap="2">
                    <FormHelperText mt="0">Manual clients are kept in this inbound. Marzban-managed users are merged automatically at runtime.</FormHelperText>
                    <Button size="sm" variant="outline" onClick={addUser}>Add client</Button>
                  </HStack>
                  {users.length === 0 && <Alert status="info" py="2" fontSize="sm"><AlertIcon />No manual clients yet.</Alert>}
                  {users.map((user, index) => (
                    <Box key={`${String(user.name || "client")}-${index}`} borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3">
                      <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="3">
                        <FormControl><FormLabel fontSize="xs" mb="1">Name</FormLabel><Input size="sm" fontFamily="mono" value={String(user.name || "")} onChange={(event) => updateUser(index, "name", event.target.value)} /></FormControl>
                        {["vless", "vmess", "anytls"].includes(protocol) && <FormControl><FormLabel fontSize="xs" mb="1">UUID</FormLabel><Input size="sm" fontFamily="mono" value={String(user.uuid || "")} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" onChange={(event) => updateUser(index, "uuid", event.target.value)} /></FormControl>}
                        {!["vless", "vmess", "anytls"].includes(protocol) && <FormControl><FormLabel fontSize="xs" mb="1">Password</FormLabel><Input size="sm" type="password" value={String(user.password || "")} onChange={(event) => updateUser(index, "password", event.target.value)} /></FormControl>}
                        {protocol === "vless" && <FormControl><FormLabel fontSize="xs" mb="1">Flow</FormLabel><Input size="sm" fontFamily="mono" value={String(user.flow || "")} placeholder="xtls-rprx-vision" onChange={(event) => updateUser(index, "flow", event.target.value)} /></FormControl>}
                        {protocol === "vmess" && <FormControl><FormLabel fontSize="xs" mb="1">Alter ID</FormLabel><Input size="sm" type="number" value={user.alter_id === undefined ? "" : String(user.alter_id)} onChange={(event) => updateUser(index, "alter_id", event.target.value ? Number(event.target.value) : undefined)} /></FormControl>}
                      </Grid>
                      <HStack justify="flex-end" mt="3"><Button size="xs" variant="ghost" colorScheme="red" onClick={() => removeUser(index)}>Remove</Button></HStack>
                    </Box>
                  ))}
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </ModalBody>
        <ModalFooter gap="2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button colorScheme="primary" onClick={save}>Create inbound</Button></ModalFooter>
      </ModalContent>
    </Modal>
  );
};
