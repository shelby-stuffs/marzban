import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
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
  Select,
  Spinner,
  Table,
  Tbody,
  Td,
  Text,
  Textarea,
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

type ManagedInbound = {
  tag: string;
  protocol: string;
  listen?: string | null;
  port?: number | null;
  settings: Settings;
  streamSettings: Settings;
  sniffing: Settings;
};

const PROTOCOLS = ["vless", "vmess", "trojan", "shadowsocks", "dokodemo-door", "socks", "http", "wireguard"];
const NETWORKS = ["tcp", "ws", "grpc", "kcp", "httpupgrade", "xhttp", "http2", "quic"];
const SECURITIES = ["none", "tls", "reality"];

const emptyDraft: ManagedInbound & { id?: string } = {
  tag: "",
  protocol: "vless",
  listen: "0.0.0.0",
  port: 443,
  settings: { clients: [], decryption: "none" },
  streamSettings: { network: "ws", security: "none" },
  sniffing: { enabled: true, destOverride: ["http", "tls"] },
};

const clean = (settings: Settings) => Object.fromEntries(
  Object.entries(settings).filter(([, value]) => value !== "" && value !== undefined && value !== null)
);

const errorMessage = (error: any, fallback: string) =>
  error?.response?._data?.detail || error?.message || fallback;

const when = (value?: string | number | null) =>
  value !== undefined && value !== null && value !== "" ? String(value) : "—";

const JsonField = ({ label, value, onChange }: { label: string; value: unknown; onChange: (value: unknown) => void }) => {
  const [text, setText] = useState(value ? JSON.stringify(value, null, 2) : "");
  useEffect(() => setText(value ? JSON.stringify(value, null, 2) : ""), [value]);
  return (
    <FormControl>
      <FormLabel>{label}</FormLabel>
      <Textarea
        minH="150px" fontFamily="mono" value={text}
        onChange={(event) => setText(event.target.value)}
        onBlur={() => {
          if (!text.trim()) return onChange(undefined);
          try { onChange(JSON.parse(text)); } catch { /* validated before save */ }
        }}
      />
    </FormControl>
  );
};

