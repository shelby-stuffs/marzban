import {
  Badge,
  Box,
  Button,
  Divider,
  FormControl,
  FormLabel,
  Grid,
  HStack,
  Heading,
  Select,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  Textarea,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { Header } from "components/Header";
import { Panel } from "components/Panel";
import { Input } from "components/Input";
import { FC, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetcher } from "service/http";

interface WireGuardPeerConfig {
  publicKey: string;
  endpoint: string;
  allowedIPs: string[];
  keepAlive?: number;
  reserved?: number[];
}

interface WireGuardOutbound {
  tag: string;
  protocol: "wireguard";
  settings: {
    secretKey: string;
    address: string[];
    peers: WireGuardPeerConfig[];
    mtu?: number;
    reserved?: number[];
    domainStrategy?: string;
  };
}

const emptyForm = {
  tag: "wireguard-out",
  secretKey: "",
  address: "",
  peerPublicKey: "",
  endpoint: "",
  allowedIPs: "0.0.0.0/0, ::/0",
  keepAlive: "25",
  mtu: "1420",
  reserved: "",
  domainStrategy: "ForceIP",
  inboundTags: "",
};

const splitList = (value: string) =>
  value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);

const parseReserved = (value: string) => {
  if (!value.trim()) return undefined;
  return splitList(value).map(Number);
};

const errorMessage = (error: any) =>
  error?.response?._data?.detail || error?.data?.detail || error?.message || "Request failed";

