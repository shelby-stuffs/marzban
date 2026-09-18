import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Checkbox,
  Code,
  FormControl,
  FormHelperText,
  FormLabel,
  Grid,
  HStack,
  Input,
  Select,
  Spinner,
  Switch,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
  Textarea,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { AnsiLogViewer } from "components/AnsiLogViewer";
import { Header } from "components/Header";
import { JsonEditor } from "components/JsonEditor";
import { Panel } from "components/Panel";
import { SingBoxInboundDialog } from "components/SingBoxInboundDialog";
import { SingBoxObjectDialog } from "components/SingBoxObjectDialog";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetch } from "service/http";

type HysteriaSettings = {
  enabled: boolean;
  tag: string;
  listen: string;
  listen_port: number;
  up_mbps: number | null;
  down_mbps: number | null;
  ignore_client_bandwidth: boolean;
  obfs_type: "" | "salamander";
  obfs_password: string;
  certificate_path: string;
  key_path: string;
  alpn: string[];
  masquerade: string;
  subscription_enabled: boolean;
  subscription_address: string;
  subscription_port: number | null;
  subscription_sni: string;
  subscription_insecure: boolean;
  subscription_remark: string;
};

type SettingsResponse = {
  settings: HysteriaSettings;
  source?: string;
  persisted: boolean;
  feature_enabled: boolean;
  runtime_started: boolean;
};


type AdvancedConfigResponse = {
  config: Record<string, unknown>;
  persisted: boolean;
  allowed_top_level_keys: string[];
  reserved_top_level_keys: string[];
};

type SingBoxInbound = Record<string, unknown>;
type SingBoxSchema = Record<string, any>;
type ObjectDialogState = {
  section: "inbounds" | "outbounds" | "dnsServers" | "endpoints" | "services";
  index: number | null;
  value: SingBoxInbound;
};

const INBOUND_TYPES = ["anytls", "cloudflared", "direct", "http", "hysteria", "hysteria2", "mixed", "naive", "redirect", "shadowsocks", "shadowtls", "snell", "socks", "tproxy", "trojan", "tuic", "tun", "vless", "vmess"];
const OUTBOUND_TYPES = ["anytls", "block", "bridge", "direct", "http", "hysteria", "hysteria2", "naive", "selector", "shadowsocks", "shadowtls", "socks", "ssh", "tor", "trojan", "tuic", "urltest", "vless", "vmess"];
const DNS_SERVER_TYPES = ["dhcp", "fakeip", "h3", "hosts", "https", "local", "mdns", "openconnect", "openvpn", "quic", "resolved", "tailscale", "tcp", "tls", "udp"];
const ENDPOINT_TYPES = ["openconnect", "openvpn-client", "openvpn-server", "tailscale", "wireguard"];
const SERVICE_TYPES = ["api", "ccm", "derp", "hysteria-realm", "ocm", "oom-killer", "resolved", "ssm-api", "usbip-client"];
const SUBSCRIPTION_INBOUND_TYPES = ["anytls", "http", "hysteria", "hysteria2", "mixed", "naive", "shadowsocks", "shadowtls", "socks", "trojan", "tuic", "vless", "vmess"];


type RuleSetItem = {
  enabled: boolean;
  tag: string;
  type: "remote" | "local" | "inline";
  format: "binary" | "source";
  url: string;
  path: string;
  download_detour: string;
  update_interval: string;
  outbound: string;
  ip_cidr: string[];
  ip_cidr_match_source: boolean;
};

type RuleSetsSettings = {
  cache_enabled: boolean;
  cache_path: string;
  items: RuleSetItem[];
};

type RuleSetsResponse = {
  settings: RuleSetsSettings;
  persisted: boolean;
  runtime_started: boolean;
};


type LogsResponse = {
  feature_enabled: boolean;
  started: boolean;
  pid: number | null;
  config_path: string | null;
  logs: string[];
};

const password = () =>
  Array.from(crypto.getRandomValues(new Uint8Array(16)))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");

const errorMessage = (error: any) =>
  error?.response?._data?.detail || error?.data?.detail || error?.message || "Request failed";

const readInbounds = (config: Record<string, unknown>): SingBoxInbound[] =>
  Array.isArray(config.inbounds)
    ? config.inbounds.filter((item): item is SingBoxInbound => Boolean(item) && typeof item === "object" && !Array.isArray(item))
    : [];

