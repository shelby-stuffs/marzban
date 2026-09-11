import { extendTheme } from "@chakra-ui/react";
import { terminalTheme } from "./src/theme/terminal";

const mono = `"JetBrains Mono","SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace`;
const sans = `Manrope,Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif`;

const BG = "#130a14";
const SURFACE = "#1d111f";
const OVERLAY = "#2a182d";
const BORDER = "#593653";
const TEXT = "#ffe9f6";

// The dashboard is dark-only. There is no light color mode, so every component
// style below targets a single dark canvas and no _light branches exist.
const baseTheme = extendTheme({
  config: {
    initialColorMode: "dark",
    useSystemColorMode: false,
  },
  fonts: {
    body: sans,
    heading: mono,
    mono,
  },
  fontSizes: {
    xs: "11px",
    sm: "13px",
    md: "14px",
    lg: "16px",
    xl: "19px",
    "2xl": "23px",
    "3xl": "28px",
  },
  radii: { sm: "8px", md: "12px", lg: "16px", xl: "20px" },
  colors: {
    // Kept as an alias so legacy references still resolve to the dark border.
    "light-border": BORDER,
    white: TEXT,
    terminal: {
      bg: BG,
      surface: SURFACE,
      overlay: OVERLAY,
      border: BORDER,
      dim: "#5b6b7d",
      text: TEXT,
    },
    primary: {
      50: "#fff2fa",
      100: "#ffd9ef",
      200: "#ffbce2",
      300: "#ff96d2",
      400: "#ff72c2",
      500: "#f653ad",
      600: "#d83b93",
      700: "#ad2b73",
      800: "#7d2056",
      900: "#4d1737",
    },
    accent: {
      400: "#d4b4ff",
      500: "#bd91ff",
      600: "#9d6ee8",
    },
    gray: {
      50: "#fff4fa",
      100: "#f7ddea",
      200: "#e9bfd4",
      300: "#dca9c3",
      400: "#c892af",
      500: "#a87592",
      600: BORDER,
      700: OVERLAY,
      750: "#241427",
      800: SURFACE,
      900: BG,
    },
  },
  shadows: {
    outline: `0 0 0 3px rgba(246, 83, 173, 0.28)`,
    glow: "0 0 0 1px rgba(255, 150, 210, 0.32), 0 0 28px -6px rgba(246, 83, 173, 0.72)",
    panel: "0 1px 0 rgba(255,255,255,.08) inset, 0 20px 55px -34px rgba(246,83,173,.72), 0 14px 36px -28px rgba(0,0,0,.9)",
  },
  styles: {
    global: {
      html: { fontSize: "15px", bg: BG, colorScheme: "dark" },
      body: {
        lineHeight: 1.45,
        bg: BG,
        color: TEXT,
        backgroundImage:
          "radial-gradient(circle at 18% 8%, rgba(255,114,194,.18), transparent 31%), radial-gradient(circle at 86% 18%, rgba(189,145,255,.13), transparent 28%), linear-gradient(145deg, #130a14 0%, #1d0e1c 52%, #120a18 100%)",
        backgroundSize: "auto",
        backgroundAttachment: "fixed",
      },
      "*::selection": { bg: "primary.500", color: BG },
      "*::placeholder": { color: "gray.500" },
      "::-webkit-scrollbar": { width: "10px", height: "10px" },
      "::-webkit-scrollbar-track": { bg: "transparent" },
      "::-webkit-scrollbar-thumb": {
        bg: BORDER,
        borderRadius: "999px",
        _hover: { bg: "primary.700" },
      },
    },
  },
  components: {
    Heading: {
      baseStyle: {
        fontFamily: mono,
        fontWeight: "600",
        letterSpacing: "-0.01em",
      },
    },
    Card: {
      baseStyle: {
        container: {
          bg: SURFACE,
          borderColor: BORDER,
          borderRadius: "16px",
          boxShadow: "none",
        },
      },
    },
    Button: {
      baseStyle: {
        borderRadius: "12px",
        fontFamily: sans,
        fontWeight: "500",
        letterSpacing: "0.02em",
        _focusVisible: { boxShadow: "outline" },
      },
      defaultProps: { size: "sm", colorScheme: "primary" },
      variants: {
        solid: {
          bg: "primary.500",
          color: "#04150d",
          _hover: { bg: "primary.400", _disabled: { bg: "primary.700" } },
          _active: { bg: "primary.600" },
        },
        outline: {
          borderColor: BORDER,
          color: TEXT,
          bg: "transparent",
          _hover: { bg: OVERLAY, borderColor: "primary.600", color: "primary.300" },
          _active: { bg: OVERLAY },
        },
        ghost: {
          color: "gray.400",
          _hover: { bg: OVERLAY, color: "primary.300" },
          _active: { bg: OVERLAY },
        },
      },
    },
    IconButton: { defaultProps: { size: "sm", variant: "outline" } },
    Badge: {
      baseStyle: {
        borderRadius: "999px",
        fontFamily: sans,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        fontWeight: "500",
        px: "1.5",
      },
    },
    Tag: {
      baseStyle: {
        container: { borderRadius: "999px", fontFamily: sans, bg: OVERLAY, color: TEXT },
      },
      defaultProps: { size: "sm" },
    },
    Code: {
      baseStyle: {
        fontFamily: mono,
        bg: OVERLAY,
        color: "primary.300",
        borderRadius: "8px",
      },
    },
    FormLabel: {
      baseStyle: {
        fontFamily: sans,
        fontSize: "xs",
        fontWeight: "700",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        mb: "1.5",
        color: "gray.400",
      },
    },
    FormHelperText: { baseStyle: { fontSize: "xs", color: "gray.500" } },
    Input: {
      defaultProps: { size: "sm", variant: "outline" },
      baseStyle: {
        field: {
          fontFamily: mono,
          borderRadius: "4px",
          bg: SURFACE,
          borderColor: BORDER,
          color: TEXT,
          _hover: { borderColor: "gray.500" },
          _focusVisible: { boxShadow: "none", borderColor: "primary.500", bg: OVERLAY },
          _placeholder: { color: "gray.500" },
          _disabled: { color: "gray.500", borderColor: BORDER },
        },
        addon: {
          fontFamily: mono,
          bg: OVERLAY,
          borderColor: BORDER,
          color: "gray.400",
        },
      },
    },
    NumberInput: {
      defaultProps: { size: "sm" },
      baseStyle: {
        field: {
          fontFamily: mono,
          bg: SURFACE,
          borderColor: BORDER,
          color: TEXT,
          _focusVisible: { boxShadow: "none", borderColor: "primary.500" },
        },
        stepper: { borderColor: BORDER, color: "gray.400" },
      },
    },
    Textarea: {
      defaultProps: { size: "sm" },
      baseStyle: {
        fontFamily: mono,
        borderRadius: "4px",
        bg: SURFACE,
        borderColor: BORDER,
        color: TEXT,
        _focusVisible: { boxShadow: "none", borderColor: "primary.500" },
        _placeholder: { color: "gray.500" },
      },
    },
    Select: {
      defaultProps: { size: "sm" },
      baseStyle: {
        field: {
          fontFamily: mono,
          borderRadius: "4px",
          bg: SURFACE,
          borderColor: BORDER,
          color: TEXT,
          _focusVisible: { boxShadow: "none", borderColor: "primary.500" },
          "> option": { bg: OVERLAY, color: TEXT },
        },
        icon: { color: "gray.500" },
      },
    },
    Checkbox: {
      defaultProps: { size: "sm", colorScheme: "primary" },
      baseStyle: {
        control: { borderRadius: "2px", borderColor: "gray.500", bg: SURFACE },
        label: { fontSize: "sm" },
      },
    },
    Switch: { defaultProps: { size: "sm", colorScheme: "primary" } },
    Tabs: {
      defaultProps: { size: "sm", colorScheme: "primary" },
      baseStyle: {
        tab: {
          fontFamily: mono,
          fontSize: "xs",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "gray.400",
          _selected: { color: "primary.300", borderColor: "primary.500" },
          _hover: { color: TEXT },
        },
        tablist: { borderColor: BORDER },
      },
    },
    Alert: {
      baseStyle: {
        container: {
          borderRadius: "4px",
          fontSize: "sm",
          borderLeft: "2px solid",
          borderLeftColor: "currentColor",
        },
      },
    },
    Menu: {
      baseStyle: {
        list: {
          minW: "auto",
          py: "1",
          borderRadius: "4px",
          bg: OVERLAY,
          borderColor: BORDER,
          boxShadow: "panel",
        },
        item: {
          fontFamily: mono,
          fontSize: "sm",
          py: "1.5",
          bg: "transparent",
          color: TEXT,
          _hover: { bg: SURFACE, color: "primary.300" },
          _focus: { bg: SURFACE },
        },
      },
    },
    Modal: {
      baseStyle: {
        dialog: {
          borderRadius: "16px",
          bg: SURFACE,
          border: "1px solid",
          borderColor: BORDER,
          boxShadow: "panel",
        },
        overlay: { bg: "rgba(3, 5, 8, 0.78)", backdropFilter: "blur(3px)" },
        header: {
          fontFamily: mono,
          fontSize: "sm",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          py: "3",
          borderBottom: "1px solid",
          borderColor: BORDER,
        },
        body: { py: "4" },
        footer: { py: "3", borderTop: "1px solid", borderColor: BORDER },
        closeButton: { borderRadius: "2px", _hover: { bg: OVERLAY } },
      },
    },
    Drawer: {
      baseStyle: {
        dialog: { bg: SURFACE, borderRight: "1px solid", borderColor: BORDER },
        overlay: { bg: "rgba(3, 5, 8, 0.78)" },
      },
    },
    Popover: {
      baseStyle: {
        content: {
          bg: OVERLAY,
          borderColor: BORDER,
          borderRadius: "4px",
          boxShadow: "panel",
          _focusVisible: { boxShadow: "panel" },
        },
      },
    },
    Tooltip: {
      baseStyle: {
        fontFamily: mono,
        fontSize: "xs",
        borderRadius: "3px",
        bg: OVERLAY,
        color: TEXT,
        border: "1px solid",
        borderColor: BORDER,
      },
    },
    Divider: { baseStyle: { borderColor: BORDER, opacity: 1 } },
    Table: {
      defaultProps: { size: "sm" },
      baseStyle: {
        table: { borderCollapse: "separate", borderSpacing: 0, fontFamily: mono },
        th: {
          px: "3",
          py: "2.5",
          fontSize: "xs",
          fontFamily: mono,
          fontWeight: "500",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "gray.400",
          background: OVERLAY,
          borderBottom: "1px solid",
          borderColor: `${BORDER} !important`,
        },
        td: {
          px: "3",
          py: "2",
          fontSize: "sm",
          transition: "background .1s ease-out",
          borderBottom: "1px solid",
          borderColor: `${BORDER} !important`,
        },
        tr: {
          "&.interactive": {
            cursor: "pointer",
            _hover: { "& > td": { bg: OVERLAY } },
          },
        },
      },
    },
  },
});

export const theme = extendTheme(baseTheme, terminalTheme);
export default theme;