const InboundsSection: FC = () => {
  const toast = useToast();
  const [inbounds, setInbounds] = useState<ManagedInbound[]>([]);
  const [draft, setDraft] = useState<ManagedInbound | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ManagedInbound | null>(null);

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

  const update = (values: Partial<ManagedInbound>) =>
    setDraft((current) => (current ? { ...current, ...values } : current));

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
      toast({ title: "Inbound saved, Xray restarted", status: "success", position: "top" });
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
      toast({ title: "Inbound deleted, Xray restarted", status: "success", position: "top" });
      setDeleteTarget(null);
      await load();
    } catch (error: any) {
      toast({ title: errorMessage(error, "Failed to delete inbound"), status: "error", position: "top" });
    } finally {
      setSaving(false);
    }
  };

  const network = draft?.streamSettings?.network || "";
  const security = draft?.streamSettings?.security || "";

  return (
    <VStack align="stretch" spacing="4">
      <Alert status="info" fontSize="sm">
        <AlertIcon />
        Создание inbound-подключений как в 3x-ui. Сохранение валидирует конфиг, пишет XRAY_JSON
        и перезапускает Xray и подключённые ноды.
      </Alert>

      <Panel label="managed inbounds">
        {loading ? (
          <Spinner />
        ) : (
          <Box overflowX="auto">
            <Table size="sm" fontFamily="mono">
              <Thead>
                <Tr>
                  <Th>tag</Th>
                  <Th>protocol</Th>
                  <Th>listen</Th>
                  <Th>port</Th>
                  <Th>network</Th>
                  <Th>security</Th>
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
                    <Td>{inbound.listen || "—"}</Td>
                    <Td>{inbound.port ?? "—"}</Td>
                    <Td>{inbound.streamSettings?.network || "—"}</Td>
                    <Td>{inbound.streamSettings?.security || "none"}</Td>
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
            Новый inbound
          </Button>
          <Button size="sm" variant="ghost" onClick={() => void load()}>
            Обновить
          </Button>
        </HStack>
      </Panel>

      <Modal
        isOpen={draft !== null}
        onClose={() => setDraft(null)}
        size="3xl"
        scrollBehavior="inside"
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {inbounds.some((item) => item.tag === draft?.tag)
              ? `Редактирование inbound: ${draft?.tag}`
              : "Новый inbound"}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {draft && (
              <VStack align="stretch" spacing="4">
                <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
                  <FormControl isRequired>
                    <FormLabel>Tag</FormLabel>
                    <Input
                      fontFamily="mono"
                      value={draft.tag}
                      isDisabled={inbounds.some((item) => item.tag === draft.tag)}
                      onChange={(event) => update({ tag: event.target.value })}
                    />
                  </FormControl>
                  <FormControl isRequired>
                    <FormLabel>Протокол</FormLabel>
                    <Select
                      value={draft.protocol}
                      onChange={(event) => update({ protocol: event.target.value })}
                    >
                      {PROTOCOLS.map((protocol) => (
                        <option key={protocol} value={protocol}>{protocol}</option>
                      ))}
                    </Select>
                  </FormControl>
                  <FormControl>
                    <FormLabel>Listen</FormLabel>
                    <Input
                      fontFamily="mono"
                      value={draft.listen || ""}
                      onChange={(event) => update({ listen: event.target.value })}
                    />
                  </FormControl>
                  <FormControl>
                    <FormLabel>Порт</FormLabel>
                    <Input
                      type="number"
                      value={draft.port ?? ""}
                      onChange={(event) =>
                        update({ port: event.target.value === "" ? null : Number(event.target.value) })
                      }
                    />
                  </FormControl>
                </Grid>

                <Panel label="stream settings">
                  <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
                    <FormControl>
                      <FormLabel>Network</FormLabel>
                      <Select
                        value={network}
                        onChange={(event) =>
                          update({ streamSettings: { ...draft.streamSettings, network: event.target.value } })
                        }
                      >
                        {NETWORKS.map((value) => (
                          <option key={value} value={value}>{value}</option>
                        ))}
                      </Select>
                    </FormControl>
                    <FormControl>
                      <FormLabel>Security</FormLabel>
                      <Select
                        value={security}
                        onChange={(event) =>
                          update({ streamSettings: { ...draft.streamSettings, security: event.target.value } })
                        }
                      >
                        {SECURITIES.map((value) => (
                          <option key={value} value={value}>{value}</option>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  {security === "reality" && (
                    <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap="4" mt="4">
                      <JsonField
                        label="realitySettings (JSON)"
                        value={draft.streamSettings?.realitySettings}
                        onChange={(value) =>
                          update({ streamSettings: { ...draft.streamSettings, realitySettings: value } })
                        }
                      />
                    </Grid>
                  )}
                  {security === "tls" && (
                    <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap="4" mt="4">
                      <JsonField
                        label="tlsSettings (JSON)"
                        value={draft.streamSettings?.tlsSettings}
                        onChange={(value) =>
                          update({ streamSettings: { ...draft.streamSettings, tlsSettings: value } })
                        }
                      />
                    </Grid>
                  )}
                  {network === "ws" && (
                    <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap="4" mt="4">
                      <JsonField
                        label="wsSettings (JSON)"
                        value={draft.streamSettings?.wsSettings}
                        onChange={(value) =>
                          update({ streamSettings: { ...draft.streamSettings, wsSettings: value } })
                        }
                      />
                    </Grid>
                  )}
                  {network === "grpc" && (
                    <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap="4" mt="4">
                      <JsonField
                        label="grpcSettings (JSON)"
                        value={draft.streamSettings?.grpcSettings}
                        onChange={(value) =>
                          update({ streamSettings: { ...draft.streamSettings, grpcSettings: value } })
                        }
                      />
                    </Grid>
                  )}
                </Panel>

                <Grid templateColumns={{ base: "1fr", lg: "repeat(3, 1fr)" }} gap="4">
                  <JsonField
                    label="settings (JSON)"
                    value={draft.settings}
                    onChange={(value) => update({ settings: value as Settings })}
                  />
                  <JsonField
                    label="streamSettings (JSON)"
                    value={draft.streamSettings}
                    onChange={(value) => update({ streamSettings: value as Settings })}
                  />
                  <JsonField
                    label="sniffing (JSON)"
                    value={draft.sniffing}
                    onChange={(value) => update({ sniffing: value as Settings })}
                  />
                </Grid>
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
            <Text fontSize="xs" color="gray.500" mt="2">
              {when(deleteTarget?.port)}
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
