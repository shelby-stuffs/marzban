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
import { Header } from "components/Header";
import { JsonEditor } from "components/JsonEditor";
import { Panel } from "components/Panel";
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


type RuleSetItem = {
  enabled: boolean;
  tag: string;
  type: "remote" | "local";
  format: "binary" | "source";
  url: string;
  path: string;
  download_detour: string;
  update_interval: string;
  outbound: string;
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

export const SingBoxSettingsPage = () => {
  const { t } = useTranslation();
  const toast = useToast();
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
      setAdvancedConfig(response.config);
      setAdvancedText(JSON.stringify(response.config, null, 2));
    } catch (error) {
      toast({ title: errorMessage(error), status: "error", position: "top" });
    } finally {
      setAdvancedLoading(false);
    }
  };

  useEffect(() => { void loadAdvanced(); }, []);

  const parseAdvanced = () => {
    const parsed = JSON.parse(advancedText);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error(t("singbox.editorObjectRequired"));
    }
    return parsed as Record<string, unknown>;
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
      setAdvancedConfig(response.config);
      setAdvancedText(JSON.stringify(response.config, null, 2));
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
    setAdvancedConfig(defaults);
    setAdvancedText(JSON.stringify(defaults, null, 2));
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

  const addRuleSet = () => setRuleSets((current) => ({
    ...current,
    items: [...current.items, {
      enabled: true,
      tag: `rule-set-${current.items.length + 1}`,
      type: "remote",
      format: "binary",
      url: "",
      path: "",
      download_detour: "direct",
      update_interval: "1d",
      outbound: "",
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
        <Box
          ref={logsRef}
          as="pre"
          minH="220px"
          maxH="420px"
          overflow="auto"
          m="0"
          p="4"
          bg="#05070a"
          border="1px solid"
          borderColor="terminal.border"
          borderRadius="3px"
          color="gray.300"
          fontFamily="mono"
          fontSize="xs"
          lineHeight="1.65"
          whiteSpace="pre-wrap"
          wordBreak="break-word"
        >
          {logsMeta?.logs.length ? logsMeta.logs.join("\n") : t("singbox.logsEmpty")}
        </Box>
        {logsMeta?.config_path && <Text mt="2" color="gray.500" fontFamily="mono" fontSize="xs">{t("singbox.configPath")}: {logsMeta.config_path}</Text>}
      </Panel>

      <Panel label={t("singbox.advancedEditor")}>
        <Alert status="warning" mb="4"><AlertIcon />{t("singbox.editorWarning")}</Alert>
        <HStack justify="space-between" mb="3" flexWrap="wrap" gap="2">
          <Text color="gray.500" fontFamily="mono" fontSize="xs">
            {t("singbox.editorAllowed")}: {(advancedMeta?.allowed_top_level_keys || ["log", "dns", "outbounds", "route", "experimental"]).join(", ")}
          </Text>
          <Badge colorScheme={advancedMeta?.persisted ? "green" : "gray"}>{advancedMeta?.persisted ? t("singbox.editorSavedSource") : t("singbox.editorDefaultSource")}</Badge>
        </HStack>
        {advancedLoading ? <Spinner /> : <JsonEditor json={advancedConfig} onChange={setAdvancedText} />}
        <HStack justify="flex-end" mt="4" flexWrap="wrap">
          <Button variant="ghost" onClick={resetAdvanced}>{t("singbox.editorReset")}</Button>
          <Button variant="outline" isLoading={advancedChecking} onClick={() => void checkAdvanced()}>{t("singbox.editorCheck")}</Button>
          <Button colorScheme="primary" isLoading={advancedSaving} onClick={() => void saveAdvanced()}>{t("singbox.editorSave")}</Button>
        </HStack>
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
            <Alert status="info" mb="4"><AlertIcon />{t("singbox.subscriptionFormatsHelp")}</Alert>
            <Panel label={t("singbox.subscription")}>
            <VStack align="stretch" spacing="4">
              <FormControl display="flex" justifyContent="space-between" alignItems="center">
                <Box><FormLabel mb="0">{t("singbox.subscriptionEnabled")}</FormLabel><FormHelperText>{t("singbox.subscriptionHelp")}</FormHelperText></Box>
                <Switch isChecked={form.subscription_enabled} onChange={(event) => update("subscription_enabled", event.target.checked)} />
              </FormControl>
              <Alert status="warning"><AlertIcon />{t("singbox.subscriptionTlsHint")}</Alert>
              <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
                <FormControl isRequired={form.subscription_enabled}><FormLabel>{t("singbox.subscriptionAddress")}</FormLabel><Input fontFamily="mono" placeholder="hy.example.com" value={form.subscription_address} onChange={(event) => update("subscription_address", event.target.value)} /><FormHelperText>{t("singbox.subscriptionAddressHelp")}</FormHelperText></FormControl>
                <FormControl><FormLabel>{t("singbox.subscriptionPort")}</FormLabel><Input type="number" placeholder={String(form.listen_port)} value={form.subscription_port ?? ""} onChange={(event) => update("subscription_port", event.target.value ? Number(event.target.value) : null)} /></FormControl>
                <FormControl><FormLabel>SNI</FormLabel><Input fontFamily="mono" placeholder="hy.example.com" value={form.subscription_sni} onChange={(event) => update("subscription_sni", event.target.value)} /></FormControl>
                <FormControl display="flex" justifyContent="space-between" alignItems="center" pt="7"><FormLabel mb="0">{t("singbox.subscriptionInsecure")}</FormLabel><Switch isChecked={form.subscription_insecure} onChange={(event) => update("subscription_insecure", event.target.checked)} /></FormControl>
              </Grid>
              <FormControl isRequired={form.subscription_enabled}><FormLabel>{t("singbox.subscriptionRemark")}</FormLabel><Input value={form.subscription_remark} onChange={(event) => update("subscription_remark", event.target.value)} /><FormHelperText>{t("singbox.subscriptionRemarkHelp")}</FormHelperText></FormControl>
            </VStack>
          </Panel>
            <HStack justify="flex-end" position="sticky" bottom="0" bg="terminal.bg" py="3" borderTop="1px solid" borderColor="terminal.border">
              <Button variant="ghost" onClick={() => void load()}>{t("cancel")}</Button>
              <Button colorScheme="primary" isLoading={saving} onClick={() => void save()}>{t("hysteria.save")}</Button>
            </HStack>
          </TabPanel>
          <TabPanel px="0">
      {ruleSetsLoading ? <Spinner /> : <VStack align="stretch" spacing="4">
        <Panel label={t("singbox.ruleSetCache")}>
          <VStack align="stretch" spacing="4">
            <FormControl display="flex" justifyContent="space-between" alignItems="center">
              <Box><FormLabel mb="0">{t("singbox.ruleSetCacheEnabled")}</FormLabel><FormHelperText>{t("singbox.ruleSetCacheHelp")}</FormHelperText></Box>
              <Switch isChecked={ruleSets.cache_enabled} onChange={(event) => setRuleSets((current) => ({ ...current, cache_enabled: event.target.checked }))} />
            </FormControl>
            <FormControl isRequired={ruleSets.cache_enabled}><FormLabel>{t("singbox.ruleSetCachePath")}</FormLabel><Input fontFamily="mono" value={ruleSets.cache_path} onChange={(event) => setRuleSets((current) => ({ ...current, cache_path: event.target.value }))} /></FormControl>
          </VStack>
        </Panel>

        <HStack justify="space-between" flexWrap="wrap">
          <Text color="gray.500" fontFamily="mono" fontSize="sm">{t("singbox.ruleSetsHelp")}</Text>
          <Button variant="outline" onClick={addRuleSet}>{t("singbox.ruleSetAdd")}</Button>
        </HStack>

        {ruleSets.items.length === 0 && <Alert status="info"><AlertIcon />{t("singbox.ruleSetsEmpty")}</Alert>}
        {ruleSets.items.map((item, index) => (
          <Panel key={index} label={`${t("singbox.ruleSet")} ${index + 1}: ${item.tag || "—"}`}>
            <VStack align="stretch" spacing="4">
              <HStack justify="space-between">
                <Checkbox isChecked={item.enabled} onChange={(event) => updateRuleSet(index, "enabled", event.target.checked)}>{t("singbox.ruleSetEnabled")}</Checkbox>
                <Button size="sm" variant="ghost" colorScheme="red" onClick={() => removeRuleSet(index)}>{t("delete")}</Button>
              </HStack>
              <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", xl: "repeat(4, 1fr)" }} gap="4">
                <FormControl isRequired><FormLabel>{t("singbox.ruleSetTag")}</FormLabel><Input fontFamily="mono" value={item.tag} onChange={(event) => updateRuleSet(index, "tag", event.target.value)} /></FormControl>
                <FormControl><FormLabel>{t("singbox.ruleSetType")}</FormLabel><Select value={item.type} onChange={(event) => updateRuleSet(index, "type", event.target.value as "remote" | "local")}><option value="remote">remote</option><option value="local">local</option></Select></FormControl>
                <FormControl><FormLabel>{t("singbox.ruleSetFormat")}</FormLabel><Select value={item.format} onChange={(event) => updateRuleSet(index, "format", event.target.value as "binary" | "source")}><option value="binary">binary (.srs)</option><option value="source">source (JSON)</option></Select></FormControl>
                <FormControl><FormLabel>{t("singbox.ruleSetOutbound")}</FormLabel><Input fontFamily="mono" placeholder="direct" value={item.outbound} onChange={(event) => updateRuleSet(index, "outbound", event.target.value)} /><FormHelperText>{t("singbox.ruleSetOutboundHelp")}</FormHelperText></FormControl>
              </Grid>
              {item.type === "remote" ? <Grid templateColumns={{ base: "1fr", lg: "2fr 1fr 1fr" }} gap="4">
                <FormControl isRequired={item.enabled}><FormLabel>URL</FormLabel><Input fontFamily="mono" placeholder="https://example.com/rules.srs" value={item.url} onChange={(event) => updateRuleSet(index, "url", event.target.value)} /></FormControl>
                <FormControl><FormLabel>{t("singbox.ruleSetDetour")}</FormLabel><Input fontFamily="mono" value={item.download_detour} onChange={(event) => updateRuleSet(index, "download_detour", event.target.value)} /></FormControl>
                <FormControl><FormLabel>{t("singbox.ruleSetInterval")}</FormLabel><Input fontFamily="mono" placeholder="1d" value={item.update_interval} onChange={(event) => updateRuleSet(index, "update_interval", event.target.value)} /></FormControl>
              </Grid> : <FormControl isRequired={item.enabled}><FormLabel>{t("singbox.ruleSetPath")}</FormLabel><Input fontFamily="mono" placeholder="/var/lib/marzban/rules/local.srs" value={item.path} onChange={(event) => updateRuleSet(index, "path", event.target.value)} /></FormControl>}
            </VStack>
          </Panel>
        ))}

        <Alert status="warning"><AlertIcon />{t("singbox.ruleSetReloadWarning")}</Alert>
        <HStack justify="flex-end" flexWrap="wrap">
          <Badge colorScheme={ruleSetsMeta?.persisted ? "green" : "gray"}>{ruleSetsMeta?.persisted ? t("singbox.editorSavedSource") : t("singbox.editorDefaultSource")}</Badge>
          <Button variant="ghost" onClick={() => void loadRuleSets()}>{t("cancel")}</Button>
          <Button variant="outline" isLoading={ruleSetsChecking} onClick={() => void checkRuleSets()}>{t("singbox.editorCheck")}</Button>
          <Button variant="outline" isLoading={ruleSetsReloading} onClick={() => void reloadRuleSets()}>{t("singbox.ruleSetReload")}</Button>
          <Button colorScheme="primary" isLoading={ruleSetsSaving} onClick={() => void saveRuleSets()}>{t("singbox.editorSave")}</Button>
        </HStack>
      </VStack>}
          </TabPanel>
        </TabPanels>
      </Tabs>
    </VStack>
  );
};

export default SingBoxSettingsPage;