export const WireGuardOutbounds: FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(emptyForm);
  const [editingTag, setEditingTag] = useState<string | null>(null);

  const outboundsQuery = useQuery<WireGuardOutbound[]>(
    ["xray-wireguard-outbounds"],
    () => fetcher("/core/wireguard-outbounds")
  );

  const selectedOutbound = useMemo(
    () => outboundsQuery.data?.find((item) => item.tag === editingTag),
    [outboundsQuery.data, editingTag]
  );

  const saveMutation = useMutation(
    () =>
      fetcher(`/core/wireguard-outbounds/${encodeURIComponent(form.tag)}`, {
        method: "PUT",
        body: {
          secret_key: form.secretKey,
          address: splitList(form.address),
          peers: [
            {
              public_key: form.peerPublicKey,
              endpoint: form.endpoint.trim(),
              allowed_ips: splitList(form.allowedIPs),
              keep_alive: Number(form.keepAlive || 0),
              reserved: parseReserved(form.reserved),
            },
          ],
          mtu: Number(form.mtu || 1420),
          reserved: parseReserved(form.reserved),
          domain_strategy: form.domainStrategy,
          route_inbound_tags: splitList(form.inboundTags),
        },
      }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["xray-wireguard-outbounds"]);
        setEditingTag(form.tag);
        toast({ title: "WireGuard outbound saved and Xray restarted", status: "success", position: "top" });
      },
      onError: (error) => {
        toast({ title: errorMessage(error), status: "error", position: "top", isClosable: true });
      },
    }
  );

  const deleteMutation = useMutation(
    (tag: string) =>
      fetcher(`/core/wireguard-outbounds/${encodeURIComponent(tag)}`, { method: "DELETE" }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["xray-wireguard-outbounds"]);
        setEditingTag(null);
        setForm(emptyForm);
        toast({ title: "WireGuard outbound deleted", status: "success", position: "top" });
      },
      onError: (error) => {
        toast({ title: errorMessage(error), status: "error", position: "top", isClosable: true });
      },
    }
  );

  const updateField = (name: keyof typeof emptyForm, value: string) =>
    setForm((current) => ({ ...current, [name]: value }));

  const editOutbound = (outbound: WireGuardOutbound) => {
    const peer = outbound.settings.peers[0];
    setEditingTag(outbound.tag);
    setForm({
      tag: outbound.tag,
      secretKey: outbound.settings.secretKey || "",
      address: (outbound.settings.address || []).join(", "),
      peerPublicKey: peer?.publicKey || "",
      endpoint: peer?.endpoint || "",
      allowedIPs: (peer?.allowedIPs || []).join(", "),
      keepAlive: String(peer?.keepAlive || 0),
      mtu: String(outbound.settings.mtu || 1420),
      reserved: (peer?.reserved || outbound.settings.reserved || []).join(", "),
      domainStrategy: outbound.settings.domainStrategy || "ForceIP",
      inboundTags: "",
    });
  };

  const resetForm = () => {
    setEditingTag(null);
    setForm(emptyForm);
  };

  return (
    <VStack align="stretch" spacing="4" w="full">
      <Header title="WireGuard outbounds" />
      <SimpleGrid columns={{ base: 1, xl: 2 }} spacing="4" alignItems="start">
        <Panel label="configured outbounds">
          <HStack justify="space-between" mb="4" flexWrap="wrap" gap="2">
            <Text color="terminal.dim" fontSize="sm">Xray WireGuard</Text>
            <Button size="sm" onClick={resetForm}>New outbound</Button>
          </HStack>
          {outboundsQuery.isLoading && <Spinner />}
          {outboundsQuery.isError && <Text color="red.400">Unable to load WireGuard outbounds.</Text>}
          <Stack spacing="3">
            {outboundsQuery.data?.map((outbound) => (
              <Box
                key={outbound.tag}
                borderWidth="1px"
                borderColor={editingTag === outbound.tag ? "primary.400" : "light-border"}
                borderRadius="4px"
                bg="terminal.overlay"
                p="3"
              >
                <HStack justify="space-between" align="start" flexWrap="wrap" gap="2">
                  <Box>
                    <HStack>
                      <Text fontWeight="semibold">{outbound.tag}</Text>
                      <Badge colorScheme="blue">Xray outbound</Badge>
                    </HStack>
                    <Text fontSize="sm" color="gray.500">
                      {outbound.settings.peers.length} peer(s) · {outbound.settings.address.join(", ")}
                    </Text>
                  </Box>
                  <HStack>
                    <Button size="xs" onClick={() => editOutbound(outbound)}>Edit</Button>
                    <Button
                      size="xs"
                      colorScheme="red"
                      variant="outline"
                      isLoading={deleteMutation.isLoading && editingTag === outbound.tag}
                      onClick={() => {
                        setEditingTag(outbound.tag);
                        if (window.confirm(`Delete outbound ${outbound.tag}?`)) deleteMutation.mutate(outbound.tag);
                      }}
                    >
                      Delete
                    </Button>
                  </HStack>
                </HStack>
              </Box>
            ))}
            {!outboundsQuery.isLoading && !outboundsQuery.data?.length && (
              <Text color="gray.500">No WireGuard outbounds configured.</Text>
            )}
          </Stack>
        </Panel>

        <Panel label={selectedOutbound ? "edit outbound" : "new outbound"}>
          <Heading size="md" mb="1">{selectedOutbound ? `Edit ${selectedOutbound.tag}` : "Add outbound"}</Heading>
          <Text fontSize="sm" color="gray.500" mb="4">
            Saving validates the complete configuration with Xray-core and restarts connected cores.
          </Text>
          <Stack spacing="4">
            <Input label="Outbound tag" value={form.tag} onChange={(event) => updateField("tag", event.target.value)} disabled={!!editingTag} />
            <FormControl>
              <FormLabel>Secret key</FormLabel>
              <Textarea value={form.secretKey} onChange={(event) => updateField("secretKey", event.target.value.trim())} rows={2} fontFamily="mono" />
            </FormControl>
            <Input label="Local addresses" placeholder="172.16.0.2/32, 2606:4700::2/128" value={form.address} onChange={(event) => updateField("address", event.target.value)} />
            <Divider />
            <Heading size="sm">Peer</Heading>
            <FormControl>
              <FormLabel>Public key</FormLabel>
              <Textarea value={form.peerPublicKey} onChange={(event) => updateField("peerPublicKey", event.target.value.trim())} rows={2} fontFamily="mono" />
            </FormControl>
            <Input label="Endpoint" placeholder="vpn.example.com:51820" value={form.endpoint} onChange={(event) => updateField("endpoint", event.target.value)} />
            <Input label="Allowed IPs" value={form.allowedIPs} onChange={(event) => updateField("allowedIPs", event.target.value)} />
            <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
              <Input label="Keepalive" type="number" value={form.keepAlive} onChange={(value) => updateField("keepAlive", String(value))} />
              <Input label="MTU" type="number" value={form.mtu} onChange={(value) => updateField("mtu", String(value))} />
            </Grid>
            <Input label="Reserved bytes" placeholder="0, 0, 0" value={form.reserved} onChange={(event) => updateField("reserved", event.target.value)} />
            <FormControl>
              <FormLabel>Domain strategy</FormLabel>
              <Select value={form.domainStrategy} onChange={(event) => updateField("domainStrategy", event.target.value)}>
                {['ForceIP', 'ForceIPv4', 'ForceIPv6', 'UseIP', 'UseIPv4', 'UseIPv6', 'AsIs'].map((value) => <option key={value}>{value}</option>)}
              </Select>
            </FormControl>
            <Input label="Route inbound tags" placeholder="VLESS_TCP, VLESS_REALITY" value={form.inboundTags} onChange={(event) => updateField("inboundTags", event.target.value)} />
            <HStack justify="flex-end">
              <Button variant="ghost" onClick={resetForm}>Reset</Button>
              <Button colorScheme="primary" isLoading={saveMutation.isLoading} onClick={() => saveMutation.mutate()}>
                Save and restart Xray
              </Button>
            </HStack>
          </Stack>
        </Panel>
      </SimpleGrid>
    </VStack>
  );
};

export default WireGuardOutbounds;
