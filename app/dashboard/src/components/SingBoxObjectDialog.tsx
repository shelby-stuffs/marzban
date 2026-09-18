import {
  Alert,
  AlertIcon,
  Button,
  Checkbox,
  FormControl,
  FormHelperText,
  FormLabel,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Stack,
  Text,
  Textarea,
} from "@chakra-ui/react";
import { useEffect, useMemo, useState } from "react";

type JsonObject = Record<string, any>;

type Props = {
  isOpen: boolean;
  title: string;
  schema: JsonObject | null;
  section: "inbounds" | "outbounds" | "dnsServers" | "endpoints" | "services";
  initialValue: JsonObject;
  onClose: () => void;
  onSave: (value: JsonObject) => void;
};

const SECTION_DEFS: Record<Props["section"], string> = {
  inbounds: "Inbound",
  outbounds: "Outbound",
  dnsServers: "DNSServer",
  endpoints: "Endpoint",
  services: "Service",
};

const titleize = (value: string) => value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const resolveRef = (schema: JsonObject, root: JsonObject): JsonObject => {
  const ref = schema?.$ref;
  if (typeof ref !== "string" || !ref.startsWith("#/$defs/")) return schema;
  return root.$defs?.[ref.slice("#/$defs/".length)] || schema;
};

const mergeSchemas = (schema: JsonObject, root: JsonObject): JsonObject => {
  const resolved = resolveRef(schema || {}, root);
  if (Array.isArray(resolved.allOf)) {
    return resolved.allOf.reduce((result: JsonObject, item: JsonObject) => ({
      ...result,
      ...mergeSchemas(item, root),
      properties: { ...(result.properties || {}), ...(mergeSchemas(item, root).properties || {}) },
      required: [...(result.required || []), ...(mergeSchemas(item, root).required || [])],
    }), { ...resolved });
  }
  return resolved;
};

const selectVariant = (schema: JsonObject, value: JsonObject, root: JsonObject): JsonObject => {
  const resolved = mergeSchemas(schema, root);
  const variants = resolved.oneOf || resolved.anyOf;
  if (!Array.isArray(variants)) return resolved;
  const selected = variants.find((variant: JsonObject) => {
    const typeConst = variant?.properties?.type?.const;
    return typeConst && typeConst === value?.type;
  }) || variants.find((variant: JsonObject) => variant?.properties?.type?.const === "mixed") || variants[0];
  return mergeSchemas(selected || {}, root);
};

const sectionSchema = (schema: JsonObject, section: Props["section"], value: JsonObject) => {
  if (!schema) return null;
  const definition = schema.$defs?.[SECTION_DEFS[section]];
  return selectVariant(definition || {}, value, schema);
};

const sectionTypeOptions = (schema: JsonObject, section: Props["section"]) => {
  const definition = schema?.$defs?.[SECTION_DEFS[section]];
  return Array.isArray(definition?.oneOf)
    ? definition.oneOf.map((item: JsonObject) => item?.properties?.type?.const).filter(Boolean)
    : [];
};

const semanticRequired = (section: Props["section"], type: unknown): string[] => {
  if (typeof type !== "string") return [];
  if (section === "inbounds") {
    if (!["direct", "tun", "cloudflared"].includes(type)) return ["listen_port"];
    if (type === "tun") return ["address"];
  }
  if (section === "outbounds") {
    if (["socks", "http", "shadowsocks", "vmess", "trojan", "naive", "hysteria", "vless", "tuic", "hysteria2", "anytls", "snell", "shadowtls", "ssh"].includes(type)) {
      return ["server", "server_port"];
    }
    if (["selector", "urltest"].includes(type)) return ["outbounds"];
  }
  if (section === "dnsServers" && ["tcp", "udp", "tls", "quic", "h3", "https"].includes(type)) {
    return ["server"];
  }
  return [];
};

const isComplex = (schema: JsonObject) => Boolean(
  schema?.type === "object" ||
  schema?.type === "array" ||
  schema?.$ref ||
  schema?.oneOf ||
  schema?.anyOf
);

