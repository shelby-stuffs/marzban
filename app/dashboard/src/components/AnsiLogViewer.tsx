import { Badge, Box, HStack, Text } from "@chakra-ui/react";
import { forwardRef } from "react";
import type { CSSProperties, ReactNode } from "react";

const BASIC_COLORS = [
  "#161b22", "#ff6b6b", "#52d273", "#f4c95d", "#58a6ff", "#c792ea", "#4fd1c5", "#d8dee9",
  "#6b7280", "#ff8585", "#69e58c", "#ffd875", "#79b8ff", "#d6a4ff", "#67e8f9", "#ffffff",
];

export const ansi256Color = (value: number) => {
  if (value < 0 || value > 255) return undefined;
  if (value < 16) return BASIC_COLORS[value];
  if (value < 232) {
    const index = value - 16;
    const level = (part: number) => part === 0 ? 0 : 55 + part * 40;
    const red = level(Math.floor(index / 36));
    const green = level(Math.floor((index % 36) / 6));
    const blue = level(index % 6);
    return `rgb(${red}, ${green}, ${blue})`;
  }
  const gray = 8 + (value - 232) * 10;
  return `rgb(${gray}, ${gray}, ${gray})`;
};

type StyledChunk = { text: string; style: CSSProperties };

export const tokenizeAnsi = (line: string): StyledChunk[] => {
  // Some transports preserve ESC, while others leave only strings such as [36m.
  const pattern = /(?:\u001b\[|\[)([0-9;]*)m/g;
  const chunks: StyledChunk[] = [];
  let style: CSSProperties = {};
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(line)) !== null) {
    if (match.index > cursor) chunks.push({ text: line.slice(cursor, match.index), style: { ...style } });
    const codes = (match[1] || "0").split(";").map(Number);
    for (let index = 0; index < codes.length; index += 1) {
      const code = codes[index];
      if (code === 0) style = {};
      else if (code === 1) style = { ...style, fontWeight: 700 };
      else if (code === 2) style = { ...style, opacity: 0.65 };
      else if (code === 22) style = { ...style, fontWeight: undefined, opacity: undefined };
      else if (code >= 30 && code <= 37) style = { ...style, color: BASIC_COLORS[code - 30] };
      else if (code >= 90 && code <= 97) style = { ...style, color: BASIC_COLORS[code - 90 + 8] };
      else if (code === 39) style = { ...style, color: undefined };
      else if (code === 38 && codes[index + 1] === 5 && Number.isFinite(codes[index + 2])) {
        style = { ...style, color: ansi256Color(codes[index + 2]) };
        index += 2;
      } else if (code === 38 && codes[index + 1] === 2 && codes.slice(index + 2, index + 5).every(Number.isFinite)) {
        style = { ...style, color: `rgb(${codes[index + 2]}, ${codes[index + 3]}, ${codes[index + 4]})` };
        index += 4;
      }
    }
    cursor = pattern.lastIndex;
  }
  if (cursor < line.length) chunks.push({ text: line.slice(cursor), style: { ...style } });
  return chunks.length ? chunks : [{ text: line, style: {} }];
};

const TOKEN = /(\+?\d{4}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}|\b(?:TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\b)/g;
const LEVEL_COLORS: Record<string, string> = {
  TRACE: "#a78bfa", DEBUG: "#c084fc", INFO: "#5eead4", WARN: "#fbbf24",
  WARNING: "#fbbf24", ERROR: "#fb7185", FATAL: "#ff4d6d",
};

const renderChunk = (chunk: StyledChunk, key: string): ReactNode[] =>
  chunk.text.split(TOKEN).filter(Boolean).map((text, index) => {
    const isTimestamp = /^\+?\d{4}\s+\d{4}-/.test(text);
    const levelColor = LEVEL_COLORS[text];
    const style: CSSProperties = {
      ...chunk.style,
      color: chunk.style.color || (isTimestamp ? "#718096" : levelColor),
      fontWeight: chunk.style.fontWeight || (levelColor ? 700 : undefined),
    };
    return <span key={`${key}-${index}`} style={style}>{text}</span>;
  });

const plainLine = (line: string) => line.replace(/(?:\u001b\[|\[)[0-9;]*m/g, "");
const accentForLine = (line: string) => {
  const plain = plainLine(line);
  if (/\b(?:ERROR|FATAL)\b/.test(plain)) return "#fb7185";
  if (/\bWARN(?:ING)?\b/.test(plain)) return "#fbbf24";
  if (/\bDEBUG\b/.test(plain)) return "#c084fc";
  if (/\bINFO\b/.test(plain)) return "#2dd4bf";
  if (plain.startsWith("[marzban]")) return "#58a6ff";
  return "transparent";
};

type Props = {
  logs: string[];
  emptyText: string;
  title?: string;
};

export const AnsiLogViewer = forwardRef<HTMLDivElement, Props>(({ logs, emptyText, title = "sing-box / stdout" }, ref) => (
  <Box
    border="1px solid"
    borderColor="#263142"
    borderRadius="8px"
    overflow="hidden"
    bg="#070a0f"
    boxShadow="0 14px 40px rgba(0, 0, 0, .28), inset 0 1px 0 rgba(255, 255, 255, .025)"
  >
    <HStack
      px="4" py="2.5" spacing="3" bg="linear-gradient(180deg, #151b25 0%, #0e131b 100%)"
      borderBottom="1px solid" borderColor="#263142"
    >
      <HStack spacing="1.5">
        <Box w="10px" h="10px" borderRadius="full" bg="#ff5f57" boxShadow="0 0 10px rgba(255,95,87,.25)" />
        <Box w="10px" h="10px" borderRadius="full" bg="#febc2e" boxShadow="0 0 10px rgba(254,188,46,.2)" />
        <Box w="10px" h="10px" borderRadius="full" bg="#28c840" boxShadow="0 0 10px rgba(40,200,64,.2)" />
      </HStack>
      <Text flex="1" textAlign="center" color="#8b9bb0" fontFamily="mono" fontSize="xs">{title}</Text>
      <Badge bg="#1a2330" color="#8b9bb0" borderRadius="full" px="2" fontFamily="mono">{logs.length}</Badge>
    </HStack>
    <Box ref={ref} minH="260px" maxH="480px" overflow="auto" py="2" fontFamily="mono" fontSize="12px" lineHeight="1.7">
      {logs.length ? logs.map((line, index) => (
        <Box
          key={index}
          display="flex"
          minW="max-content"
          px="0"
          borderLeft="2px solid"
          borderLeftColor={accentForLine(line)}
          _hover={{ bg: "rgba(88, 166, 255, .055)" }}
        >
          <Text
            as="span" userSelect="none" flex="0 0 48px" pr="3" textAlign="right"
            color="#39465a" borderRight="1px solid" borderRightColor="#151d29"
          >{index + 1}</Text>
          <Box as="code" display="block" px="4" color="#c8d6e2" whiteSpace="pre-wrap" wordBreak="break-word">
            {tokenizeAnsi(line).flatMap((chunk, chunkIndex) => renderChunk(chunk, `${index}-${chunkIndex}`))}
          </Box>
        </Box>
      )) : (
        <Box minH="240px" display="flex" alignItems="center" justifyContent="center">
          <Text color="#536176" fontFamily="mono" fontSize="sm">$ {emptyText}</Text>
        </Box>
      )}
    </Box>
  </Box>
));

AnsiLogViewer.displayName = "AnsiLogViewer";
