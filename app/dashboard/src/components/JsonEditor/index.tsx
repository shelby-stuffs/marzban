import { Box } from "@chakra-ui/react";
import Editor, { BeforeMount, OnMount } from "@monaco-editor/react";
import { forwardRef, useEffect, useRef } from "react";
import { useDashboardTheme } from "contexts/ThemeContext";

export type JSONEditorProps = {
  onChange: (value: string) => void;
  json: any;
  schemaUri?: string;
};
const editorThemes = {
  "terminal-green": { accent: "00E08C", key: "66DAFA", value: "7DFFC0", bg: "080C0F", fg: "DFFFF0", line: "11191D", dim: "668678", selection: "153C2D" },
  "glamour-pink": { accent: "F653AD", key: "D4B4FF", value: "FF96D2", bg: "1A0F1C", fg: "FFE9F6", line: "2A182D", dim: "C892AF", selection: "4C2141" },
  "cyber-violet": { accent: "9B7CFF", key: "5DE7FA", value: "BAA1FF", bg: "0F0D20", fg: "F3EFFF", line: "211B38", dim: "AAA0CB", selection: "392D68" },
  "airy-light": { accent: "7590FB", key: "F58AC1", value: "9BAEFF", bg: "111522", fg: "F1F5FF", line: "1C2335", dim: "8995AF", selection: "30416E" },
} as const;
const configureTheme: BeforeMount = (monaco) => {
  Object.entries(editorThemes).forEach(([id, colors]) => monaco.editor.defineTheme(`marzban-${id}`, {
    base: "vs-dark", inherit: true,
    rules: [{ token: "string.key.json", foreground: colors.key }, { token: "string.value.json", foreground: colors.value }, { token: "number", foreground: "FFC08E" }],
    colors: { "editor.background": `#${colors.bg}`, "editor.foreground": `#${colors.fg}`, "editorLineNumber.foreground": `#${colors.dim}`, "editorCursor.foreground": `#${colors.accent}`, "editor.selectionBackground": `#${colors.selection}`, "editor.lineHighlightBackground": `#${colors.line}` },
  }));
};
const stringify = (value: any) => JSON.stringify(value ?? {}, null, 2);
export const JsonEditor = forwardRef<HTMLDivElement, JSONEditorProps>(({ json, onChange, schemaUri }, ref) => {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);
  const { theme } = useDashboardTheme();
  const handleMount: OnMount = (editor) => { editorRef.current = editor; };
  const configure = (monaco: Parameters<BeforeMount>[0]) => {
    configureTheme(monaco);
    if (schemaUri) {
      const jsonDefaults = (monaco.languages as any).json.jsonDefaults;
      jsonDefaults.setDiagnosticsOptions({
        validate: true,
        enableSchemaRequest: true,
        schemas: [{ uri: schemaUri, fileMatch: ["*"] }],
      });
    }
  };
  useEffect(() => { const editor = editorRef.current; if (editor && !editor.hasTextFocus()) { const text = stringify(json); if (editor.getValue() !== text) editor.setValue(text); } }, [json]);
  return <Box ref={ref} border="1px solid" borderColor="terminal.border" borderRadius="14px" h="full" overflow="hidden"><Editor height="500px" defaultLanguage="json" defaultValue={stringify(json)} theme={`marzban-${theme}`} beforeMount={configure} onMount={handleMount} onChange={(value) => onChange(value ?? "")} options={{ minimap: { enabled: false }, fontSize: 13, fontFamily: "JetBrains Mono, monospace", tabSize: 2, scrollBeyondLastLine: false, automaticLayout: true, formatOnPaste: true, fixedOverflowWidgets: true }} /></Box>;
});
