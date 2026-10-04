import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Checkbox,
  Divider,
  FormControl,
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
  NumberInput,
  NumberInputField,
  Select,
  Spinner,
  Switch,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { Header } from "components/Header";
import { Panel } from "components/Panel";
import { FC, useEffect, useState } from "react";
import { fetch } from "service/http";

type Settings = Record<string, any>;

type InboundClient = {
  email?: string;
  id?: string;
  password?: string;
  flow?: string;
  limitIp?: number;
  totalGB?: number;
  expiryTime?: number;
  enable?: boolean;
};

type ManagedInbound = {
  tag: string;
  protocol: string;
  listen?: string | null;
  port?: number | null;
  settings: Settings;
  streamSettings: Settings;
  sniffing: Settings;
};

const PROTOCOLS = ["vless", "vmess", "trojan", "shadowsocks", "socks", "http", "dokodemo-door", "wireguard"];
const NETWORKS = ["tcp", "ws", "httpupgrade", "xhttp", "grpc", "kcp", "http2", "quic"];
const SECURITIES = ["none", "tls", "reality"];
const VLESS_FLOWS = ["", "xtls-rprx-vision"];
const CLIENT_PROTOCOLS = ["vless", "vmess", "trojan", "shadowsocks"];

const emptyDraft: ManagedInbound = {
  tag: "",
  protocol: "vless",
  listen: "0.0.0.0",
  port: 443,
  settings: { clients: [], decryption: "none" },
  streamSettings: { network: "tcp", security: "none" },
  sniffing: { enabled: true, destOverride: ["http", "tls"] },
};

const errorMessage = (error: any, fallback: string) =>
  error?.response?._data?.detail || error?.message || fallback;

const generateUuid = () =>
  typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : Array.from(crypto.getRandomValues(new Uint8Array(16)))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");

const generatePassword = () =>
  Array.from(crypto.getRandomValues(new Uint8Array(12)))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

const generateShortId = () =>
  Array.from(crypto.getRandomValues(new Uint8Array(4)))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

const clean = (settings: Settings) => Object.fromEntries(
  Object.entries(settings).filter(([, value]) => value !== "" && value !== undefined && value !== null)
);

