import { Box } from "@chakra-ui/react";
import Editor, { BeforeMount, OnMount } from "@monaco-editor/react";
import { forwardRef, useEffect, useRef } from "react";

export type JSONEditorProps = {
  onChange: (value: string) => void;
  json: any;
};

const configureTheme: BeforeMount = (monaco) => {
  monaco.editor.defineTheme("marzban-terminal", {
    base: "vs-dark", inherit: true,
    rules: [
      { token: "string.key.json", foreground: "89c5ff" },
      { token: "string.value.json", foreground: "42ffb6" },
      { token: "number", foreground: "ffc078" },
    ],
    colors: {
      "editor.background": "#0b0f15", "editor.foreground": "#c8d6e2",
      "editorLineNumber.foreground": "#8b9bb0",
      "editorCursor.foreground": "#00e08c",
      "editor.selectionBackground": "#143b30",
      "editor.lineHighlightBackground": "#101620",
    },
  });
};

const stringify = (value: any) => JSON.stringify(value ?? {}, null, 2);

export const JsonEditor = forwardRef<HTMLDivElement, JSONEditorProps>(
  ({ json, onChange }, ref) => {
    const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

    const handleMount: OnMount = (editor) => {
      editorRef.current = editor;
    };

    useEffect(() => {
      const editor = editorRef.current;
      if (editor && !editor.hasTextFocus()) {
        const text = stringify(json);
        if (editor.getValue() !== text) editor.setValue(text);
      }
    }, [json]);

    return (
      <Box
        ref={ref}
        border="1px solid"
        borderColor="terminal.border"
        borderRadius="4px"
        h="full"
        overflow="hidden"
      >
        <Editor
          height="500px"
          defaultLanguage="json"
          defaultValue={stringify(json)}
          theme="marzban-terminal"
          beforeMount={configureTheme}
          onMount={handleMount}
          onChange={(value) => onChange(value ?? "")}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: "JetBrains Mono, monospace",
            tabSize: 2,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            formatOnPaste: true,
            fixedOverflowWidgets: true,
          }}
        />
      </Box>
    );
  }
);
