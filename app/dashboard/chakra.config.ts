import { extendTheme } from "@chakra-ui/react";

const mono = `"JetBrains Mono","SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace`;
const sans = `Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",sans-serif`;

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
  },
  radii: { sm: "3px", md: "4px", lg: "6px", xl: "8px" },
  colors: {
    "light-border": "#d6dae0",
    terminal: {
      bg: "#06080b",
      surface: "#0b0f15",
      overlay: "#101620",
      border: "#1c2634",
      dim: "#5b6b7d",
      text: "#c8d6e2",
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
      50: "#f6f8fa",
      100: "#e7ecf1",
      200: "#cfd8e3",
      300: "#a9b7c6",
      400: "#7d8fa3",
      500: "#5b6b7d",
      600: "#1c2634",
      700: "#101620",
      750: "#0e141c",
      800: "#0b0f15",
      900: "#06080b",
    },
  },
  shadows: {
    outline: "0 0 0 1px var(--chakra-colors-primary-500)",
    glow: "0 0 0 1px rgba(0, 224, 140, 0.35), 0 0 18px -6px rgba(0, 224, 140, 0.45)",
    panel: "0 1px 0 rgba(255, 255, 255, 0.02) inset, 0 8px 24px -18px rgba(0, 0, 0, 0.9)",
  },
  styles: {
    global: {
      html: { fontSize: "15px" },
      body: {
        lineHeight: 1.45,
        bg: "terminal.bg",
        color: "terminal.text",
        backgroundImage:
          "linear-gradient(rgba(0,255,156,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,156,0.035) 1px, transparent 1px)",
        backgroundSize: "32px 32px",
        backgroundAttachment: "fixed",
        _light: {
          bg: "gray.50",
          color: "gray.800",
          backgroundImage: "none",
        },
      },
      "*::selection": { bg: "primary.500", color: "terminal.bg" },
      "::-webkit-scrollbar": { width: "10px", height: "10px" },
      "::-webkit-scrollbar-track": { bg: "transparent" },
      "::-webkit-scrollbar-thumb": {
        bg: "gray.600",
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
        textTransform: "none",
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
          borderColor: "terminal.border",
          color: "terminal.text",
          bg: "transparent",
          _hover: { bg: "terminal.overlay", borderColor: "primary.600", color: "primary.300" },
          _light: { borderColor: "light-border", color: "gray.700" },
        },
        ghost: {
          color: "gray.300",
          _hover: { bg: "terminal.overlay", color: "primary.300" },
          _light: { color: "gray.600", _hover: { bg: "gray.100" } },
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
      baseStyle: { container: { borderRadius: "2px", fontFamily: mono } },
      defaultProps: { size: "sm" },
    },
    Code: {
      baseStyle: {
        fontFamily: mono,
        bg: "terminal.overlay",
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
        _light: { color: "gray.600" },
      },
    },
    FormHelperText: { baseStyle: { fontSize: "xs", color: "gray.500" } },
    Input: {
      defaultProps: { size: "sm", variant: "outline" },
      baseStyle: {
        field: {
          fontFamily: mono,
          borderRadius: "4px",
          bg: "terminal.surface",
          borderColor: "terminal.border",
          _hover: { borderColor: "gray.500" },
          _focusVisible: {
            boxShadow: "none",
            borderColor: "primary.500",
            bg: "terminal.overlay",
          },
          _placeholder: { color: "gray.500" },
          _disabled: { color: "gray.500", borderColor: "terminal.border" },
          _light: { bg: "white", borderColor: "light-border" },
        },
        addon: {
          fontFamily: mono,
          bg: "terminal.overlay",
          borderColor: "terminal.border",
          color: "gray.400",
          _light: { bg: "gray.100", borderColor: "light-border", color: "gray.600" },
        },
      },
    },
    NumberInput: {
      defaultProps: { size: "sm" },
      baseStyle: {
        field: {
          fontFamily: mono,
          bg: "terminal.surface",
          borderColor: "terminal.border",
          _light: { bg: "white", borderColor: "light-border" },
        },
      },
    },
    Textarea: {
      defaultProps: { size: "sm" },
      baseStyle: {
        fontFamily: mono,
        borderRadius: "4px",
        bg: "terminal.surface",
        borderColor: "terminal.border",
        _focusVisible: { boxShadow: "none", borderColor: "primary.500" },
        _placeholder: { color: "gray.500" },
        _light: { bg: "white", borderColor: "light-border" },
      },
    },
    Select: {
      defaultProps: { size: "sm" },
      baseStyle: {
        field: {
          fontFamily: mono,
          borderRadius: "4px",
          bg: "terminal.surface",
          borderColor: "terminal.border",
          _focusVisible: { boxShadow: "none", borderColor: "primary.500" },
          _light: { bg: "white", borderColor: "light-border" },
          "> option": { bg: "terminal.overlay" },
        },
      },
    },
    Checkbox: {
      defaultProps: { size: "sm", colorScheme: "primary" },
      baseStyle: {
        control: { borderRadius: "2px", borderColor: "gray.500" },
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
          _selected: { color: "primary.300", borderColor: "primary.500" },
        },
        tablist: { borderColor: "terminal.border" },
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
          bg: "terminal.overlay",
          borderColor: "terminal.border",
          boxShadow: "panel",
          _light: { bg: "white", borderColor: "light-border" },
        },
        item: {
          fontFamily: mono,
          fontSize: "sm",
          py: "1.5",
          bg: "transparent",
          _hover: { bg: "terminal.surface", color: "primary.300" },
          _focus: { bg: "terminal.surface" },
          _light: { _hover: { bg: "gray.100" } },
        },
      },
    },
    Modal: {
      baseStyle: {
        dialog: {
          borderRadius: "6px",
          bg: "terminal.surface",
          border: "1px solid",
          borderColor: "terminal.border",
          boxShadow: "panel",
          _light: { bg: "white", borderColor: "light-border" },
        },
        overlay: { bg: "rgba(3, 5, 8, 0.75)", backdropFilter: "blur(3px)" },
        header: {
          fontFamily: mono,
          fontSize: "sm",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          py: "3",
          borderBottom: "1px solid",
          borderColor: "terminal.border",
        },
        body: { py: "4" },
        footer: { py: "3", borderTop: "1px solid", borderColor: "terminal.border" },
      },
    },
    Tooltip: {
      baseStyle: {
        fontFamily: mono,
        fontSize: "xs",
        borderRadius: "3px",
        bg: "terminal.overlay",
        color: "terminal.text",
        border: "1px solid",
        borderColor: "terminal.border",
      },
    },
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
          background: "terminal.overlay",
          borderBottom: "1px solid",
          borderColor: "terminal.border !important",
          _light: {
            background: "#f3f5f8",
            color: "gray.600",
            borderColor: "light-border !important",
          },
        },
        td: {
          px: "3",
          py: "2",
          fontSize: "sm",
          transition: "background .1s ease-out",
          borderBottom: "1px solid",
          borderColor: "terminal.border !important",
          _light: { borderColor: "light-border !important" },
        },
        tr: {
          "&.interactive": {
            cursor: "pointer",
            _hover: {
              "& > td": {
                bg: "terminal.overlay",
                _light: { bg: "gray.100" },
              },
            },
          },
        },
      },
    },
  },
});

export default theme;