const stringifyField = (value: unknown, schema: JsonObject) => {
  if (value === undefined || value === null) return schema?.type === "array" || isComplex(schema) ? "" : "";
  if (schema?.type === "array" || isComplex(schema) || typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
};

export const SingBoxObjectDialog = ({ isOpen, title, schema, section, initialValue, onClose, onSave }: Props) => {
  const [value, setValue] = useState<JsonObject>(initialValue || {});
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) return;
    setValue(initialValue || {});
    setError("");
  }, [initialValue, isOpen]);

  const resolved = useMemo(() => sectionSchema(schema || {}, section, value), [schema, section, value]);
  const properties: JsonObject = resolved?.properties || {};
  const required = new Set<string>([...(resolved?.required || []), "tag", ...semanticRequired(section, value.type)]);
  const typeOptions = sectionTypeOptions(schema || {}, section);

  const update = (key: string, next: unknown) => setValue((current) => ({ ...current, [key]: next }));

  const save = () => {
    if (!schema) {
      setError("sing-box schema is still loading");
      return;
    }
    for (const key of required) {
      const field = value[key];
      if (field === undefined || field === null || field === "" || (Array.isArray(field) && field.length === 0)) {
        setError(`${titleize(key)} is required`);
        return;
      }
    }
    const nextValue = { ...value };
    for (const [key, fieldSchema] of Object.entries(properties)) {
      const fieldValue = nextValue[key];
      if (typeof fieldValue !== "string" || !isComplex(fieldSchema) || !fieldValue.trim()) continue;
      try {
        if (fieldSchema.type === "array" || fieldSchema.type === "object" || fieldSchema.$ref || fieldSchema.oneOf || fieldSchema.anyOf) {
          nextValue[key] = JSON.parse(fieldValue);
        }
      } catch {
        setError(`${titleize(key)} must contain valid JSON`);
        return;
      }
    }
    onSave(nextValue);
    onClose();
  };

  const changeType = (nextType: string) => {
    const nextSchema = sectionSchema(schema || {}, section, { type: nextType });
    const allowed = new Set(Object.keys(nextSchema?.properties || {}));
    setValue((current) => ({
      type: nextType,
      ...Object.fromEntries(Object.entries(current).filter(([key]) => key !== "type" && allowed.has(key))),
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg="terminal.bg" border="1px solid" borderColor="terminal.border">
        <ModalHeader fontFamily="mono">{title}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {!schema && <Alert status="warning" mb="4"><AlertIcon />Loading sing-box schema…</Alert>}
          {error && <Alert status="error" mb="4"><AlertIcon />{error}</Alert>}
          <Stack spacing="4">
            {Object.entries(properties).map(([key, rawSchema]) => {
              const fieldSchema = mergeSchemas(rawSchema as JsonObject, schema || {});
              const fieldValue = value[key];
              const isRequired = required.has(key);
              const enumValues = fieldSchema.enum || [];
              const typeConst = fieldSchema.const;
              if (key === "type" && typeOptions.length) {
                return <FormControl key={key} isRequired><FormLabel>{titleize(key)}</FormLabel><Select value={String(value.type || typeConst || "")} onChange={(event) => changeType(event.target.value)}>{typeOptions.map((item: string) => <option key={item} value={item}>{item}</option>)}</Select></FormControl>;
              }
              if (key === "type" && Array.isArray(fieldSchema.enum)) {
                return <FormControl key={key} isRequired={isRequired}><FormLabel>{titleize(key)}</FormLabel><Select value={String(fieldValue || "")} onChange={(event) => update(key, event.target.value)}>{enumValues.map((item: string) => <option key={item} value={item}>{item || "default"}</option>)}</Select></FormControl>;
              }
              if (fieldSchema.type === "boolean") {
                return <FormControl key={key}><Checkbox isChecked={fieldValue === true} onChange={(event) => update(key, event.target.checked)}>{titleize(key)}</Checkbox></FormControl>;
              }
              if (fieldSchema.type === "number" || fieldSchema.type === "integer") {
                return <FormControl key={key} isRequired={isRequired}><FormLabel>{titleize(key)}</FormLabel><Input type="number" value={fieldValue === undefined ? "" : String(fieldValue)} onChange={(event) => update(key, event.target.value === "" ? undefined : Number(event.target.value))} /><FormHelperText>{fieldSchema.description}</FormHelperText></FormControl>;
              }
              if (fieldSchema.enum?.length) {
                return <FormControl key={key} isRequired={isRequired}><FormLabel>{titleize(key)}</FormLabel><Select value={String(fieldValue || "")} onChange={(event) => update(key, event.target.value)}><option value="">—</option>{fieldSchema.enum.map((item: string) => <option key={item} value={item}>{item || "default"}</option>)}</Select><FormHelperText>{fieldSchema.description}</FormHelperText></FormControl>;
              }
              if (fieldSchema.type === "string" && !fieldSchema.oneOf && !fieldSchema.anyOf) {
                return <FormControl key={key} isRequired={isRequired}><FormLabel>{titleize(key)}</FormLabel><Input fontFamily="mono" value={String(fieldValue || "")} onChange={(event) => update(key, event.target.value)} /><FormHelperText>{fieldSchema.description}</FormHelperText></FormControl>;
              }
              return <FormControl key={key} isRequired={isRequired}><FormLabel>{titleize(key)} <Text as="span" color="gray.500" fontSize="xs">(JSON)</Text></FormLabel><Textarea minH="120px" fontFamily="mono" fontSize="sm" value={stringifyField(fieldValue, fieldSchema)} onChange={(event) => update(key, event.target.value)} placeholder={fieldSchema.description || "JSON value"} /><FormHelperText>{fieldSchema.description}</FormHelperText></FormControl>;
            })}
          </Stack>
        </ModalBody>
        <ModalFooter gap="2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button colorScheme="primary" onClick={save}>Save</Button></ModalFooter>
      </ModalContent>
    </Modal>
  );
};