const ClientModal: FC<{
  protocol: string;
  initial: InboundClient | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (client: InboundClient) => void;
}> = ({ protocol, initial, isOpen, onClose, onSave }) => {
  const [client, setClient] = useState<InboundClient>({});
  useEffect(() => {
    if (isOpen) {
      setClient(
        initial
          ? { ...initial }
          : {
              email: `user-${Math.floor(Math.random() * 10000)}`,
              ...(protocol === "vless" || protocol === "vmess" ? { id: generateUuid() } : {}),
              ...(protocol === "trojan" || protocol === "shadowsocks" ? { password: generatePassword() } : {}),
              flow: "",
              limitIp: 0,
              totalGB: 0,
              expiryTime: 0,
              enable: true,
            }
      );
    }
  }, [isOpen, initial, protocol]);

  const update = (values: Partial<InboundClient>) =>
    setClient((current) => ({ ...current, ...values }));

  const idLabel = protocol === "vless" || protocol === "vmess" ? "UUID" : "Password";
  const idValue = client.id || client.password || "";

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{initial ? "Редактировать клиента" : "Добавить клиента"}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack align="stretch" spacing="4">
            <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
              <FormControl isRequired>
                <FormLabel>Email</FormLabel>
                <Input value={client.email || ""} onChange={(e) => update({ email: e.target.value })} />
              </FormControl>
              <FormControl>
                <FormLabel>Sub ID</FormLabel>
                <Input value={client.subId || ""} onChange={(e) => update({ subId: e.target.value } as any)} />
              </FormControl>
            </Grid>
            {CLIENT_PROTOCOLS.includes(protocol) && (
              <FormControl isRequired>
                <FormLabel>{idLabel}</FormLabel>
                <HStack>
                  <Input
                    fontFamily="mono"
                    value={idValue}
                    onChange={(e) =>
                      protocol === "vless" || protocol === "vmess"
                        ? update({ id: e.target.value, password: undefined })
                        : update({ password: e.target.value, id: undefined })
                    }
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      protocol === "vless" || protocol === "vmess"
                        ? update({ id: generateUuid() })
                        : update({ password: generatePassword() })
                    }
                  >
                    Сгенерировать
                  </Button>
                </HStack>
              </FormControl>
            )}
            {protocol === "vless" && (
              <FormControl>
                <FormLabel>Flow</FormLabel>
                <Select value={client.flow || ""} onChange={(e) => update({ flow: e.target.value })}>
                  {VLESS_FLOWS.map((flow) => (
                    <option key={flow} value={flow}>{flow || "none"}</option>
                  ))}
                </Select>
              </FormControl>
            )}
            <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap="4">
              <FormControl>
                <FormLabel>Limit IP (0 = ∞)</FormLabel>
                <NumberInput value={client.limitIp ?? 0} onChange={(_, value) => update({ limitIp: value })}>
                  <NumberInputField />
                </NumberInput>
              </FormControl>
              <FormControl>
                <FormLabel>Трафик GB (0 = ∞)</FormLabel>
                <NumberInput value={(client.totalGB ?? 0) / 1073741824} onChange={(_, value) => update({ totalGB: (value || 0) * 1073741824 })}>
                  <NumberInputField />
                </NumberInput>
              </FormControl>
              <FormControl>
                <FormLabel>Срок (дни, 0 = ∞)</FormLabel>
                <NumberInput
                  value={(client.expiryTime ?? 0) / 86400000}
                  onChange={(_, value) => update({ expiryTime: (value || 0) * 86400000 })}
                >
                  <NumberInputField />
                </NumberInput>
              </FormControl>
            </Grid>
            <HStack spacing="6">
              <HStack>
                <Switch
                  colorScheme="primary"
                  isChecked={client.enable !== false}
                  onChange={(e) => update({ enable: e.target.checked })}
                />
                <Text fontSize="sm">включён</Text>
              </HStack>
            </HStack>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <HStack spacing="3">
            <Button variant="ghost" onClick={onClose}>Отмена</Button>
            <Button
              colorScheme="primary"
              isDisabled={!client.email || (!idValue && CLIENT_PROTOCOLS.includes(protocol))}
              onClick={() => {
                onSave(clean(client) as InboundClient);
                onClose();
              }}
            >
              Сохранить
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

