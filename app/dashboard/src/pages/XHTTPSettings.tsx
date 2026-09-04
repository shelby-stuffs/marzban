import {
  Box,
  Button,
  Checkbox,
  FormControl,
  FormLabel,
  Grid,
  HStack,
  Select,
  Spinner,
  Text,
  Textarea,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { Header } from "components/Header";
import { Input } from "components/Input";
import { useEffect, useMemo, useState } from "react";
import { fetch } from "service/http";

type XHTTPSettings = Record<string, any>;
type Host = Record<string, any> & {
  remark: string;
  address: string;
  xhttp_settings?: XHTTPSettings | null;
};
type Hosts = Record<string, Host[]>;
type Inbound = { tag: string; network: string };

const textFields = [
  ["scMaxEachPostBytes", "Max POST bytes"],
  ["scMinPostsIntervalMs", "Min POST interval (ms)"],
  ["xPaddingBytes", "Padding bytes"],
  ["xPaddingKey", "Padding key"],
  ["xPaddingHeader", "Padding header"],
  ["xPaddingPlacement", "Padding placement"],
  ["xPaddingMethod", "Padding method"],
  ["uplinkHTTPMethod", "Uplink HTTP method"],
  ["sessionIDPlacement", "Session ID placement"],
  ["sessionIDKey", "Session ID key"],
  ["sessionIDTable", "Session ID table"],
  ["sessionIDLength", "Session ID length"],
  ["seqPlacement", "Sequence placement"],
  ["seqKey", "Sequence key"],
  ["uplinkDataPlacement", "Uplink data placement"],
  ["uplinkDataKey", "Uplink data key"],
  ["uplinkChunkSize", "Uplink chunk size"],
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

const jsonText = (value: unknown) =>
  value ? JSON.stringify(value, null, 2) : "";

export const XHTTPSettingsPage = () => {
  const toast = useToast();
  const [hosts, setHosts] = useState<Hosts>({});
  const [tags, setTags] = useState<string[]>([]);
  const [tag, setTag] = useState("");
  const [hostIndex, setHostIndex] = useState(0);
  const [settings, setSettings] = useState<XHTTPSettings>({});
  const [headers, setHeaders] = useState("");
  const [xmux, setXmux] = useState("");
  const [downloadSettings, setDownloadSettings] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [hostData, inboundData] = await Promise.all([
        fetch<Hosts>("/hosts"),
        fetch<Record<string, Inbound[]>>("/inbounds"),
      ]);
      const xhttpTags = Object.values(inboundData)
        .flat()
        .filter((inbound) => ["xhttp", "splithttp"].includes(inbound.network))
        .map((inbound) => inbound.tag);
      setHosts(hostData);
      setTags(xhttpTags);
      setTag((current) => current || xhttpTags[0] || "");
    } catch (error: any) {
      toast({ title: error?.message || "Failed to load XHTTP settings", status: "error", position: "top" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const tagHosts = useMemo(() => hosts[tag] || [], [hosts, tag]);
  const selectedHost = tagHosts[hostIndex];

  useEffect(() => {
    const next = selectedHost?.xhttp_settings || {};
    setSettings(next);
    setHeaders(jsonText(next.headers));
    setXmux(jsonText(next.xmux));
    setDownloadSettings(jsonText(next.downloadSettings));
  }, [selectedHost]);

  const update = (key: string, value: unknown) =>
    setSettings((current) => ({ ...current, [key]: value }));

  const parseJson = (label: string, value: string) => {
    if (!value.trim()) return undefined;
    try {
      return JSON.parse(value);
    } catch {
      throw new Error(`${label} must be valid JSON`);
    }
  };

  const save = async () => {
    if (!selectedHost) return;
    setSaving(true);
    try {
      const nextSettings = {
        ...settings,
        headers: parseJson("Headers", headers),
        xmux: parseJson("XMUX", xmux),
        downloadSettings: parseJson("Download settings", downloadSettings),
      };
      const cleanSettings = Object.fromEntries(
        Object.entries(nextSettings).filter(([, value]) => value !== "" && value !== undefined)
      );
      const nextHosts = {
        ...hosts,
        [tag]: tagHosts.map((host, index) =>
          index === hostIndex ? { ...host, xhttp_settings: cleanSettings } : host
        ),
      };
      await fetch("/hosts", { method: "PUT", body: nextHosts });
      setHosts(nextHosts);
      setSettings(cleanSettings);
      toast({ title: "XHTTP host settings saved", status: "success", position: "top" });
    } catch (error: any) {
      toast({ title: error?.message || "Failed to save XHTTP settings", status: "error", position: "top" });
    } finally {
      setSaving(false);
    }
  };

  const clear = () => {
    setSettings({});
    setHeaders("");
    setXmux("");
    setDownloadSettings("");
  };

  return (
    <Box>
      <Header title="XHTTP" />
      {loading ? (
        <Spinner />
      ) : tags.length === 0 ? (
        <Text>No XHTTP or legacy SplitHTTP inbounds found.</Text>
      ) : (
        <VStack align="stretch" spacing="5">
          <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
            <FormControl>
              <FormLabel>Inbound</FormLabel>
              <Select value={tag} onChange={(event) => { setTag(event.target.value); setHostIndex(0); }}>
                {tags.map((item) => <option key={item}>{item}</option>)}
              </Select>
            </FormControl>
            <FormControl>
              <FormLabel>Subscription host</FormLabel>
              <Select value={hostIndex} onChange={(event) => setHostIndex(Number(event.target.value))}>
                {tagHosts.map((host, index) => (
                  <option key={`${host.remark}-${index}`} value={index}>{host.remark} — {host.address}</option>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {selectedHost && (
            <>
              <Box borderWidth="1px" borderRadius="lg" p="4">
                <Text fontWeight="semibold" mb="4">Transport</Text>
                <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap="4">
                  <FormControl>
                    <FormLabel>Mode</FormLabel>
                    <Select value={settings.mode || ""} onChange={(event) => update("mode", event.target.value)}>
                      <option value="">Inbound default</option>
                      <option value="auto">auto</option>
                      <option value="packet-up">packet-up</option>
                      <option value="stream-up">stream-up</option>
                      <option value="stream-one">stream-one</option>
                    </Select>
                  </FormControl>
                  {numberFields.map(([key, label]) => (
                    <FormControl key={key}>
                      <FormLabel>{label}</FormLabel>
                      <Input type="number" value={settings[key] ?? ""} onChange={(event) => update(key, event.target.value === "" ? "" : Number(event.target.value))} />
                    </FormControl>
                  ))}
                  {textFields.map(([key, label]) => (
                    <FormControl key={key}>
                      <FormLabel>{label}</FormLabel>
                      <Input value={settings[key] ?? ""} onChange={(event) => update(key, event.target.value)} />
                    </FormControl>
                  ))}
                </Grid>
                <HStack mt="4" spacing="6" flexWrap="wrap">
                  {boolFields.map(([key, label]) => (
                    <Checkbox key={key} isChecked={settings[key] === true} onChange={(event) => update(key, event.target.checked)}>{label}</Checkbox>
                  ))}
                </HStack>
              </Box>

              <Box borderWidth="1px" borderRadius="lg" p="4">
                <Text fontWeight="semibold" mb="4">Structured settings</Text>
                <Grid templateColumns={{ base: "1fr", lg: "repeat(3, 1fr)" }} gap="4">
                  <FormControl><FormLabel>HTTP headers (JSON)</FormLabel><Textarea minH="180px" fontFamily="mono" value={headers} onChange={(event) => setHeaders(event.target.value)} /></FormControl>
                  <FormControl><FormLabel>XMUX (JSON)</FormLabel><Textarea minH="180px" fontFamily="mono" value={xmux} onChange={(event) => setXmux(event.target.value)} /></FormControl>
                  <FormControl><FormLabel>Download settings (JSON)</FormLabel><Textarea minH="180px" fontFamily="mono" value={downloadSettings} onChange={(event) => setDownloadSettings(event.target.value)} /></FormControl>
                </Grid>
              </Box>

              <HStack justify="flex-end">
                <Button variant="ghost" onClick={clear}>Use inbound defaults</Button>
                <Button colorScheme="primary" isLoading={saving} onClick={() => void save()}>Save XHTTP settings</Button>
              </HStack>
            </>
          )}
        </VStack>
      )}
    </Box>
  );
};
