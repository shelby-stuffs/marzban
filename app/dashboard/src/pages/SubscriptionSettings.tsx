import {
  Alert,
  AlertIcon,
  Badge,
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
  Table,
  Tabs,
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

type Rule = {
  id: number;
  name: string;
  pattern: string;
  config_format: string;
  as_base64: boolean;
  reverse: boolean;
  priority: number;
  ignore_case: boolean;
  min_version?: string | null;
  max_version?: string | null;
  is_disabled: boolean;
};

type RulesResponse = { rules: Rule[]; formats: string[] };

type Preview = {
  user_agent: string;
  rule: string;
  config_format: string;
  as_base64: boolean;
  reverse: boolean;
  media_type: string;
  source: string;
};

type CacheState = { entries: number; ttl: number; etag: boolean };

type Token = {
  id: number;
  name?: string | null;
  token: string;
  url: string;
  created_at: string;
  expires_at?: string | null;
  revoked_at?: string | null;
  last_used_at?: string | null;
  last_user_agent?: string | null;
  is_active: boolean;
};

type RuleDraft = Omit<Rule, "id"> & { id?: number };

const emptyDraft: RuleDraft = {
  name: "",
  pattern: "",
  config_format: "v2ray",
  as_base64: false,
  reverse: false,
  priority: 100,
  ignore_case: false,
  min_version: "",
  max_version: "",
  is_disabled: false,
};

const FALLBACK_FORMATS = [
  "v2ray",
  "v2ray-json",
  "clash",
  "clash-meta",
  "sing-box",
  "outline",
  "hysteria2",
  "happ",
];

const when = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : "—";

const errorMessage = (error: any, fallback: string) =>
  error?.response?._data?.detail || error?.message || fallback;

const RulesSection: FC = () => {
  const toast = useToast();
  const [rules, setRules] = useState<Rule[]>([]);
  const [formats, setFormats] = useState<string[]>(FALLBACK_FORMATS);
  const [draft, setDraft] = useState<RuleDraft>(emptyDraft);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [userAgent, setUserAgent] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [cacheState, setCacheState] = useState<CacheState | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetch<RulesResponse>("/subscription/rules");
      setRules(data.rules);
      if (data.formats?.length) setFormats(data.formats);
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Failed to load subscription rules"),
        status: "error",
        position: "top",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadCache = async () => {
    try {
      setCacheState(await fetch<CacheState>("/subscription/cache"));
    } catch {
      setCacheState(null);
    }
  };

  useEffect(() => {
    void load();
    void loadCache();
  }, []);

  const update = (values: Partial<RuleDraft>) =>
    setDraft((current) => ({ ...current, ...values }));

  const save = async () => {
    setSaving(true);
    const body = {
      ...draft,
      min_version: draft.min_version || null,
      max_version: draft.max_version || null,
    };
    delete (body as any).id;
    try {
      if (draft.id) {
        await fetch(`/subscription/rules/${draft.id}`, { method: "PUT", body });
      } else {
        await fetch("/subscription/rules", { method: "POST", body });
      }
      toast({ title: "Rule saved", status: "success", position: "top" });
      setDraft(emptyDraft);
      await load();
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Invalid rule"),
        status: "error",
        position: "top",
      });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (rule: Rule) => {
    try {
      await fetch(`/subscription/rules/${rule.id}`, { method: "DELETE" });
      if (draft.id === rule.id) setDraft(emptyDraft);
      await load();
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Failed to delete rule"),
        status: "error",
        position: "top",
      });
    }
  };

  const seed = async () => {
    try {
      await fetch("/subscription/rules/seed", { method: "POST" });
      toast({ title: "Built-in rules copied", status: "success", position: "top" });
      await load();
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Failed to copy built-in rules"),
        status: "error",
        position: "top",
      });
    }
  };

  const runPreview = async () => {
    try {
      setPreview(
        await fetch<Preview>(
          `/subscription/preview?user_agent=${encodeURIComponent(userAgent)}`
        )
      );
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Preview failed"),
        status: "error",
        position: "top",
      });
    }
  };

  const flushCache = async () => {
    try {
      await fetch("/subscription/cache", { method: "DELETE" });
      await loadCache();
      toast({ title: "Cache flushed", status: "success", position: "top" });
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Failed to flush cache"),
        status: "error",
        position: "top",
      });
    }
  };

  return (
    <VStack align="stretch" spacing="4">
      <Alert status="info" fontSize="sm">
        <AlertIcon />
        Пока таблица пуста, работают встроенные правила. Правила проверяются по
        возрастанию приоритета, первое совпадение выигрывает.
      </Alert>

      <Panel label="client rules">
        {loading ? (
          <Spinner />
        ) : (
          <Box overflowX="auto">
            <Table size="sm" fontFamily="mono">
              <Thead>
                <Tr>
                  <Th>prio</Th>
                  <Th>name</Th>
                  <Th>pattern</Th>
                  <Th>format</Th>
                  <Th>flags</Th>
                  <Th />
                </Tr>
              </Thead>
              <Tbody>
                {rules.length === 0 && (
                  <Tr>
                    <Td colSpan={6}>
                      <Text color="terminal.dim">
                        Нет правил в БД — используются встроенные.
                      </Text>
                    </Td>
                  </Tr>
                )}
                {rules.map((rule) => (
                  <Tr key={rule.id} opacity={rule.is_disabled ? 0.5 : 1}>
                    <Td>{rule.priority}</Td>
                    <Td>{rule.name}</Td>
                    <Td maxW="260px" isTruncated title={rule.pattern}>
                      {rule.pattern}
                    </Td>
                    <Td>
                      <Badge colorScheme="primary">{rule.config_format}</Badge>
                    </Td>
                    <Td>
                      <HStack spacing="1" flexWrap="wrap">
                        {rule.as_base64 && <Badge>b64</Badge>}
                        {rule.reverse && <Badge>reverse</Badge>}
                        {rule.ignore_case && <Badge>icase</Badge>}
                        {rule.min_version && <Badge>≥{rule.min_version}</Badge>}
                        {rule.max_version && <Badge>≤{rule.max_version}</Badge>}
                        {rule.is_disabled && <Badge colorScheme="red">off</Badge>}
                      </HStack>
                    </Td>
                    <Td>
                      <HStack justify="flex-end" spacing="2">
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() =>
                            setDraft({
                              ...rule,
                              min_version: rule.min_version || "",
                              max_version: rule.max_version || "",
                            })
                          }
                        >
                          edit
                        </Button>
                        <Button
                          size="xs"
                          variant="ghost"
                          colorScheme="red"
                          onClick={() => void remove(rule)}
                        >
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
          <Button size="sm" variant="ghost" onClick={() => void seed()}>
            Скопировать встроенные правила
          </Button>
          <Button size="sm" variant="ghost" onClick={() => void load()}>
            Обновить
          </Button>
        </HStack>
      </Panel>

      <Panel label={draft.id ? `edit rule #${draft.id}` : "new rule"}>
        <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap="4">
          <FormControl>
            <FormLabel>Название</FormLabel>
            <Input
              value={draft.name}
              onChange={(event) => update({ name: event.target.value })}
            />
          </FormControl>
          <FormControl gridColumn={{ md: "span 2" }}>
            <FormLabel>Регулярное выражение по User-Agent</FormLabel>
            <Input
              fontFamily="mono"
              value={draft.pattern}
              onChange={(event) => update({ pattern: event.target.value })}
            />
          </FormControl>
          <FormControl>
            <FormLabel>Формат</FormLabel>
            <Select
              value={draft.config_format}
              onChange={(event) => update({ config_format: event.target.value })}
            >
              {formats.map((format) => (
                <option key={format} value={format}>
                  {format}
                </option>
              ))}
            </Select>
          </FormControl>
          <FormControl>
            <FormLabel>Приоритет</FormLabel>
            <Input
              type="number"
              value={draft.priority}
              onChange={(event) =>
                update({ priority: Number(event.target.value) || 0 })
              }
            />
          </FormControl>
          <FormControl>
            <FormLabel>Версии клиента (мин / макс)</FormLabel>
            <HStack>
              <Input
                placeholder="1.8.29"
                value={draft.min_version || ""}
                onChange={(event) => update({ min_version: event.target.value })}
              />
              <Input
                placeholder="—"
                value={draft.max_version || ""}
                onChange={(event) => update({ max_version: event.target.value })}
              />
            </HStack>
          </FormControl>
        </Grid>
        <HStack mt="4" spacing="6" flexWrap="wrap">
          <Checkbox
            isChecked={draft.as_base64}
            onChange={(event) => update({ as_base64: event.target.checked })}
          >
            base64
          </Checkbox>
          <Checkbox
            isChecked={draft.reverse}
            onChange={(event) => update({ reverse: event.target.checked })}
          >
            обратный порядок
          </Checkbox>
          <Checkbox
            isChecked={draft.ignore_case}
            onChange={(event) => update({ ignore_case: event.target.checked })}
          >
            без учёта регистра
          </Checkbox>
          <Checkbox
            isChecked={draft.is_disabled}
            onChange={(event) => update({ is_disabled: event.target.checked })}
          >
            отключено
          </Checkbox>
        </HStack>
        <HStack mt="4" justify="flex-end" spacing="3">
          {draft.id && (
            <Button variant="ghost" onClick={() => setDraft(emptyDraft)}>
              Отмена
            </Button>
          )}
          <Button
            colorScheme="primary"
            isLoading={saving}
            isDisabled={!draft.name || !draft.pattern}
            onClick={() => void save()}
          >
            {draft.id ? "Сохранить правило" : "Добавить правило"}
          </Button>
        </HStack>
      </Panel>

      <Panel label="user-agent preview">
        <HStack align="flex-end" spacing="3" flexWrap="wrap">
          <FormControl maxW="520px">
            <FormLabel>User-Agent</FormLabel>
            <Input
              fontFamily="mono"
              placeholder="v2rayNG/1.8.29"
              value={userAgent}
              onChange={(event) => setUserAgent(event.target.value)}
            />
          </FormControl>
          <Button variant="ghost" onClick={() => void runPreview()}>
            Проверить
          </Button>
        </HStack>
        {preview && (
          <HStack mt="4" spacing="2" flexWrap="wrap" fontFamily="mono">
            <Badge colorScheme="primary">{preview.config_format}</Badge>
            <Badge>{preview.rule}</Badge>
            <Badge>{preview.source}</Badge>
            <Badge>{preview.media_type}</Badge>
            {preview.as_base64 && <Badge>b64</Badge>}
            {preview.reverse && <Badge>reverse</Badge>}
          </HStack>
        )}
      </Panel>

      <Panel label="response cache">
        <HStack spacing="6" flexWrap="wrap" fontFamily="mono" fontSize="sm">
          <Text>записей: {cacheState?.entries ?? "—"}</Text>
          <Text>ttl: {cacheState?.ttl ?? "—"}s</Text>
          <Text>etag: {cacheState?.etag ? "on" : "off"}</Text>
          <Button size="sm" variant="ghost" onClick={() => void flushCache()}>
            Сбросить кэш
          </Button>
        </HStack>
      </Panel>
    </VStack>
  );
};

const TokensSection: FC = () => {
  const toast = useToast();
  const [username, setUsername] = useState("");
  const [loaded, setLoaded] = useState("");
  const [tokens, setTokens] = useState<Token[]>([]);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [expiresInDays, setExpiresInDays] = useState("");

  const load = async (target: string) => {
    if (!target) return;
    setLoading(true);
    try {
      const data = await fetch<{ tokens: Token[] }>(
        `/user/${encodeURIComponent(target)}/subscription/tokens`
      );
      setTokens(data.tokens);
      setLoaded(target);
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Failed to load tokens"),
        status: "error",
        position: "top",
      });
    } finally {
      setLoading(false);
    }
  };

  const create = async () => {
    try {
      await fetch(`/user/${encodeURIComponent(loaded)}/subscription/tokens`, {
        method: "POST",
        body: {
          name: name || null,
          expires_in_days: expiresInDays ? Number(expiresInDays) : null,
        },
      });
      setName("");
      setExpiresInDays("");
      await load(loaded);
      toast({ title: "Token issued", status: "success", position: "top" });
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Failed to issue token"),
        status: "error",
        position: "top",
      });
    }
  };

  const revoke = async (token: Token) => {
    try {
      await fetch(
        `/user/${encodeURIComponent(loaded)}/subscription/tokens/${token.id}/revoke`,
        { method: "POST" }
      );
      await load(loaded);
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Failed to revoke token"),
        status: "error",
        position: "top",
      });
    }
  };

  const remove = async (token: Token) => {
    try {
      await fetch(
        `/user/${encodeURIComponent(loaded)}/subscription/tokens/${token.id}`,
        { method: "DELETE" }
      );
      await load(loaded);
    } catch (error: any) {
      toast({
        title: errorMessage(error, "Failed to delete token"),
        status: "error",
        position: "top",
      });
    }
  };

  const copy = (value: string) => {
    void navigator.clipboard?.writeText(value);
    toast({ title: "Скопировано", status: "success", position: "top", duration: 1200 });
  };

  return (
    <VStack align="stretch" spacing="4">
      <Alert status="info" fontSize="sm">
        <AlertIcon />
        Отдельная ссылка на каждое устройство. Ревокация одного токена не влияет
        на остальные; общая ревокация подписки гасит все выданные ранее.
      </Alert>

      <Panel label="user">
        <HStack align="flex-end" spacing="3" flexWrap="wrap">
          <FormControl maxW="360px">
            <FormLabel>Имя пользователя</FormLabel>
            <Input
              fontFamily="mono"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void load(username.trim());
              }}
            />
          </FormControl>
          <Button
            colorScheme="primary"
            isLoading={loading}
            isDisabled={!username.trim()}
            onClick={() => void load(username.trim())}
          >
            Загрузить токены
          </Button>
        </HStack>
      </Panel>

      {loaded && (
        <>
          <Panel label={`tokens · ${loaded}`}>
            <Box overflowX="auto">
              <Table size="sm" fontFamily="mono">
                <Thead>
                  <Tr>
                    <Th>name</Th>
                    <Th>state</Th>
                    <Th>created</Th>
                    <Th>expires</Th>
                    <Th>last used</Th>
                    <Th />
                  </Tr>
                </Thead>
                <Tbody>
                  {tokens.length === 0 && (
                    <Tr>
                      <Td colSpan={6}>
                        <Text color="terminal.dim">Токенов пока нет.</Text>
                      </Td>
                    </Tr>
                  )}
                  {tokens.map((token) => (
                    <Tr key={token.id} opacity={token.is_active ? 1 : 0.5}>
                      <Td>{token.name || `#${token.id}`}</Td>
                      <Td>
                        <Badge colorScheme={token.is_active ? "primary" : "red"}>
                          {token.revoked_at
                            ? "revoked"
                            : token.is_active
                            ? "active"
                            : "expired"}
                        </Badge>
                      </Td>
                      <Td>{when(token.created_at)}</Td>
                      <Td>{token.expires_at ? when(token.expires_at) : "∞"}</Td>
                      <Td>
                        <Text
                          maxW="220px"
                          isTruncated
                          title={token.last_user_agent || ""}
                        >
                          {when(token.last_used_at)}
                          {token.last_user_agent
                            ? ` · ${token.last_user_agent}`
                            : ""}
                        </Text>
                      </Td>
                      <Td>
                        <HStack justify="flex-end" spacing="2">
                          <Button
                            size="xs"
                            variant="ghost"
                            onClick={() => copy(token.url || token.token)}
                          >
                            copy
                          </Button>
                          {token.is_active && (
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => void revoke(token)}
                            >
                              revoke
                            </Button>
                          )}
                          <Button
                            size="xs"
                            variant="ghost"
                            colorScheme="red"
                            onClick={() => void remove(token)}
                          >
                            delete
                          </Button>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          </Panel>

          <Panel label="issue token">
            <HStack align="flex-end" spacing="3" flexWrap="wrap">
              <FormControl maxW="260px">
                <FormLabel>Метка (устройство)</FormLabel>
                <Input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </FormControl>
              <FormControl maxW="200px">
                <FormLabel>Срок жизни, дней</FormLabel>
                <Input
                  type="number"
                  placeholder="бессрочно"
                  value={expiresInDays}
                  onChange={(event) => setExpiresInDays(event.target.value)}
                />
              </FormControl>
              <Button colorScheme="primary" onClick={() => void create()}>
                Выдать токен
              </Button>
            </HStack>
          </Panel>
        </>
      )}
    </VStack>
  );
};

export const SubscriptionSettingsPage: FC = () => (
  <Box>
    <Header title="Subscriptions" />
    <Tabs colorScheme="primary" isLazy>
      <TabList>
        <Tab>Правила клиентов</Tab>
        <Tab>Токены</Tab>
      </TabList>
      <TabPanels>
        <TabPanel px="0">
          <RulesSection />
        </TabPanel>
        <TabPanel px="0">
          <TokensSection />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </Box>
);

export default SubscriptionSettingsPage;