const StreamSettings: FC<{ stream: Settings; onChange: (settings: Settings) => void }> = ({ stream, onChange }) => {
  const update = (key: string, value: unknown) => onChange({ ...stream, [key]: value });
  const subUpdate = (section: string, key: string, value: unknown) =>
    onChange({ ...stream, [section]: { ...(stream[section] || {}), [key]: value } });
  const network = stream.network || "tcp";
  const security = stream.security || "none";
  const [keyLoading, setKeyLoading] = useState(false);
  const toast = useToast();

  const generateKeys = async () => {
    setKeyLoading(true);
    try {
      const keys = await fetch<{ private_key: string; public_key: string }>("/core/inbounds/reality-keygen", { method: "POST" });
      onChange({
        ...stream,
        realitySettings: {
          ...(stream.realitySettings || {}),
          privateKey: keys.private_key,
          publicKey: keys.public_key,
        },
      });
      toast({ title: "Reality keys generated", status: "success", position: "top", duration: 2000 });
    } catch (error: any) {
      toast({ title: errorMessage(error, "Failed to generate keys"), status: "error", position: "top" });
    } finally {
      setKeyLoading(false);
    }
  };

  return (
    <Panel label="stream settings">
      <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
        <FormControl>
          <FormLabel>Transport</FormLabel>
          <Select value={network} onChange={(e) => update("network", e.target.value)}>
            {NETWORKS.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </Select>
        </FormControl>
        <FormControl>
          <FormLabel>Security</FormLabel>
          <Select value={security} onChange={(e) => update("security", e.target.value)}>
            {SECURITIES.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </Select>
        </FormControl>
      </Grid>

      <Divider my="4" />

      {network === "tcp" && (
        <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>Header type</FormLabel>
            <Select value={stream.tcpSettings?.header?.type || "none"} onChange={(e) => subUpdate("tcpSettings", "header", { type: e.target.value })}>
              <option value="none">none</option>
              <option value="http">http</option>
            </Select>
          </FormControl>
          {stream.tcpSettings?.header?.type === "http" && (
            <FormControl>
              <FormLabel>HTTP Request Path</FormLabel>
              <Input value={stream.tcpSettings?.header?.request?.path || "/"} onChange={(e) => subUpdate("tcpSettings", "header", { type: "http", request: { ...(stream.tcpSettings?.header?.request || {}), path: e.target.value } })} />
            </FormControl>
          )}
        </Grid>
      )}

      {network === "ws" && (
        <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>Path</FormLabel>
            <Input fontFamily="mono" value={stream.wsSettings?.path || "/"} onChange={(e) => subUpdate("wsSettings", "path", e.target.value)} />
          </FormControl>
          <FormControl>
            <FormLabel>Host</FormLabel>
            <Input value={stream.wsSettings?.host || ""} onChange={(e) => subUpdate("wsSettings", "host", e.target.value)} />
          </FormControl>
        </Grid>
      )}

      {network === "httpupgrade" && (
        <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>Path</FormLabel>
            <Input fontFamily="mono" value={stream.httpupgradeSettings?.path || "/"} onChange={(e) => subUpdate("httpupgradeSettings", "path", e.target.value)} />
          </FormControl>
          <FormControl>
            <FormLabel>Host</FormLabel>
            <Input value={stream.httpupgradeSettings?.host || ""} onChange={(e) => subUpdate("httpupgradeSettings", "host", e.target.value)} />
          </FormControl>
        </Grid>
      )}

      {network === "xhttp" && (
        <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>Mode</FormLabel>
            <Select value={stream.xhttpSettings?.mode || "auto"} onChange={(e) => subUpdate("xhttpSettings", "mode", e.target.value)}>
              <option value="auto">auto</option>
              <option value="packet-up">packet-up</option>
              <option value="stream-up">stream-up</option>
              <option value="stream-one">stream-one</option>
            </Select>
          </FormControl>
          <FormControl>
            <FormLabel>Path</FormLabel>
            <Input fontFamily="mono" value={stream.xhttpSettings?.path || "/"} onChange={(e) => subUpdate("xhttpSettings", "path", e.target.value)} />
          </FormControl>
          <FormControl>
            <FormLabel>Host</FormLabel>
            <Input value={stream.xhttpSettings?.host || ""} onChange={(e) => subUpdate("xhttpSettings", "host", e.target.value)} />
          </FormControl>
        </Grid>
      )}

      {network === "grpc" && (
        <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>Service Name</FormLabel>
            <Input fontFamily="mono" value={stream.grpcSettings?.serviceName || ""} onChange={(e) => subUpdate("grpcSettings", "serviceName", e.target.value)} />
          </FormControl>
          <FormControl>
            <FormLabel>Multi-mode</FormLabel>
            <Checkbox isChecked={stream.grpcSettings?.multiMode === true} onChange={(e) => subUpdate("grpcSettings", "multiMode", e.target.checked)}>
              включить
            </Checkbox>
          </FormControl>
        </Grid>
      )}

      {network === "kcp" && (
        <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>MTU</FormLabel>
            <NumberInput value={stream.kcpSettings?.mtu || 1350} onChange={(_, value) => subUpdate("kcpSettings", "mtu", value)}>
              <NumberInputField />
            </NumberInput>
          </FormControl>
          <FormControl>
            <FormLabel>TTI</FormLabel>
            <NumberInput value={stream.kcpSettings?.tti || 50} onChange={(_, value) => subUpdate("kcpSettings", "tti", value)}>
              <NumberInputField />
            </NumberInput>
          </FormControl>
          <FormControl>
            <FormLabel>Uplink Capacity (MB/s)</FormLabel>
            <NumberInput value={stream.kcpSettings?.uplinkCapacity || 5} onChange={(_, value) => subUpdate("kcpSettings", "uplinkCapacity", value)}>
              <NumberInputField />
            </NumberInput>
          </FormControl>
          <FormControl>
            <FormLabel>Downlink Capacity (MB/s)</FormLabel>
            <NumberInput value={stream.kcpSettings?.downlinkCapacity || 20} onChange={(_, value) => subUpdate("kcpSettings", "downlinkCapacity", value)}>
              <NumberInputField />
            </NumberInput>
          </FormControl>
          <FormControl>
            <FormLabel>Congestion</FormLabel>
            <Checkbox isChecked={stream.kcpSettings?.congestion === true} onChange={(e) => subUpdate("kcpSettings", "congestion", e.target.checked)}>
              включить
            </Checkbox>
          </FormControl>
          <FormControl>
            <FormLabel>Header type</FormLabel>
            <Select value={stream.kcpSettings?.header?.type || "none"} onChange={(e) => subUpdate("kcpSettings", "header", { type: e.target.value })}>
              <option value="none">none</option>
              <option value="srtp">srtp</option>
              <option value="utp">utp</option>
              <option value="wechat-video">wechat-video</option>
              <option value="dtls">dtls</option>
              <option value="wireguard">wireguard</option>
              <option value="dns">dns</option>
            </Select>
          </FormControl>
        </Grid>
      )}

      {network === "http2" && (
        <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>Path</FormLabel>
            <Input fontFamily="mono" value={stream.http2Settings?.path || "/"} onChange={(e) => subUpdate("http2Settings", "path", e.target.value)} />
          </FormControl>
          <FormControl>
            <FormLabel>Host</FormLabel>
            <Input value={stream.http2Settings?.host || ""} onChange={(e) => subUpdate("http2Settings", "host", e.target.value)} />
          </FormControl>
        </Grid>
      )}

      {network === "quic" && (
        <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>Key</FormLabel>
            <Input value={stream.quicSettings?.key || ""} onChange={(e) => subUpdate("quicSettings", "key", e.target.value)} />
          </FormControl>
          <FormControl>
            <FormLabel>Security</FormLabel>
            <Select value={stream.quicSettings?.security || "none"} onChange={(e) => subUpdate("quicSettings", "security", e.target.value)}>
              <option value="none">none</option>
              <option value="aes-128-gcm">aes-128-gcm</option>
              <option value="chacha20-poly1305">chacha20-poly1305</option>
            </Select>
          </FormControl>
          <FormControl>
            <FormLabel>Header type</FormLabel>
            <Select value={stream.quicSettings?.header?.type || "none"} onChange={(e) => subUpdate("quicSettings", "header", { type: e.target.value })}>
              <option value="none">none</option>
              <option value="srtp">srtp</option>
              <option value="utp">utp</option>
              <option value="wechat-video">wechat-video</option>
              <option value="dtls">dtls</option>
            </Select>
          </FormControl>
        </Grid>
      )}

      {security === "tls" && (
        <>
          <Divider my="4" />
          <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
            <FormControl>
              <FormLabel>SNI (Server Name)</FormLabel>
              <Input value={stream.tlsSettings?.serverName || ""} onChange={(e) => subUpdate("tlsSettings", "serverName", e.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>ALPN</FormLabel>
              <Input placeholder="h2,http/1.1" value={stream.tlsSettings?.alpn || ""} onChange={(e) => subUpdate("tlsSettings", "alpn", e.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>Сертификат: файл (путь на сервере)</FormLabel>
              <Input fontFamily="mono" value={stream.tlsSettings?.certificates?.[0]?.certificateFile || ""} onChange={(e) => subUpdate("tlsSettings", "certificates", [{ ...(stream.tlsSettings?.certificates?.[0] || {}), certificateFile: e.target.value }])} />
            </FormControl>
            <FormControl>
              <FormLabel>Ключ: файл (путь на сервере)</FormLabel>
              <Input fontFamily="mono" value={stream.tlsSettings?.certificates?.[0]?.keyFile || ""} onChange={(e) => subUpdate("tlsSettings", "certificates", [{ ...(stream.tlsSettings?.certificates?.[0] || {}), keyFile: e.target.value }])} />
            </FormControl>
          </Grid>
          <HStack mt="4">
            <Checkbox isChecked={stream.tlsSettings?.allowInsecure === true} onChange={(e) => subUpdate("tlsSettings", "allowInsecure", e.target.checked)}>
              разрешить небезопасное соединение
            </Checkbox>
          </HStack>
        </>
      )}

      {security === "reality" && (
        <>
          <Divider my="4" />
          <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
            <FormControl>
              <FormLabel>Dest / SNI (serverNames)</FormLabel>
              <Input
                fontFamily="mono"
                placeholder="yahoo.com:443"
                value={(stream.realitySettings?.serverNames || []).join(",")}
                onChange={(e) => subUpdate("realitySettings", "serverNames", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
              />
            </FormControl>
            <FormControl>
              <FormLabel>Client Fingerprint</FormLabel>
              <Select value={stream.realitySettings?.fingerprint || "chrome"} onChange={(e) => subUpdate("realitySettings", "fingerprint", e.target.value)}>
                {["chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq", "random", "randomized"].map((fp) => (
                  <option key={fp} value={fp}>{fp}</option>
                ))}
              </Select>
            </FormControl>
            <FormControl isRequired>
              <FormLabel>Private Key</FormLabel>
              <HStack>
                <Input fontFamily="mono" value={stream.realitySettings?.privateKey || ""} onChange={(e) => subUpdate("realitySettings", "privateKey", e.target.value)} />
                <Button variant="outline" size="sm" isLoading={keyLoading} onClick={() => void generateKeys()}>
                  Сгенерировать
                </Button>
              </HStack>
            </FormControl>
            <FormControl>
              <FormLabel>Public Key</FormLabel>
              <Input fontFamily="mono" value={stream.realitySettings?.publicKey || ""} onChange={(e) => subUpdate("realitySettings", "publicKey", e.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>Short IDs (через запятую)</FormLabel>
              <Input
                fontFamily="mono"
                value={(stream.realitySettings?.shortIds || []).join(",")}
                onChange={(e) => subUpdate("realitySettings", "shortIds", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
              />
            </FormControl>
            <FormControl>
              <FormLabel>SpiderX</FormLabel>
              <Input fontFamily="mono" value={stream.realitySettings?.spiderX || ""} onChange={(e) => subUpdate("realitySettings", "spiderX", e.target.value)} />
            </FormControl>
          </Grid>
        </>
      )}
    </Panel>
  );
};

const InboundsSection: FC = () => {
  const toast = useToast();
  const [inbounds, setInbounds] = useState<ManagedInbound[]>([]);
  const [draft, setDraft] = useState<ManagedInbound | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ManagedInbound | null>(null);
  const [clientModalOpen, setClientModalOpen] = useState(false);
  const [editingClientIndex, setEditingClientIndex] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetch<ManagedInbound[]>("/core/inbounds");
      setInbounds(data);
    } catch (error: any) {
      toast({ title: errorMessage(error, "Failed to load inbounds"), status: "error", position: "top" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const clients = draft?.settings?.clients || [];
  const update = (values: Partial<ManagedInbound>) =>
    setDraft((current) => (current ? { ...current, ...values } : current));

  const openClientModal = (index: number | null) => {
    setEditingClientIndex(index);
    setClientModalOpen(true);
  };

  const saveClient = (client: InboundClient) => {
    if (!draft) return;
    const next = [...clients];
    if (editingClientIndex !== null) {
      next[editingClientIndex] = client;
    } else {
      next.push(client);
    }
    update({ settings: { ...draft.settings, clients: next } });
  };

  const removeClient = (index: number) => {
    if (!draft) return;
    const next = clients.filter((_, i) => i !== index);
    update({ settings: { ...draft.settings, clients: next } });
  };

  const save = async () => {
    if (!draft) return;
    setSaving(true);
    const isEdit = inbounds.some((item) => item.tag === draft.tag);
    try {
      if (isEdit) {
        await fetch(`/core/inbounds/${encodeURIComponent(draft.tag)}`, {
          method: "PUT",
          body: {
            protocol: draft.protocol,
            listen: draft.listen || undefined,
            port: draft.port ?? undefined,
            settings: clean(draft.settings || {}),
            streamSettings: clean(draft.streamSettings || {}),
            sniffing: clean(draft.sniffing || {}),
          },
        });
      } else {
        await fetch("/core/inbounds", { method: "POST", body: { ...draft } });
      }
      toast({ title: "Inbound сохранён, Xray перезапущен", status: "success", position: "top" });
      setDraft(null);
      await load();
    } catch (error: any) {
      toast({ title: errorMessage(error, "Invalid inbound"), status: "error", position: "top" });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (inbound: ManagedInbound) => {
    setSaving(true);
    try {
      await fetch(`/core/inbounds/${encodeURIComponent(inbound.tag)}`, { method: "DELETE" });
      toast({ title: "Inbound удалён, Xray перезапущен", status: "success", position: "top" });
      setDeleteTarget(null);
      await load();
    } catch (error: any) {
      toast({ title: errorMessage(error, "Failed to delete inbound"), status: "error", position: "top" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <VStack align="stretch" spacing="4">
      <Alert status="info" fontSize="sm">
        <AlertIcon />
        Создание inbound-подключений как в 3x-ui: клиенты, стрим-настройки, TLS/Reality.
        Сохранение валидирует конфиг, пишет XRAY_JSON и перезапускает Xray и ноды.
      </Alert>

      <Panel label="inbounds">
        {loading ? (
          <Spinner />
        ) : (
          <Box overflowX="auto">
            <Table size="sm" fontFamily="mono">
              <Thead>
                <Tr>
                  <Th>tag</Th>
                  <Th>protocol</Th>
                  <Th>port</Th>
                  <Th>network</Th>
                  <Th>security</Th>
                  <Th>clients</Th>
                  <Th />
                </Tr>
              </Thead>
              <Tbody>
                {inbounds.length === 0 && (
                  <Tr>
                    <Td colSpan={7}>
                      <Text color="gray.500">Нет inbounds.</Text>
                    </Td>
                  </Tr>
                )}
                {inbounds.map((inbound) => (
                  <Tr key={inbound.tag}>
                    <Td>{inbound.tag}</Td>
                    <Td>
                      <Badge colorScheme="primary">{inbound.protocol}</Badge>
                    </Td>
                    <Td>{inbound.port ?? "—"}</Td>
                    <Td>{inbound.streamSettings?.network || "—"}</Td>
                    <Td>{inbound.streamSettings?.security || "none"}</Td>
                    <Td>{inbound.settings?.clients?.length ?? 0}</Td>
                    <Td>
                      <HStack justify="flex-end" spacing="2">
                        <Button size="xs" variant="ghost" onClick={() => setDraft({ ...inbound })}>
                          edit
                        </Button>
                        <Button size="xs" variant="ghost" colorScheme="red" onClick={() => setDeleteTarget(inbound)}>
                          delete
                        </Button>
                      </HStack>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
        <HStack mt="4" spacing="3">
          <Button size="sm" colorScheme="primary" onClick={() => setDraft({ ...emptyDraft })}>
            + Новый inbound
          </Button>
          <Button size="sm" variant="ghost" onClick={() => void load()}>
            Обновить
          </Button>
        </HStack>
      </Panel>

      <Modal
        isOpen={draft !== null}
        onClose={() => setDraft(null)}
        size="4xl"
        scrollBehavior="inside"
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {inbounds.some((item) => item.tag === draft?.tag)
              ? `Редактирование: ${draft?.tag}`
              : "Новый inbound"}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {draft && (
              <VStack align="stretch" spacing="4">
                <Panel label="basic">
                  <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
                    <FormControl isRequired>
                      <FormLabel>Tag (Remark)</FormLabel>
                      <Input
                        fontFamily="mono"
                        value={draft.tag}
                        isDisabled={inbounds.some((item) => item.tag === draft.tag)}
                        onChange={(event) => update({ tag: event.target.value })}
                      />
                    </FormControl>
                    <FormControl isRequired>
                      <FormLabel>Протокол</FormLabel>
                      <Select value={draft.protocol} onChange={(event) => update({ protocol: event.target.value })}>
                        {PROTOCOLS.map((protocol) => (
                          <option key={protocol} value={protocol}>{protocol}</option>
                        ))}
                      </Select>
                    </FormControl>
                    <FormControl>
                      <FormLabel>Listen IP</FormLabel>
                      <Input fontFamily="mono" value={draft.listen || ""} onChange={(event) => update({ listen: event.target.value })} />
                    </FormControl>
                    <FormControl>
                      <FormLabel>Порт</FormLabel>
                      <NumberInput value={draft.port ?? 0} onChange={(_, value) => update({ port: value })}>
                        <NumberInputField />
                      </NumberInput>
                    </FormControl>
                  </Grid>
                </Panel>

                {CLIENT_PROTOCOLS.includes(draft.protocol) && (
                  <Panel label={`clients (${clients.length})`}>
                    <Box overflowX="auto">
                      <Table size="sm" fontFamily="mono">
                        <Thead>
                          <Tr>
                            <Th>email</Th>
                            <Th>id / password</Th>
                            <Th>flow</Th>
                            <Th>limitIp</Th>
                            <Th>traffic</Th>
                            <Th>expiry</Th>
                            <Th>status</Th>
                            <Th />
                          </Tr>
                        </Thead>
                        <Tbody>
                          {clients.length === 0 && (
                            <Tr>
                              <Td colSpan={8}>
                                <Text color="gray.500">Нет клиентов.</Text>
                              </Td>
                            </Tr>
                          )}
                          {clients.map((client, index) => (
                            <Tr key={index} opacity={client.enable === false ? 0.5 : 1}>
                              <Td>{client.email}</Td>
                              <Td maxW="200px" isTruncated title={client.id || client.password}>
                                {client.id || client.password}
                              </Td>
                              <Td>{client.flow || "—"}</Td>
                              <Td>{client.limitIp ?? 0}</Td>
                              <Td>{client.totalGB ? `${(client.totalGB / 1073741824).toFixed(1)} GB` : "∞"}</Td>
                              <Td>{client.expiryTime ? `${Math.round(client.expiryTime / 86400000)}d` : "∞"}</Td>
                              <Td>
                                <Badge colorScheme={client.enable === false ? "red" : "green"}>
                                  {client.enable === false ? "off" : "on"}
                                </Badge>
                              </Td>
                              <Td>
                                <HStack justify="flex-end" spacing="2">
                                  <Button size="xs" variant="ghost" onClick={() => openClientModal(index)}>edit</Button>
                                  <Button size="xs" variant="ghost" colorScheme="red" onClick={() => removeClient(index)}>del</Button>
                                </HStack>
                              </Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    </Box>
                    <HStack mt="3">
                      <Button size="sm" colorScheme="primary" variant="outline" onClick={() => openClientModal(null)}>
                        + Добавить клиента
                      </Button>
                    </HStack>
                  </Panel>
                )}

                {draft.protocol === "vless" && (
                  <Panel label="decryption">
                    <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
                      <FormControl>
                        <FormLabel>Decryption</FormLabel>
                        <Select value={draft.settings?.decryption || "none"} onChange={(e) => update({ settings: { ...draft.settings, decryption: e.target.value } })}>
                          <option value="none">none</option>
                        </Select>
                      </FormControl>
                    </Grid>
                  </Panel>
                )}

                <StreamSettings
                  stream={draft.streamSettings || {}}
                  onChange={(streamSettings) => update({ streamSettings })}
                />

                <Panel label="sniffing">
                  <HStack spacing="6" flexWrap="wrap">
                    <Checkbox
                      isChecked={draft.sniffing?.enabled === true}
                      onChange={(e) => update({ sniffing: { ...draft.sniffing, enabled: e.target.checked } })}
                    >
                      включить sniffing
                    </Checkbox>
                    <Checkbox
                      isChecked={(draft.sniffing?.destOverride || []).includes("http")}
                      onChange={(e) => {
                        const current = draft.sniffing?.destOverride || [];
                        update({
                          sniffing: {
                            ...draft.sniffing,
                            destOverride: e.target.checked
                              ? [...current, "http"]
                              : current.filter((v: string) => v !== "http"),
                          },
                        });
                      }}
                    >
                      http
                    </Checkbox>
                    <Checkbox
                      isChecked={(draft.sniffing?.destOverride || []).includes("tls")}
                      onChange={(e) => {
                        const current = draft.sniffing?.destOverride || [];
                        update({
                          sniffing: {
                            ...draft.sniffing,
                            destOverride: e.target.checked
                              ? [...current, "tls"]
                              : current.filter((v: string) => v !== "tls"),
                          },
                        });
                      }}
                    >
                      tls
                    </Checkbox>
                    <Checkbox
                      isChecked={(draft.sniffing?.destOverride || []).includes("quic")}
                      onChange={(e) => {
                        const current = draft.sniffing?.destOverride || [];
                        update({
                          sniffing: {
                            ...draft.sniffing,
                            destOverride: e.target.checked
                              ? [...current, "quic"]
                              : current.filter((v: string) => v !== "quic"),
                          },
                        });
                      }}
                    >
                      quic
                    </Checkbox>
                  </HStack>
                </Panel>
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <HStack spacing="3">
              <Button variant="ghost" onClick={() => setDraft(null)}>
                Отмена
              </Button>
              <Button
                colorScheme="primary"
                isLoading={saving}
                isDisabled={!draft?.tag}
                onClick={() => void save()}
              >
                Сохранить и перезапустить Xray
              </Button>
            </HStack>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <ClientModal
        protocol={draft?.protocol || "vless"}
        initial={editingClientIndex !== null ? clients[editingClientIndex] : null}
        isOpen={clientModalOpen}
        onClose={() => setClientModalOpen(false)}
        onSave={saveClient}
      />

      <Modal isOpen={deleteTarget !== null} onClose={() => setDeleteTarget(null)} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Удалить inbound</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text>
              Вы уверены, что хотите удалить inbound <b>{deleteTarget?.tag}</b>?
              Xray будет перезапущен, пользователи этого inbound потеряют подключение.
            </Text>
          </ModalBody>
          <ModalFooter>
            <HStack spacing="3">
              <Button variant="ghost" onClick={() => setDeleteTarget(null)}>
                Отмена
              </Button>
              <Button
                colorScheme="red"
                isLoading={saving}
                onClick={() => deleteTarget && void remove(deleteTarget)}
              >
                Удалить
              </Button>
            </HStack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </VStack>
  );
};

export const InboundsPage = () => (
  <Box>
    <Header title="Inbounds" />
    <Box mt="4">
      <InboundsSection />
    </Box>
  </Box>
);
