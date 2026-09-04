import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormLabel,
  Grid,
  HStack,
  Input,
  Select,
  Spinner,
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
import { useEffect, useMemo, useState } from "react";
import { fetch } from "service/http";

type Settings = Record<string, any>;
type Host = Record<string, any> & { remark: string; address: string; xhttp_settings?: Settings | null };
type Hosts = Record<string, Host[]>;
type RuntimeInbound = { tag: string; protocol: string; listen?: string; port?: number; settings: Settings };

const rangeFields = [
  ["scMaxEachPostBytes", "Max POST bytes"],
  ["scMinPostsIntervalMs", "Min POST interval (ms)"],
  ["xPaddingBytes", "Padding bytes"],
  ["sessionIDLength", "Session ID length"],
  ["uplinkChunkSize", "Uplink chunk size"],
] as const;
const textFields = [
  ["xPaddingKey", "Padding key"], ["xPaddingHeader", "Padding header"],
  ["xPaddingPlacement", "Padding placement"], ["xPaddingMethod", "Padding method"],
  ["uplinkHTTPMethod", "Uplink HTTP method"], ["sessionIDPlacement", "Session ID placement"],
  ["sessionIDKey", "Session ID key"], ["sessionIDTable", "Session ID table"],
  ["seqPlacement", "Sequence placement"], ["seqKey", "Sequence key"],
  ["uplinkDataPlacement", "Uplink data placement"], ["uplinkDataKey", "Uplink data key"],
] as const;
const numberFields = [
  ["scMaxBufferedPosts", "Max buffered POSTs"],
  ["scStreamUpServerSecs", "Stream-up server seconds"],
  ["serverMaxHeaderBytes", "Max server header bytes"],
  ["keepAlivePeriod", "Keepalive period"],
] as const;
const boolFields = [
  ["noGRPCHeader", "Disable gRPC header"],
  ["noSSEHeader", "Disable SSE header"],
  ["xPaddingObfsMode", "Padding obfuscation"],
] as const;

const clean = (settings: Settings) => Object.fromEntries(
  Object.entries(settings).filter(([, value]) => value !== "" && value !== undefined && value !== null)
);

const JsonField = ({ label, value, onChange }: { label: string; value: unknown; onChange: (value: unknown) => void }) => {
  const [text, setText] = useState(value ? JSON.stringify(value, null, 2) : "");
  useEffect(() => setText(value ? JSON.stringify(value, null, 2) : ""), [value]);
  return (
    <FormControl>
      <FormLabel>{label}</FormLabel>
      <Textarea
        minH="170px" fontFamily="mono" value={text}
        onChange={(event) => setText(event.target.value)}
        onBlur={() => {
          if (!text.trim()) return onChange(undefined);
          try { onChange(JSON.parse(text)); } catch { /* validated before save */ }
        }}
      />
    </FormControl>
  );
};

const SettingsEditor = ({ settings, onChange, runtime = false }: {
  settings: Settings; onChange: (settings: Settings) => void; runtime?: boolean;
}) => {
  const update = (key: string, value: unknown) => onChange({ ...settings, [key]: value });
  return (
    <VStack align="stretch" spacing="5">
      <Box borderWidth="1px" borderRadius="lg" p="4">
        <Text fontWeight="semibold" mb="4">Transport</Text>
        <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
          {runtime && <FormControl><FormLabel>Path</FormLabel><Input value={settings.path || ""} onChange={(e) => update("path", e.target.value)} /></FormControl>}
          {runtime && <FormControl><FormLabel>Host</FormLabel><Input value={Array.isArray(settings.host) ? settings.host.join(",") : settings.host || ""} onChange={(e) => update("host", e.target.value)} /></FormControl>}
          <FormControl><FormLabel>Mode</FormLabel><Select value={settings.mode || ""} onChange={(e) => update("mode", e.target.value)}>
            <option value="">{runtime ? "Xray default" : "Inherit from inbound"}</option>
            <option value="auto">auto</option><option value="packet-up">packet-up</option>
            <option value="stream-up">stream-up</option><option value="stream-one">stream-one</option>
          </Select></FormControl>
          {numberFields.map(([key, label]) => <FormControl key={key}><FormLabel>{label}</FormLabel><Input type="number" value={settings[key] ?? ""} onChange={(e) => update(key, e.target.value === "" ? "" : Number(e.target.value))} /></FormControl>)}
          {rangeFields.map(([key, label]) => <FormControl key={key}><FormLabel>{label} (number or min-max)</FormLabel><Input value={settings[key] ?? ""} onChange={(e) => update(key, e.target.value)} /></FormControl>)}
          {textFields.map(([key, label]) => <FormControl key={key}><FormLabel>{label}</FormLabel><Input value={settings[key] ?? ""} onChange={(e) => update(key, e.target.value)} /></FormControl>)}
        </Grid>
        <HStack mt="4" spacing="6" flexWrap="wrap">
          {boolFields.map(([key, label]) => runtime ? (
            <Checkbox key={key} isChecked={settings[key] === true} onChange={(e) => update(key, e.target.checked)}>{label}</Checkbox>
          ) : (
            <FormControl key={key} maxW="220px"><FormLabel>{label}</FormLabel><Select value={settings[key] === undefined ? "inherit" : String(settings[key])} onChange={(e) => update(key, e.target.value === "inherit" ? undefined : e.target.value === "true")}>
              <option value="inherit">Inherit</option><option value="true">Enabled</option><option value="false">Disabled</option>
            </Select></FormControl>
          ))}
        </HStack>
      </Box>
      <Box borderWidth="1px" borderRadius="lg" p="4">
        <Text fontWeight="semibold" mb="4">Structured settings</Text>
        <Grid templateColumns={{ base: "1fr", lg: "repeat(3, 1fr)" }} gap="4">
          <JsonField label="HTTP headers (JSON)" value={settings.headers} onChange={(value) => update("headers", value)} />
          <JsonField label="XMUX (JSON)" value={settings.xmux} onChange={(value) => update("xmux", value)} />
          <JsonField label="Download settings (JSON)" value={settings.downloadSettings} onChange={(value) => update("downloadSettings", value)} />
        </Grid>
      </Box>
    </VStack>
  );
};

