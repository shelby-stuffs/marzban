import { extendTheme } from "@chakra-ui/react";

const mono = `"JetBrains Mono","SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace`;
const sans = `Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",sans-serif`;

const BG = "#06080b";
const SURFACE = "#0b0f15";
const OVERLAY = "#101620";
const BORDER = "#1c2634";
const TEXT = "#c8d6e2";

// The dashboard is dark-only. There is no light color mode, so every component
// style below targets a single dark canvas and no _light branches exist.
export const theme = extendTheme({
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
  radii: { sm: "3px", md: "4px", lg: "6px", xl: "8px" },
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
      50: "#e6fff5",
      100: "#b8ffe3",
      200: "#7dffcd",
      300: "#42ffb6",
      400: "#12f79f",
      500: "#00e08c",
      600: "#00b872",
      700: "#008f58",
      800: "#00663f",
      900: "#003d26",
    },
    accent: {
      400: "#38e0ff",
      500: "#22d3ee",
      600: "#0ea5c4",
    },
    gray: {
      50: "#e7ecf1",
      100: "#cfd8e3",
      200: "#a9b7c6",
      300: "#a9b7c6",
      400: "#7d8fa3",
      500: "#5b6b7d",
      600: BORDER,
      700: OVERLAY,
      750: "#0e141c",
      800: SURFACE,
      900: BG,
    },
  },
  shadows: {
    outline: `0 0 0 1px #00e08c`,
    glow: "0 0 0 1px rgba(0, 224, 140, 0.35), 0 0 18px -6px rgba(0, 224, 140, 0.45)",
    panel: "0 1px 0 rgba(255, 255, 255, 0.02) inset, 0 8px 24px -18px rgba(0, 0, 0, 0.9)",
  },
  styles: {
    global: {
      html: { fontSize: "15px", bg: BG, colorScheme: "dark" },
      body: {
        lineHeight: 1.45,
        bg: BG,
        color: TEXT,
        backgroundImage:
          "linear-gradient(rgba(0,255,156,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,156,0.035) 1px, transparent 1px)",
        backgroundSize: "32px 32px",
        backgroundAttachment: "fixed",
      },
      "*::selection": { bg: "primary.500", color: BG },
      "*::placeholder": { color: "gray.500" },
      "::-webkit-scrollbar": { width: "10px", height: "10px" },
      "::-webkit-scrollbar-track": { bg: "transparent" },
      "::-webkit-scrollbar-thumb": {
        bg: BORDER,
        borderRadius: "0",
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
          borderRadius: "6px",
          boxShadow: "none",
        },
      },
    },
    Button: {
      baseStyle: {
        borderRadius: "4px",
        fontFamily: mono,
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
        borderRadius: "2px",
        fontFamily: mono,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        fontWeight: "500",
        px: "1.5",
      },
    },
    Tag: {
      baseStyle: {
        container: { borderRadius: "2px", fontFamily: mono, bg: OVERLAY, color: TEXT },
      },
      defaultProps: { size: "sm" },
    },
    Code: {
      baseStyle: {
        fontFamily: mono,
        bg: OVERLAY,
        color: "primary.300",
        borderRadius: "2px",
      },
    },
    FormLabel: {
      baseStyle: {
        fontFamily: mono,
        fontSize: "xs",
        fontWeight: "500",
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
          borderRadius: "6px",
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

export default theme;