export const SingBoxSettingsPage = () => {
  const { t } = useTranslation();
  const toast = useToast();
  const singBoxSchemaUri = new URL("sing-box-schema-1.14.json", globalThis.location.href).toString();
  const [form, setForm] = useState<HysteriaSettings | null>(null);
  const [meta, setMeta] = useState<SettingsResponse | null>(null);
  const [preview, setPreview] = useState("");
  const [userCount, setUserCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [logsMeta, setLogsMeta] = useState<LogsResponse | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const logsRef = useRef<HTMLDivElement>(null);
  const [advancedConfig, setAdvancedConfig] = useState<Record<string, unknown>>({});
  const [singBoxSchema, setSingBoxSchema] = useState<SingBoxSchema | null>(null);
  const [inboundDialog, setInboundDialog] = useState<{ index: number | null; value: SingBoxInbound } | null>(null);
  const [objectDialog, setObjectDialog] = useState<ObjectDialogState | null>(null);
  const [inbounds, setInbounds] = useState<SingBoxInbound[]>([]);
  const [outbounds, setOutbounds] = useState<SingBoxInbound[]>([]);
  const [dnsServers, setDnsServers] = useState<SingBoxInbound[]>([]);
  const [endpoints, setEndpoints] = useState<SingBoxInbound[]>([]);
  const [services, setServices] = useState<SingBoxInbound[]>([]);
  const [dnsConfig, setDnsConfig] = useState<Record<string, unknown>>({});
  const [advancedText, setAdvancedText] = useState("{}");
  const [advancedMeta, setAdvancedMeta] = useState<AdvancedConfigResponse | null>(null);
  const [advancedLoading, setAdvancedLoading] = useState(true);
  const [advancedChecking, setAdvancedChecking] = useState(false);
  const [advancedSaving, setAdvancedSaving] = useState(false);
  const [ruleSets, setRuleSets] = useState<RuleSetsSettings>({ cache_enabled: true, cache_path: "/var/lib/marzban/sing-box-cache.db", items: [] });
  const [ruleSetsMeta, setRuleSetsMeta] = useState<RuleSetsResponse | null>(null);
  const [ruleSetsLoading, setRuleSetsLoading] = useState(true);
  const [ruleSetsChecking, setRuleSetsChecking] = useState(false);
  const [ruleSetsSaving, setRuleSetsSaving] = useState(false);
  const [ruleSetsReloading, setRuleSetsReloading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const response = await fetch<SettingsResponse>("/singbox");
      setMeta(response);
      setForm(response.settings);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const loadAdvanced = async () => {
    setAdvancedLoading(true);
    try {
      const response = await fetch<AdvancedConfigResponse>("/singbox/advanced-config");
      setAdvancedMeta(response);
      setAdvancedDocument(response.config);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    } finally {
      setAdvancedLoading(false);
    }
  };

  useEffect(() => { void loadAdvanced(); }, []);

  useEffect(() => {
    void globalThis.fetch(singBoxSchemaUri)
      .then((response) => response.json())
      .then((schema) => setSingBoxSchema(schema))
      .catch((error) => toast({ title: errorMessage(error), status: "error", position: "top" }));
  }, [singBoxSchemaUri]);

  const parseAdvanced = () => {
    const parsed = JSON.parse(advancedText);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error(t("singbox.editorObjectRequired"));
    }
    return parsed as Record<string, unknown>;
  };

  const syncBuilderState = (config: Record<string, unknown>) => {
    setInbounds(readInbounds(config));
    setOutbounds(readInbounds({ inbounds: config.outbounds }));
    const nextDns = config.dns && typeof config.dns === "object" && !Array.isArray(config.dns)
      ? config.dns as Record<string, unknown>
      : {};
    setDnsConfig(nextDns);
    setDnsServers(readInbounds({ inbounds: nextDns.servers }));
    setEndpoints(readInbounds({ inbounds: config.endpoints }));
    setServices(readInbounds({ inbounds: config.services }));
  };

  const setAdvancedDocument = (config: Record<string, unknown>) => {
    setAdvancedConfig(config);
    syncBuilderState(config);
    setAdvancedText(JSON.stringify(config, null, 2));
  };

  const updateCollection = (
    key: "inbounds" | "outbounds" | "endpoints" | "services",
    index: number,
    patch: Record<string, unknown>,
  ) => {
    try {
      const config = parseAdvanced();
      const current = readInbounds({ inbounds: config[key] });
      if (!current[index]) return;
      current[index] = { ...current[index], ...patch };
      config[key] = current;
      setAdvancedDocument(config);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    }
  };

  const addCollectionItem = (
    key: "inbounds" | "outbounds" | "endpoints" | "services",
    item: SingBoxInbound,
  ) => {
    try {
      const config = parseAdvanced();
      const current = readInbounds({ inbounds: config[key] });
      current.push(item);
      config[key] = current;
      setAdvancedDocument(config);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    }
  };

  const removeCollectionItem = (
    key: "inbounds" | "outbounds" | "endpoints" | "services",
    index: number,
  ) => {
    try {
      const config = parseAdvanced();
      config[key] = readInbounds({ inbounds: config[key] }).filter((_, itemIndex) => itemIndex !== index);
      setAdvancedDocument(config);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    }
  };

  const updateInbound = (index: number, key: string, value: unknown) => {
    updateCollection("inbounds", index, { [key]: value });
  };

  const addInbound = () => {
    openInboundDialog();
  };

  const removeInbound = (index: number) => {
    removeCollectionItem("inbounds", index);
  };

  const updateDns = (patch: Record<string, unknown>) => {
    try {
      const config = parseAdvanced();
      const current = config.dns && typeof config.dns === "object" && !Array.isArray(config.dns)
        ? config.dns as Record<string, unknown>
        : {};
      config.dns = { ...current, ...patch };
      setAdvancedDocument(config);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    }
  };

  const updateDnsServer = (index: number, patch: Record<string, unknown>) => {
    if (!dnsServers[index]) return;
    updateDns({
      servers: dnsServers.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item),
    });
  };

  const addDnsServer = () => {
    updateDns({
      servers: [...dnsServers, { type: "local", tag: `dns-${dnsServers.length + 1}` }],
    });
  };

  const removeDnsServer = (index: number) => {
    updateDns({ servers: dnsServers.filter((_, itemIndex) => itemIndex !== index) });
  };

  const collectionFor = (section: ObjectDialogState["section"]) => {
    if (section === "inbounds") return inbounds;
    if (section === "outbounds") return outbounds;
    if (section === "dnsServers") return dnsServers;
    if (section === "endpoints") return endpoints;
    return services;
  };

  const openInboundDialog = (index: number | null = null) => {
    const current = index === null
      ? { type: "vless", tag: `in-${inbounds.length + 1}`, listen: "::", listen_port: 443 }
      : inbounds[index];
    setInboundDialog({ index, value: { ...(current || {}) } });
  };

  const saveInboundDialog = (item: SingBoxInbound) => {
    if (!inboundDialog) return;
    if (inboundDialog.index === null) {
      addCollectionItem("inbounds", item);
    } else {
      replaceCollectionItem("inbounds", inboundDialog.index, item);
    }
  };

  const openObjectDialog = (section: ObjectDialogState["section"], index: number | null = null) => {
    const current = index === null ? {
      inbounds: { type: "mixed" },
      outbounds: { type: "direct" },
      dnsServers: { type: "local" },
      endpoints: { type: "wireguard" },
      services: { type: "api" },
    }[section] : collectionFor(section)[index];
    setObjectDialog({ section, index, value: { ...(current || {}) } });
  };

  const replaceCollectionItem = (section: Exclude<ObjectDialogState["section"], "dnsServers">, index: number, item: SingBoxInbound) => {
    try {
      const config = parseAdvanced();
      const current = readInbounds({ inbounds: config[section] });
      current[index] = item;
      config[section] = current;
      setAdvancedDocument(config);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    }
  };

  const saveObjectDialog = (item: SingBoxInbound) => {
    if (!objectDialog) return;
    if (objectDialog.section === "dnsServers") {
      const servers = objectDialog.index === null
        ? [...dnsServers, item]
        : dnsServers.map((server, index) => index === objectDialog.index ? item : server);
      updateDns({ servers });
      return;
    }
    if (objectDialog.index === null) {
      addCollectionItem(objectDialog.section, item);
    } else {
      replaceCollectionItem(objectDialog.section, objectDialog.index, item);
    }
  };

  const checkAdvanced = async () => {
    setAdvancedChecking(true);
    try {
      const parsed = parseAdvanced();
      const response = await fetch<{ valid: boolean; checked_by_binary: boolean }>("/singbox/advanced-config/check", { method: "POST", body: parsed });
      toast({ title: response.checked_by_binary ? t("singbox.editorValid") : t("singbox.editorStructureValid"), status: "success", position: "top" });
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top", isClosable: true });
    } finally {
      setAdvancedChecking(false);
    }
  };

  const saveAdvanced = async () => {
    setAdvancedSaving(true);
    try {
      const parsed = parseAdvanced();
      const response = await fetch<AdvancedConfigResponse>("/singbox/advanced-config", { method: "PUT", body: parsed });
      setAdvancedMeta(response);
      setAdvancedDocument(response.config);
      toast({ title: t("singbox.editorSaved"), status: "success", position: "top" });
      await showPreview();
      await loadLogs(true);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top", isClosable: true });
    } finally {
      setAdvancedSaving(false);
    }
  };

  const resetAdvanced = () => {
    const defaults = { outbounds: [{ type: "direct", tag: "direct" }], route: { rules: [], final: "direct" } };
    setAdvancedDocument(defaults);
  };

  const loadRuleSets = async () => {
    setRuleSetsLoading(true);
    try {
      const response = await fetch<RuleSetsResponse>("/singbox/rule-sets");
      setRuleSets(response.settings);
      setRuleSetsMeta(response);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    } finally {
      setRuleSetsLoading(false);
    }
  };

  useEffect(() => { void loadRuleSets(); }, []);

  const addRuleSet = (type: "remote" | "inline" = "remote") => setRuleSets((current) => ({
    ...current,
    items: [...current.items, {
      enabled: true,
      tag: `${type === "inline" ? "ip-set" : "rule-set"}-${current.items.length + 1}`,
      type,
      format: "binary",
      url: "",
      path: "",
      download_detour: "direct",
      update_interval: "1d",
      outbound: "",
      ip_cidr: [],
      ip_cidr_match_source: false,
    }],
  }));

  const updateRuleSet = <K extends keyof RuleSetItem>(index: number, key: K, value: RuleSetItem[K]) =>
    setRuleSets((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item),
    }));

  const removeRuleSet = (index: number) => setRuleSets((current) => ({
    ...current,
    items: current.items.filter((_, itemIndex) => itemIndex !== index),
  }));

  const checkRuleSets = async () => {
    setRuleSetsChecking(true);
    try {
      const response = await fetch<{ valid: boolean; checked_by_binary: boolean }>("/singbox/rule-sets/check", { method: "POST", body: ruleSets });
      toast({ title: response.checked_by_binary ? t("singbox.ruleSetsValid") : t("singbox.editorStructureValid"), status: "success", position: "top" });
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top", isClosable: true });
    } finally { setRuleSetsChecking(false); }
  };

  const saveRuleSets = async () => {
    setRuleSetsSaving(true);
    try {
      const response = await fetch<RuleSetsResponse>("/singbox/rule-sets", { method: "PUT", body: ruleSets });
      setRuleSets(response.settings);
      setRuleSetsMeta(response);
      setMeta((current) => current ? { ...current, runtime_started: response.runtime_started } : current);
      toast({ title: t("singbox.ruleSetsSaved"), status: "success", position: "top" });
      await loadLogs(true);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top", isClosable: true });
    } finally { setRuleSetsSaving(false); }
  };

  const reloadRuleSets = async () => {
    setRuleSetsReloading(true);
    try {
      const response = await fetch<{ runtime_started: boolean }>("/singbox/rule-sets/reload", { method: "POST" });
      setMeta((current) => current ? { ...current, runtime_started: response.runtime_started } : current);
      toast({ title: t("singbox.ruleSetsReloaded"), status: "success", position: "top" });
      await loadLogs(true);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top", isClosable: true });
    } finally { setRuleSetsReloading(false); }
  };

  const loadLogs = async (silent = false) => {
    if (!silent) setLogsLoading(true);
    try {
      const response = await fetch<LogsResponse>("/singbox/logs?limit=500");
      setLogsMeta(response);
      setMeta((current) => current ? { ...current, runtime_started: response.started } : current);
    } catch (error) {
      if (!silent) toast({ title: errorMessage(error), status: "error", position: "top" });
    } finally {
      if (!silent) setLogsLoading(false);
    }
  };

  const clearLogs = async () => {
    try {
      await fetch("/singbox/logs", { method: "DELETE" });
      await loadLogs(true);
      toast({ title: t("singbox.logsCleared"), status: "success", position: "top" });
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    }
  };

  useEffect(() => {
    void loadLogs(true);
    if (!autoRefresh) return;
    const timer = window.setInterval(() => void loadLogs(true), 3000);
    return () => window.clearInterval(timer);
  }, [autoRefresh]);

  useEffect(() => {
    if (logsRef.current && autoRefresh) logsRef.current.scrollTop = logsRef.current.scrollHeight;
  }, [logsMeta?.logs, autoRefresh]);

  const update = <K extends keyof HysteriaSettings>(key: K, value: HysteriaSettings[K]) =>
    setForm((current) => current ? { ...current, [key]: value } : current);

  const generate = async () => {
    setGenerating(true);
    try {
      const response = await fetch<{ settings: HysteriaSettings; source: string }>("/singbox/generate", { method: "POST" });
      setForm(response.settings);
      setMeta((current) => current ? { ...current, source: response.source, persisted: false } : current);
      toast({ title: t("hysteria.generated"), status: "success", position: "top" });
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    } finally { setGenerating(false); }
  };

  const save = async () => {
    if (!form) return;
    setSaving(true);
    try {
      const response = await fetch<SettingsResponse>("/singbox", { method: "PUT", body: form });
      setMeta(response);
      setForm(response.settings);
      toast({ title: t("hysteria.saved"), status: "success", position: "top" });
      await showPreview();
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top", isClosable: true });
    } finally { setSaving(false); }
  };

  const showPreview = async () => {
    setPreviewing(true);
    try {
      const response = await fetch<{ config: Record<string, unknown>; user_count: number }>("/singbox/runtime-config");
      setPreview(JSON.stringify(response.config, null, 2));
      setUserCount(response.user_count);
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    } finally { setPreviewing(false); }
  };

  if (loading || !form) return <Box><Header title={t("singbox.title")} /><Spinner mt="4" /></Box>;

  return (
    <VStack align="stretch" spacing="4" w="full">
      <Header title={t("singbox.title")} />
      <Text color="gray.500" fontFamily="mono" fontSize="sm">{t("singbox.description")}</Text>
      <HStack justify="space-between" flexWrap="wrap" gap="3">
        <HStack>
          <Badge colorScheme={meta?.feature_enabled ? "green" : "orange"}>
            {meta?.feature_enabled ? t("hysteria.featureEnabled") : t("hysteria.featureDisabled")}
          </Badge>
          <Badge colorScheme={meta?.runtime_started ? "green" : "gray"}>
            {meta?.runtime_started ? t("hysteria.running") : t("hysteria.stopped")}
          </Badge>
          <Badge>{meta?.persisted ? t("hysteria.savedSource") : meta?.source || t("hysteria.generatedSource")}</Badge>
        </HStack>
      </HStack>

      {!meta?.feature_enabled && (
        <Alert status="warning"><AlertIcon />{t("hysteria.enableHint")}</Alert>
      )}

      <Tabs colorScheme="primary" variant="enclosed" isLazy>
        <TabList overflowX="auto" overflowY="hidden">
          <Tab whiteSpace="nowrap">{t("singbox.tabJsonLogs")}</Tab>
          <Tab whiteSpace="nowrap">{t("singbox.tabInbound")}</Tab>
          <Tab whiteSpace="nowrap">{t("singbox.tabSubscription")}</Tab>
          <Tab whiteSpace="nowrap">{t("singbox.tabRuleSets")}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px="0">
      <Panel label={t("singbox.inboundBuilder")} mb="4">
        <HStack justify="space-between" mb="3" flexWrap="wrap" gap="2">
          <Text color="gray.500" fontSize="sm">{t("singbox.inboundBuilderHelp")}</Text>
          <Button size="sm" colorScheme="primary" onClick={addInbound}>{t("singbox.addInbound")}</Button>
        </HStack>
        {inbounds.length === 0 && <Alert status="info" py="2" fontSize="sm"><AlertIcon />{t("singbox.noInbounds")}</Alert>}
        <VStack align="stretch" spacing="3">
          {inbounds.map((inbound, index) => (
            <Panel key={`${String(inbound.tag || "inbound")}-${index}`} compact label={`${t("singbox.inbound")} ${index + 1}: ${String(inbound.tag || "—")}`}>
              <VStack align="stretch" spacing="3">
                <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", xl: "repeat(4, 1fr)" }} gap="3">
                  <FormControl isRequired>
                    <FormLabel fontSize="xs" mb="1">{t("singbox.inboundType")}</FormLabel>
                    <Select size="sm" fontFamily="mono" value={String(inbound.type || "")} onChange={(event) => updateInbound(index, "type", event.target.value)}>
                      {INBOUND_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
                    </Select>
                  </FormControl>
                  <FormControl isRequired>
                    <FormLabel fontSize="xs" mb="1">{t("singbox.inboundTag")}</FormLabel>
                    <Input size="sm" fontFamily="mono" value={String(inbound.tag || "")} onChange={(event) => updateInbound(index, "tag", event.target.value)} />
                  </FormControl>
                  <FormControl>
                    <FormLabel fontSize="xs" mb="1">{t("singbox.inboundListen")}</FormLabel>
                    <Input size="sm" fontFamily="mono" value={String(inbound.listen || "")} placeholder="::" onChange={(event) => updateInbound(index, "listen", event.target.value)} />
                  </FormControl>
                  <FormControl>
                    <FormLabel fontSize="xs" mb="1">{t("singbox.inboundPort")}</FormLabel>
                    <Input size="sm" type="number" value={typeof inbound.listen_port === "number" ? inbound.listen_port : ""} onChange={(event) => updateInbound(index, "listen_port", event.target.value ? Number(event.target.value) : undefined)} />
                  </FormControl>
                </Grid>
                  <HStack justify="space-between" flexWrap="wrap" gap="2">
                  <Text color="gray.500" fontSize="xs">{t("singbox.inboundAdvancedHelp")}</Text>
                  <HStack><Button size="xs" variant="outline" onClick={() => openInboundDialog(index)}>{t("singbox.editObject")}</Button><Button size="xs" variant="ghost" colorScheme="red" onClick={() => removeInbound(index)}>{t("delete")}</Button></HStack>
                </HStack>
              </VStack>
            </Panel>
          ))}
        </VStack>
      </Panel>
      <Grid templateColumns={{ base: "1fr", xl: "1fr 1fr" }} gap="4" mb="4" alignItems="start">
        <Panel label={t("singbox.outboundBuilder")}>
          <HStack justify="space-between" mb="3" flexWrap="wrap" gap="2">
            <Text color="gray.500" fontSize="sm">{t("singbox.outboundBuilderHelp")}</Text>
            <Button size="sm" colorScheme="primary" onClick={() => openObjectDialog("outbounds")}>{t("singbox.addOutbound")}</Button>
          </HStack>
          {outbounds.length === 0 && <Alert status="info" py="2" fontSize="sm"><AlertIcon />{t("singbox.noOutbounds")}</Alert>}
          <VStack align="stretch" spacing="3">
            {outbounds.map((outbound, index) => (
              <Panel key={`${String(outbound.tag || "outbound")}-${index}`} compact label={`${t("singbox.outbound")} ${index + 1}: ${String(outbound.tag || "—")}`}>
                <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3">
                  <FormControl isRequired>
                    <FormLabel fontSize="xs" mb="1">{t("singbox.outboundType")}</FormLabel>
                    <Select size="sm" fontFamily="mono" value={String(outbound.type || "")} onChange={(event) => updateCollection("outbounds", index, { type: event.target.value })}>
                      {OUTBOUND_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
                    </Select>
                  </FormControl>
                  <FormControl>
                    <FormLabel fontSize="xs" mb="1">{t("singbox.outboundTag")}</FormLabel>
                    <HStack><Input size="sm" fontFamily="mono" value={String(outbound.tag || "")} onChange={(event) => updateCollection("outbounds", index, { tag: event.target.value })} /><Button size="sm" variant="outline" onClick={() => openObjectDialog("outbounds", index)}>{t("singbox.editObject")}</Button><Button size="sm" variant="ghost" colorScheme="red" onClick={() => removeCollectionItem("outbounds", index)}>{t("delete")}</Button></HStack>
                  </FormControl>
                </Grid>
              </Panel>
            ))}
          </VStack>
        </Panel>

        <Panel label={t("singbox.dnsBuilder")}>
          <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3" mb="4">
            <FormControl>
              <FormLabel fontSize="xs" mb="1">{t("singbox.dnsFinal")}</FormLabel>
              <Input size="sm" fontFamily="mono" value={String(dnsConfig.final || "")} placeholder="local" onChange={(event) => updateDns({ final: event.target.value })} />
            </FormControl>
            <FormControl>
              <FormLabel fontSize="xs" mb="1">{t("singbox.dnsStrategy")}</FormLabel>
              <Select size="sm" value={String(dnsConfig.strategy || "")} onChange={(event) => updateDns({ strategy: event.target.value || undefined })}>
                <option value="">default</option><option value="prefer_ipv4">prefer_ipv4</option><option value="prefer_ipv6">prefer_ipv6</option><option value="ipv4_only">ipv4_only</option><option value="ipv6_only">ipv6_only</option>
              </Select>
            </FormControl>
          </Grid>
          <Checkbox size="sm" mb="3" isChecked={dnsConfig.disable_cache === true} onChange={(event) => updateDns({ disable_cache: event.target.checked })}>{t("singbox.dnsDisableCache")}</Checkbox>
          <HStack justify="space-between" mb="3" flexWrap="wrap" gap="2">
            <Text color="gray.500" fontSize="sm">{t("singbox.dnsServersHelp")}</Text>
            <Button size="sm" colorScheme="primary" onClick={() => openObjectDialog("dnsServers")}>{t("singbox.addDnsServer")}</Button>
          </HStack>
          {dnsServers.length === 0 && <Alert status="info" py="2" fontSize="sm"><AlertIcon />{t("singbox.noDnsServers")}</Alert>}
          <VStack align="stretch" spacing="3">
            {dnsServers.map((server, index) => (
              <Panel key={`${String(server.tag || "dns")}-${index}`} compact label={`${t("singbox.dnsServer")} ${index + 1}: ${String(server.tag || "—")}`}>
                <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3">
                  <FormControl isRequired>
                    <FormLabel fontSize="xs" mb="1">{t("singbox.dnsServerType")}</FormLabel>
                    <Select size="sm" fontFamily="mono" value={String(server.type || "")} onChange={(event) => updateDnsServer(index, { type: event.target.value })}>
                      {DNS_SERVER_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
                    </Select>
                  </FormControl>
                  <FormControl>
                    <FormLabel fontSize="xs" mb="1">{t("singbox.dnsServerTag")}</FormLabel>
                    <HStack><Input size="sm" fontFamily="mono" value={String(server.tag || "")} onChange={(event) => updateDnsServer(index, { tag: event.target.value })} /><Button size="sm" variant="outline" onClick={() => openObjectDialog("dnsServers", index)}>{t("singbox.editObject")}</Button><Button size="sm" variant="ghost" colorScheme="red" onClick={() => removeDnsServer(index)}>{t("delete")}</Button></HStack>
                  </FormControl>
                </Grid>
              </Panel>
            ))}
          </VStack>
        </Panel>
      </Grid>

      <Grid templateColumns={{ base: "1fr", xl: "1fr 1fr" }} gap="4" mb="4" alignItems="start">
        <Panel label={t("singbox.endpointBuilder")}>
          <HStack justify="space-between" mb="3" flexWrap="wrap" gap="2">
            <Text color="gray.500" fontSize="sm">{t("singbox.endpointBuilderHelp")}</Text>
            <Button size="sm" colorScheme="primary" onClick={() => openObjectDialog("endpoints")}>{t("singbox.addEndpoint")}</Button>
          </HStack>
          <VStack align="stretch" spacing="3">
            {endpoints.map((endpoint, index) => (
              <Panel key={`${String(endpoint.tag || "endpoint")}-${index}`} compact label={`${t("singbox.endpoint")} ${index + 1}: ${String(endpoint.tag || "—")}`}>
                <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3">
                  <Select size="sm" fontFamily="mono" value={String(endpoint.type || "")} onChange={(event) => updateCollection("endpoints", index, { type: event.target.value })}>{ENDPOINT_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</Select>
                  <HStack><Input size="sm" fontFamily="mono" value={String(endpoint.tag || "")} onChange={(event) => updateCollection("endpoints", index, { tag: event.target.value })} /><Button size="sm" variant="outline" onClick={() => openObjectDialog("endpoints", index)}>{t("singbox.editObject")}</Button><Button size="sm" variant="ghost" colorScheme="red" onClick={() => removeCollectionItem("endpoints", index)}>{t("delete")}</Button></HStack>
                </Grid>
              </Panel>
            ))}
          </VStack>
        </Panel>

        <Panel label={t("singbox.serviceBuilder")}>
          <HStack justify="space-between" mb="3" flexWrap="wrap" gap="2">
            <Text color="gray.500" fontSize="sm">{t("singbox.serviceBuilderHelp")}</Text>
            <Button size="sm" colorScheme="primary" onClick={() => openObjectDialog("services")}>{t("singbox.addService")}</Button>
          </HStack>
          <VStack align="stretch" spacing="3">
            {services.map((service, index) => (
              <Panel key={`${String(service.tag || "service")}-${index}`} compact label={`${t("singbox.service")} ${index + 1}: ${String(service.tag || "—")}`}>
                <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="3">
                  <Select size="sm" fontFamily="mono" value={String(service.type || "")} onChange={(event) => updateCollection("services", index, { type: event.target.value })}>{SERVICE_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</Select>
                  <HStack><Input size="sm" fontFamily="mono" value={String(service.tag || "")} onChange={(event) => updateCollection("services", index, { tag: event.target.value })} /><Button size="sm" variant="outline" onClick={() => openObjectDialog("services", index)}>{t("singbox.editObject")}</Button><Button size="sm" variant="ghost" colorScheme="red" onClick={() => removeCollectionItem("services", index)}>{t("delete")}</Button></HStack>
                </Grid>
              </Panel>
            ))}
          </VStack>
        </Panel>
      </Grid>

      <Panel label={t("singbox.advancedEditor")}>
        <Alert status="warning" mb="4"><AlertIcon />{t("singbox.editorWarning")}</Alert>
        <HStack justify="space-between" mb="3" flexWrap="wrap" gap="2">
          <Text color="gray.500" fontFamily="mono" fontSize="xs">
            {t("singbox.editorAllowed")}: {(advancedMeta?.allowed_top_level_keys || ["log", "dns", "inbounds", "outbounds", "route", "experimental"]).join(", ")}
          </Text>
          <Badge colorScheme={advancedMeta?.persisted ? "green" : "gray"}>{advancedMeta?.persisted ? t("singbox.editorSavedSource") : t("singbox.editorDefaultSource")}</Badge>
        </HStack>
        {advancedLoading ? <Spinner /> : <JsonEditor schemaUri={singBoxSchemaUri} json={advancedConfig} onChange={(value) => {
          setAdvancedText(value);
          try {
            syncBuilderState(JSON.parse(value) as Record<string, unknown>);
          } catch {
            // The editor may be temporarily invalid while the user is typing.
          }
        }} />}
        <HStack justify="flex-end" mt="4" flexWrap="wrap">
          <Button variant="ghost" onClick={resetAdvanced}>{t("singbox.editorReset")}</Button>
          <Button variant="outline" isLoading={advancedChecking} onClick={() => void checkAdvanced()}>{t("singbox.editorCheck")}</Button>
          <Button colorScheme="primary" isLoading={advancedSaving} onClick={() => void saveAdvanced()}>{t("singbox.editorSave")}</Button>
        </HStack>
      </Panel>

      <Panel label={t("singbox.logs")}>
        <HStack justify="space-between" align="center" mb="3" flexWrap="wrap" gap="2">
          <HStack>
            <Badge colorScheme={logsMeta?.started ? "green" : "gray"}>
              {logsMeta?.started ? t("hysteria.running") : t("hysteria.stopped")}
            </Badge>
            {logsMeta?.pid && <Badge variant="outline">{t("singbox.processId")}: {logsMeta.pid}</Badge>}
            <Text color="gray.500" fontFamily="mono" fontSize="xs">{t("singbox.logsHelp")}</Text>
          </HStack>
          <HStack>
            <Button size="sm" variant={autoRefresh ? "solid" : "outline"} onClick={() => setAutoRefresh((value) => !value)}>
              {autoRefresh ? t("singbox.autoRefresh") : t("singbox.paused")}
            </Button>
            <Button size="sm" variant="outline" isLoading={logsLoading} onClick={() => void loadLogs()}>{t("singbox.refresh")}</Button>
            <Button size="sm" variant="ghost" onClick={() => void clearLogs()}>{t("singbox.clearLogs")}</Button>
          </HStack>
        </HStack>
        <AnsiLogViewer
          ref={logsRef}
          logs={logsMeta?.logs || []}
          emptyText={t("singbox.logsEmpty")}
          title={t("singbox.logOutput")}
        />
        {logsMeta?.config_path && <Text mt="2" color="gray.500" fontFamily="mono" fontSize="xs">{t("singbox.configPath")}: {logsMeta.config_path}</Text>}
      </Panel>
          </TabPanel>
          <TabPanel px="0">
            <HStack justify="flex-end" mb="4"><Button variant="outline" isLoading={generating} onClick={() => void generate()}>{t("hysteria.autofill")}</Button></HStack>
      <Grid templateColumns={{ base: "1fr", xl: "1fr 1fr" }} gap="4" alignItems="start">
        <VStack align="stretch" spacing="4">
          <Panel label={t("singbox.hysteriaInbound")}>
            <VStack align="stretch" spacing="4">
              <FormControl display="flex" justifyContent="space-between" alignItems="center">
                <Box><FormLabel mb="0">{t("hysteria.enabled")}</FormLabel><FormHelperText>{t("hysteria.enabledHelp")}</FormHelperText></Box>
                <Switch isChecked={form.enabled} onChange={(event) => update("enabled", event.target.checked)} />
              </FormControl>
              <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
                <FormControl><FormLabel>{t("hysteria.tag")}</FormLabel><Input value={form.tag} onChange={(event) => update("tag", event.target.value)} /></FormControl>
                <FormControl><FormLabel>{t("hysteria.listen")}</FormLabel><Input value={form.listen} onChange={(event) => update("listen", event.target.value)} /></FormControl>
                <FormControl><FormLabel>{t("hysteria.port")}</FormLabel><Input type="number" value={form.listen_port} onChange={(event) => update("listen_port", Number(event.target.value))} /></FormControl>
                <FormControl><FormLabel>ALPN</FormLabel><Input value={form.alpn.join(", ")} onChange={(event) => update("alpn", event.target.value.split(",").map((item) => item.trim()).filter(Boolean))} /></FormControl>
              </Grid>
              <FormControl><FormLabel>{t("hysteria.masquerade")}</FormLabel><Input placeholder="https://example.com" value={form.masquerade} onChange={(event) => update("masquerade", event.target.value)} /><FormHelperText>{t("hysteria.masqueradeHelp")}</FormHelperText></FormControl>
            </VStack>
          </Panel>

          <Panel label={t("hysteria.tls")}>
            <VStack align="stretch" spacing="4">
              <Alert status="info"><AlertIcon />{t("hysteria.tlsHelp")}</Alert>
              <FormControl isRequired><FormLabel>{t("hysteria.certificatePath")}</FormLabel><Input fontFamily="mono" placeholder="/etc/letsencrypt/live/example.com/fullchain.pem" value={form.certificate_path} onChange={(event) => update("certificate_path", event.target.value)} /></FormControl>
              <FormControl isRequired><FormLabel>{t("hysteria.keyPath")}</FormLabel><Input fontFamily="mono" placeholder="/etc/letsencrypt/live/example.com/privkey.pem" value={form.key_path} onChange={(event) => update("key_path", event.target.value)} /></FormControl>
            </VStack>
          </Panel>

        </VStack>

        <VStack align="stretch" spacing="4">
          <Panel label={t("hysteria.salamander")}>
            <VStack align="stretch" spacing="4">
              <FormControl><FormLabel>{t("hysteria.obfs")}</FormLabel><Select value={form.obfs_type} onChange={(event) => update("obfs_type", event.target.value as "" | "salamander")}><option value="">{t("hysteria.noObfs")}</option><option value="salamander">Salamander</option></Select></FormControl>
              {form.obfs_type === "salamander" && <FormControl isRequired><FormLabel>{t("hysteria.obfsPassword")}</FormLabel><HStack><Input fontFamily="mono" value={form.obfs_password} onChange={(event) => update("obfs_password", event.target.value)} /><Button variant="outline" onClick={() => update("obfs_password", password())}>{t("hysteria.generatePassword")}</Button></HStack></FormControl>}
            </VStack>
          </Panel>

          <Panel label={t("hysteria.bandwidth")}>
            <VStack align="stretch" spacing="4">
              <Checkbox isChecked={form.ignore_client_bandwidth} onChange={(event) => update("ignore_client_bandwidth", event.target.checked)}>{t("hysteria.ignoreBandwidth")}</Checkbox>
              <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
                <FormControl isDisabled={form.ignore_client_bandwidth}><FormLabel>{t("hysteria.upMbps")}</FormLabel><Input type="number" value={form.up_mbps ?? ""} onChange={(event) => update("up_mbps", event.target.value ? Number(event.target.value) : null)} /></FormControl>
                <FormControl isDisabled={form.ignore_client_bandwidth}><FormLabel>{t("hysteria.downMbps")}</FormLabel><Input type="number" value={form.down_mbps ?? ""} onChange={(event) => update("down_mbps", event.target.value ? Number(event.target.value) : null)} /></FormControl>
              </Grid>
            </VStack>
          </Panel>

          <Panel label={t("hysteria.generatedConfig")}>
            <HStack justify="space-between" mb="3"><Text color="gray.500">{t("hysteria.usersCount")}: {userCount}</Text><Button size="sm" variant="outline" isLoading={previewing} onClick={() => void showPreview()}>{t("hysteria.preview")}</Button></HStack>
            {preview ? <Textarea value={preview} readOnly minH="320px" fontFamily="mono" fontSize="xs" /> : <Text color="gray.500">{t("hysteria.previewHelp")}</Text>}
            <Text mt="2" fontSize="xs" color="gray.500">{t("hysteria.secretsRedacted")} <Code>***</Code></Text>
          </Panel>
        </VStack>
      </Grid>
      <HStack justify="flex-end" position="sticky" bottom="0" bg="terminal.bg" py="3" borderTop="1px solid" borderColor="terminal.border">
        <Button variant="ghost" onClick={() => void load()}>{t("cancel")}</Button>
        <Button colorScheme="primary" isLoading={saving} onClick={() => void save()}>{t("hysteria.save")}</Button>
      </HStack>
          </TabPanel>
          <TabPanel px="0">
            <Alert status="info" mb="4"><AlertIcon />{t("singbox.dynamicSubscriptionHelp")}</Alert>
            <Panel label={t("singbox.dynamicSubscriptionTitle")}>
              <VStack align="stretch" spacing="3">
                {inbounds.length === 0 && <Alert status="warning" py="2"><AlertIcon />{t("singbox.dynamicSubscriptionEmpty")}</Alert>}
                {inbounds.map((inbound, index) => {
                  const type = String(inbound.type || "");
                  const supported = SUBSCRIPTION_INBOUND_TYPES.includes(type);
                  return (
                    <Box key={`${String(inbound.tag || "inbound")}-${index}`} borderWidth="1px" borderColor="terminal.border" borderRadius="md" p="3">
                      <HStack justify="space-between" flexWrap="wrap" gap="2">
                        <Box display="flex" alignItems="center" gap="2"><>
                          <Badge fontFamily="mono">{type || "unknown"}</Badge>
                          <Text fontFamily="mono">{String(inbound.tag || "—")}</Text>
                          {inbound.listen_port && <Text color="gray.500" fontFamily="mono">:{String(inbound.listen_port)}</Text>}
                        </></Box>
                        <Badge colorScheme={supported ? "green" : "gray"}>{supported ? t("singbox.dynamicSubscriptionIncluded") : t("singbox.dynamicSubscriptionUnsupported")}</Badge>
                      </HStack>
                      <Text mt="2" color="gray.500" fontSize="sm">{supported ? t("singbox.dynamicSubscriptionCredentials") : t("singbox.dynamicSubscriptionSkipReason")}</Text>
                    </Box>
                  );
                })}
              </VStack>
            </Panel>
          </TabPanel>
          <TabPanel px="0">
      {ruleSetsLoading ? <Spinner /> : <VStack align="stretch" spacing="3">
        <Panel compact label={t("singbox.ruleSetCache")}>
          <VStack align="stretch" spacing="3">
            <FormControl display="flex" justifyContent="space-between" alignItems="center">
              <Box><FormLabel mb="0" fontSize="xs">{t("singbox.ruleSetCacheEnabled")}</FormLabel><FormHelperText mt="1" fontSize="10px">{t("singbox.ruleSetCacheHelp")}</FormHelperText></Box>
              <Switch isChecked={ruleSets.cache_enabled} onChange={(event) => setRuleSets((current) => ({ ...current, cache_enabled: event.target.checked }))} />
            </FormControl>
            <FormControl isRequired={ruleSets.cache_enabled}><FormLabel fontSize="xs" mb="1">{t("singbox.ruleSetCachePath")}</FormLabel><Input size="sm" fontFamily="mono" value={ruleSets.cache_path} onChange={(event) => setRuleSets((current) => ({ ...current, cache_path: event.target.value }))} /></FormControl>
          </VStack>
        </Panel>

        <HStack justify="space-between" flexWrap="wrap">
          <Text color="gray.500" fontFamily="mono" fontSize="xs">{t("singbox.ruleSetsHelp")}</Text>
          <HStack spacing="2">
            <Button size="sm" variant="outline" onClick={() => addRuleSet()}>{t("singbox.ruleSetAddRemote")}</Button>
            <Button size="sm" colorScheme="primary" variant="outline" onClick={() => addRuleSet("inline")}>{t("singbox.ruleSetAddIp")}</Button>
          </HStack>
        </HStack>

        {ruleSets.items.length === 0 && <Alert status="info" py="2" fontSize="xs"><AlertIcon />{t("singbox.ruleSetsEmpty")}</Alert>}
        {ruleSets.items.map((item, index) => (
          <Panel key={index} compact label={`${t("singbox.ruleSet")} ${index + 1}: ${item.tag || "—"}`}>
            <VStack align="stretch" spacing="2.5">
              <HStack justify="space-between" minH="24px">
                <Checkbox isChecked={item.enabled} onChange={(event) => updateRuleSet(index, "enabled", event.target.checked)}>{t("singbox.ruleSetEnabled")}</Checkbox>
                <Button size="xs" variant="ghost" colorScheme="red" onClick={() => removeRuleSet(index)}>{t("delete")}</Button>
              </HStack>
              <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", xl: "repeat(4, 1fr)" }} gap="3">
                <FormControl isRequired><FormLabel fontSize="xs" mb="1">{t("singbox.ruleSetTag")}</FormLabel><Input size="sm" fontFamily="mono" value={item.tag} onChange={(event) => updateRuleSet(index, "tag", event.target.value)} /></FormControl>
                <FormControl><FormLabel fontSize="xs" mb="1">{t("singbox.ruleSetType")}</FormLabel><Select size="sm" value={item.type} onChange={(event) => updateRuleSet(index, "type", event.target.value as "remote" | "local" | "inline")}><option value="remote">remote</option><option value="local">local</option><option value="inline">{t("singbox.ruleSetInlineIp")}</option></Select></FormControl>
                {item.type !== "inline" && <FormControl><FormLabel fontSize="xs" mb="1">{t("singbox.ruleSetFormat")}</FormLabel><Select size="sm" value={item.format} onChange={(event) => updateRuleSet(index, "format", event.target.value as "binary" | "source")}><option value="binary">binary (.srs)</option><option value="source">source (JSON)</option></Select></FormControl>}
                <FormControl><FormLabel fontSize="xs" mb="1">{t("singbox.ruleSetOutbound")}</FormLabel><Input size="sm" fontFamily="mono" placeholder="direct" value={item.outbound} onChange={(event) => updateRuleSet(index, "outbound", event.target.value)} /><FormHelperText mt="1" fontSize="10px">{t("singbox.ruleSetOutboundHelp")}</FormHelperText></FormControl>
                <FormControl display="flex" alignItems="center" pt={{ base: "0", xl: "5" }}><Checkbox size="sm" isChecked={item.ip_cidr_match_source} onChange={(event) => updateRuleSet(index, "ip_cidr_match_source", event.target.checked)}>{t("singbox.ruleSetMatchSourceIp")}</Checkbox></FormControl>
              </Grid>
              {item.type === "remote" ? <Grid templateColumns={{ base: "1fr", lg: "2fr 1fr 1fr" }} gap="3">
                <FormControl isRequired={item.enabled}><FormLabel fontSize="xs" mb="1">URL</FormLabel><Input size="sm" fontFamily="mono" placeholder="https://example.com/rules.srs" value={item.url} onChange={(event) => updateRuleSet(index, "url", event.target.value)} /></FormControl>
                <FormControl><FormLabel fontSize="xs" mb="1">{t("singbox.ruleSetDetour")}</FormLabel><Input size="sm" fontFamily="mono" value={item.download_detour} onChange={(event) => updateRuleSet(index, "download_detour", event.target.value)} /></FormControl>
                <FormControl><FormLabel fontSize="xs" mb="1">{t("singbox.ruleSetInterval")}</FormLabel><Input size="sm" fontFamily="mono" placeholder="1d" value={item.update_interval} onChange={(event) => updateRuleSet(index, "update_interval", event.target.value)} /></FormControl>
              </Grid> : item.type === "local" ? <FormControl isRequired={item.enabled}><FormLabel fontSize="xs" mb="1">{t("singbox.ruleSetPath")}</FormLabel><Input size="sm" fontFamily="mono" placeholder="/var/lib/marzban/rules/local.srs" value={item.path} onChange={(event) => updateRuleSet(index, "path", event.target.value)} /></FormControl> : <FormControl isRequired={item.enabled}>
                <HStack justify="space-between" mb="1"><FormLabel fontSize="xs" mb="0">{t("singbox.ruleSetIpCidrs")}</FormLabel><Badge fontSize="10px">{item.ip_cidr.length}</Badge></HStack>
                <Textarea size="sm" minH="110px" resize="vertical" fontFamily="mono" fontSize="xs" placeholder={"1.1.1.1\n10.0.0.0/8\n2001:db8::/32"} value={item.ip_cidr.join("\n")} onChange={(event) => updateRuleSet(index, "ip_cidr", event.target.value.split(/[\n,]+/).map((value) => value.trim()).filter(Boolean))} />
                <FormHelperText mt="1" fontSize="10px">{t("singbox.ruleSetIpCidrsHelp")}</FormHelperText>
              </FormControl>}
            </VStack>
          </Panel>
        ))}

        <Alert status="warning" py="2" fontSize="xs"><AlertIcon />{t("singbox.ruleSetReloadWarning")}</Alert>
        <HStack justify="flex-end" flexWrap="wrap">
          <Badge fontSize="10px" colorScheme={ruleSetsMeta?.persisted ? "green" : "gray"}>{ruleSetsMeta?.persisted ? t("singbox.editorSavedSource") : t("singbox.editorDefaultSource")}</Badge>
          <Button size="sm" variant="ghost" onClick={() => void loadRuleSets()}>{t("cancel")}</Button>
          <Button size="sm" variant="outline" isLoading={ruleSetsChecking} onClick={() => void checkRuleSets()}>{t("singbox.editorCheck")}</Button>
          <Button size="sm" variant="outline" isLoading={ruleSetsReloading} onClick={() => void reloadRuleSets()}>{t("singbox.ruleSetReload")}</Button>
          <Button size="sm" colorScheme="primary" isLoading={ruleSetsSaving} onClick={() => void saveRuleSets()}>{t("singbox.editorSave")}</Button>
        </HStack>
      </VStack>}
          </TabPanel>
        </TabPanels>
      </Tabs>
      {objectDialog && <SingBoxObjectDialog
        isOpen={Boolean(objectDialog)}
        title={t("singbox.objectEditor")}
        schema={singBoxSchema}
        section={objectDialog.section}
        initialValue={objectDialog.value}
        onClose={() => setObjectDialog(null)}
        onSave={saveObjectDialog}
      />}
      {inboundDialog && <SingBoxInboundDialog
        isOpen={Boolean(inboundDialog)}
        initialValue={inboundDialog.value}
        onClose={() => setInboundDialog(null)}
        onSave={saveInboundDialog}
      />}
    </VStack>
  );
};

export default SingBoxSettingsPage;