export const XHTTPSettingsPage = () => {
  const toast = useToast();
  const [runtimeInbounds, setRuntimeInbounds] = useState<RuntimeInbound[]>([]);
  const [hosts, setHosts] = useState<Hosts>({});
  const [tag, setTag] = useState("");
  const [hostIndex, setHostIndex] = useState(0);
  const [runtimeSettings, setRuntimeSettings] = useState<Settings>({});
  const [overrideSettings, setOverrideSettings] = useState<Settings>({});
  const [loading, setLoading] = useState(true);
  const [savingRuntime, setSavingRuntime] = useState(false);
  const [savingOverrides, setSavingOverrides] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [inbounds, hostData] = await Promise.all([
        fetch<RuntimeInbound[]>("/core/xhttp-inbounds"), fetch<Hosts>("/hosts"),
      ]);
      setRuntimeInbounds(inbounds); setHosts(hostData);
      setTag((current) => current || inbounds[0]?.tag || "");
    } catch (error: any) {
      toast({ title: error?.message || "Failed to load XHTTP settings", status: "error", position: "top" });
    } finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const runtimeInbound = runtimeInbounds.find((item) => item.tag === tag);
  const tagHosts = useMemo(() => hosts[tag] || [], [hosts, tag]);
  const selectedHost = tagHosts[hostIndex];
  useEffect(() => setRuntimeSettings(runtimeInbound?.settings || {}), [runtimeInbound]);
  useEffect(() => setOverrideSettings(selectedHost?.xhttp_settings || {}), [selectedHost]);

  const saveRuntime = async () => {
    if (!tag) return;
    setSavingRuntime(true);
    try {
      const result = await fetch<RuntimeInbound>(`/core/xhttp-inbounds/${encodeURIComponent(tag)}`, { method: "PUT", body: clean(runtimeSettings) });
      setRuntimeInbounds((items) => items.map((item) => item.tag === tag ? result : item));
      toast({ title: "Inbound saved and Xray restarted", status: "success", position: "top" });
    } catch (error: any) { toast({ title: error?.message || "Invalid XHTTP inbound", status: "error", position: "top" }); }
    finally { setSavingRuntime(false); }
  };

  const saveOverrides = async () => {
    if (!selectedHost) return;
    setSavingOverrides(true);
    try {
      const nextHosts = { ...hosts, [tag]: tagHosts.map((host, index) => index === hostIndex ? { ...host, xhttp_settings: clean(overrideSettings) } : host) };
      await fetch("/hosts", { method: "PUT", body: nextHosts });
      setHosts(nextHosts);
      toast({ title: "Subscription overrides saved", status: "success", position: "top" });
    } catch (error: any) { toast({ title: error?.message || "Invalid subscription overrides", status: "error", position: "top" }); }
    finally { setSavingOverrides(false); }
  };

  return <Box><Header title="XHTTP" />{loading ? <Spinner /> : runtimeInbounds.length === 0 ? <Text>No XHTTP inbounds found.</Text> : <VStack align="stretch" spacing="5">
    <FormControl maxW="520px"><FormLabel>Inbound</FormLabel><Select value={tag} onChange={(e) => { setTag(e.target.value); setHostIndex(0); }}>
      {runtimeInbounds.map((item) => <option key={item.tag} value={item.tag}>{item.tag} — {item.protocol} — {item.port || item.listen}</option>)}
    </Select></FormControl>
    <Tabs colorScheme="primary" isLazy>
      <TabList><Tab>Runtime inbound</Tab><Tab>Subscription overrides</Tab></TabList>
      <TabPanels>
        <TabPanel px="0"><Alert status="warning" mb="4"><AlertIcon />Saving validates the full config, writes XRAY_JSON and restarts Xray and connected nodes.</Alert>
          <SettingsEditor settings={runtimeSettings} onChange={setRuntimeSettings} runtime />
          <HStack justify="flex-end" mt="4"><Button colorScheme="primary" isLoading={savingRuntime} onClick={() => void saveRuntime()}>Save inbound and restart Xray</Button></HStack>
        </TabPanel>
        <TabPanel px="0"><Alert status="info" mb="4"><AlertIcon />Overrides affect generated client subscriptions only and do not restart Xray.</Alert>
          <FormControl maxW="520px" mb="4"><FormLabel>Subscription host</FormLabel><Select value={hostIndex} onChange={(e) => setHostIndex(Number(e.target.value))}>
            {tagHosts.map((host, index) => <option key={`${host.remark}-${index}`} value={index}>{host.remark} — {host.address}</option>)}
          </Select></FormControl>
          {selectedHost ? <><SettingsEditor settings={overrideSettings} onChange={setOverrideSettings} />
            <HStack justify="flex-end" mt="4"><Button variant="ghost" onClick={() => setOverrideSettings({})}>Use inbound defaults</Button><Button colorScheme="primary" isLoading={savingOverrides} onClick={() => void saveOverrides()}>Save subscription overrides</Button></HStack></> : <Text>No subscription hosts for this inbound.</Text>}
        </TabPanel>
      </TabPanels>
    </Tabs>
  </VStack>}</Box>;
};
