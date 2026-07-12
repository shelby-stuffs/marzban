import { Box, useColorMode } from "@chakra-ui/react";
import Editor, { OnMount } from "@monaco-editor/react";
import { forwardRef, useEffect, useRef } from "react";

export type JSONEditorProps = {
  onChange: (value: string) => void;
  json: any;
};

const stringify = (value: any) => JSON.stringify(value ?? {}, null, 2);

export const JsonEditor = forwardRef<HTMLDivElement, JSONEditorProps>(
  ({ json, onChange }, ref) => {
    const { colorMode } = useColorMode();
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
        borderColor="gray.300"
        _dark={{ borderColor: "gray.500" }}
        borderRadius={5}
        h="full"
        overflow="hidden"
      >
        <Editor
          height="500px"
          defaultLanguage="json"
          defaultValue={stringify(json)}
          theme={colorMode === "dark" ? "vs-dark" : "vs"}
          onMount={handleMount}
          onChange={(value) => onChange(value ?? "")}
          options={{
            minimap: { enabled: false },
            fontSize: 12,
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
