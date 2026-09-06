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
  Text,
  Textarea,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { Header } from "components/Header";
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
};

type SettingsResponse = {
  settings: HysteriaSettings;
  source?: string;
  persisted: boolean;
  feature_enabled: boolean;
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
        <Button variant="outline" isLoading={generating} onClick={() => void generate()}>
          {t("hysteria.autofill")}
        </Button>
      </HStack>

      {!meta?.feature_enabled && (
        <Alert status="warning"><AlertIcon />{t("hysteria.enableHint")}</Alert>
      )}

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
    </VStack>
  );
};

export default SingBoxSettingsPage;
