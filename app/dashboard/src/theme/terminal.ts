// Shared terminal component layer. Keep layout and application behavior local.
const mono = '"JetBrains Mono","SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace';
const sans = 'Manrope,Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif';
const bg = "#130a14";
const surface = "#1d111f";
const overlay = "#2a182d";
const border = "#593653";
const controlBorder = "#80506f";
const text = "#ffe9f6";
const muted = "#c892af";
const focus = { boxShadow: "0 0 0 3px rgba(246,83,173,.28)", outline: "none" };

type SchemeProps = { colorScheme?: string };
const tones: Record<string, { ink: string; fill: string; hover: string; tint: string }> = {
  primary: { ink: "#ff96d2", fill: "#f653ad", hover: "#ff72c2", tint: "#3a1931" },
  red: { ink: "#ff8ca6", fill: "#ff6688", hover: "#ff9caf", tint: "#3a1825" },
  orange: { ink: "#ffc08e", fill: "#f5a66d", hover: "#ffd1aa", tint: "#392319" },
  yellow: { ink: "#ffe29a", fill: "#e7bd61", hover: "#ffedb8", tint: "#372d19" },
  blue: { ink: "#d4b4ff", fill: "#bd91ff", hover: "#e3ceff", tint: "#291d3b" },
  gray: { ink: text, fill: "#dca9c3", hover: "#ffe9f6", tint: overlay },
};
const tone = ({ colorScheme = "primary" }: SchemeProps) =>
  tones[colorScheme === "green" || colorScheme === "teal" ? "primary" : colorScheme] || tones.gray;

// Chakra's outline variants contain _dark overrides. Override that layer too;
// baseStyle alone cannot reliably replace the stock component variants.
const field = {
  bg: surface, color: text, borderColor: controlBorder, borderRadius: "12px",
  fontFamily: sans,
  _placeholder: { color: muted },
  _hover: { borderColor: muted },
  _focus: { borderColor: "primary.500", boxShadow: "0 0 0 2px rgba(246,83,173,.38)" },
  _focusVisible: { borderColor: "primary.500", boxShadow: "0 0 0 2px rgba(246,83,173,.38)" },
  _invalid: { borderColor: "#ff8794", boxShadow: "0 0 0 1px #ff8794" },
  _disabled: { bg: overlay, color: muted, opacity: 0.6, cursor: "not-allowed" },
};
const outlinedField = { ...field, _dark: field };
const buttonVariant = (variant: "solid" | "outline" | "ghost", props: SchemeProps) => {
  const c = tone(props);
  const style = {
    bg: variant === "solid" ? c.fill : "transparent",
    color: variant === "solid" ? bg : c.ink,
    border: variant === "outline" ? "1px solid" : "1px solid transparent",
    borderColor: variant === "outline" ? (props.colorScheme === "red" ? c.ink : controlBorder) : "transparent",
    _hover: { bg: variant === "solid" ? c.hover : c.tint, color: variant === "solid" ? bg : c.ink,
      _disabled: { bg: variant === "solid" ? c.fill : "transparent" } },
    _active: { bg: variant === "solid" ? c.fill : c.tint },
    _focusVisible: focus,
    _disabled: { opacity: 0.4, cursor: "not-allowed", boxShadow: "none" },
  };
  return { ...style, _dark: style };
};

export const terminalTheme = {
  fonts: { body: sans, heading: sans, mono },
  colors: { terminal: { dim: muted }, gray: { 400: muted, 500: "#a87592" } },
  styles: { global: {
    body: { fontFamily: sans },
    "*::placeholder": { color: muted, opacity: 1 },
    "a:focus-visible, summary:focus-visible": focus,
    "@media (max-width: 48em)": {
      ".chakra-input, .chakra-select, .chakra-button, .chakra-tabs__tab, .chakra-accordion__button, .chakra-modal__close-btn": { minH: "44px" },
      ".chakra-button, .chakra-modal__close-btn": { minW: "44px" },
      ".chakra-checkbox, .chakra-radio, .chakra-switch": { minH: "44px" },
      ".chakra-modal__content": { width: "calc(100% - 24px)", marginInline: "12px" },
    },
    "@media (prefers-reduced-motion: reduce)": {
      "*, *::before, *::after": { animationDuration: "0.01ms !important", animationIterationCount: "1 !important", transitionDuration: "0.01ms !important", scrollBehavior: "auto !important" },
    },
  } },
  components: {
    Button: { variants: {
      solid: (props: SchemeProps) => buttonVariant("solid", props),
      outline: (props: SchemeProps) => buttonVariant("outline", props),
      ghost: (props: SchemeProps) => buttonVariant("ghost", props),
      link: (props: SchemeProps) => ({ color: tone(props).ink, _focusVisible: focus }),
    } },
    Input: { variants: {
      outline: { field: outlinedField, addon: { bg: overlay, color: muted, borderColor: controlBorder } },
      filled: { field: outlinedField },
    } },
    Select: { variants: { outline: { field: outlinedField }, filled: { field: outlinedField } } },
    NumberInput: { variants: { outline: { field: outlinedField } } },
    Textarea: { variants: { outline: outlinedField, filled: outlinedField } },
    Form: { baseStyle: { helperText: { color: muted, fontSize: "sm" } } },
    FormLabel: { baseStyle: { color: muted, fontSize: "xs", lineHeight: 1.5 } },
    FormError: { baseStyle: { text: { color: "#ff8794", fontSize: "sm" }, icon: { color: "#ff8794" } } },
    Accordion: { baseStyle: {
      container: { borderColor: border, bg: surface, color: text },
      button: { fontFamily: sans, minH: "40px", _hover: { bg: overlay }, _expanded: { bg: overlay, color: "primary.300" }, _focusVisible: focus },
      panel: { bg: surface, pt: 3, pb: 4 },
      icon: { color: muted },
    } },
    Checkbox: { baseStyle: { control: { borderColor: controlBorder, _focusVisible: focus }, label: { fontFamily: sans, color: text } } },
    Radio: { defaultProps: { colorScheme: "primary" }, baseStyle: { control: { borderColor: controlBorder, _focusVisible: focus }, label: { fontFamily: sans } } },
    Switch: { baseStyle: { track: { bg: "#566b83", _dark: { bg: "#566b83", _checked: { bg: "primary.500" } }, _checked: { bg: "primary.500" }, _focusVisible: focus }, thumb: { bg: text } } },
    Tabs: {
      baseStyle: { tablist: { overflowX: "auto", flexWrap: "nowrap" }, tab: { flexShrink: 0, whiteSpace: "nowrap", _focusVisible: focus } },
      variants: {
        line: { tablist: { borderColor: border }, tab: { color: muted, _selected: { color: "primary.300", borderColor: "primary.500" }, _dark: { _selected: { color: "primary.300", borderColor: "primary.500" } } } },
        "soft-rounded": { tab: { borderRadius: "999px", color: muted, _selected: { bg: tones.primary.tint, color: tones.primary.ink } } },
      },
    },
    Card: { baseStyle: { container: { bg: surface, border: "1px solid", borderColor: border, borderRadius: "16px", backdropFilter: "blur(18px)" } }, variants: { elevated: { container: { bg: surface, boxShadow: "none" } }, outline: { container: { bg: surface, borderColor: border } } } },
    Modal: { baseStyle: {
      dialog: { bg: surface, color: text, borderRadius: "18px", border: "1px solid", borderColor: border, boxShadow: "panel", maxW: "calc(100vw - 32px)", _dark: { bg: surface } },
      header: { bg: overlay, pr: 12, overflowWrap: "anywhere" },
      body: { minW: 0, overflowWrap: "anywhere" },
      footer: { bg: overlay, flexWrap: "wrap", gap: 2 },
      closeButton: { color: muted, _focusVisible: focus },
    } },
    Drawer: { baseStyle: {
      dialog: { bg: surface, color: text, _dark: { bg: surface } },
      header: { bg: overlay, borderBottom: "1px solid", borderColor: border, fontFamily: mono },
      footer: { bg: overlay, borderTop: "1px solid", borderColor: border, flexWrap: "wrap", gap: 2 },
      closeButton: { color: muted, _focusVisible: focus },
    } },
    Popover: { baseStyle: {
      content: { bg: overlay, color: text, maxW: "calc(100vw - 32px)", _dark: { bg: overlay }, _focusVisible: focus },
      header: { borderColor: border, fontFamily: mono }, footer: { borderColor: border },
    } },
    Menu: { baseStyle: {
      list: { bg: overlay, color: text, maxW: "calc(100vw - 24px)", _dark: { bg: overlay } },
      item: { _dark: { bg: "transparent", _focus: { bg: surface }, _hover: { bg: surface } } },
      divider: { borderColor: border }, groupTitle: { color: muted, fontFamily: mono },
    } },
    Progress: { defaultProps: { colorScheme: "primary" }, baseStyle: { track: { bg: overlay, borderRadius: "2px" }, filledTrack: { bg: "primary.500" } } },
    Skeleton: { baseStyle: { startColor: surface, endColor: overlay } },
    Alert: { variants: { subtle: ({ status }: { status?: string }) => {
      const c = tones[status === "error" ? "red" : status === "warning" ? "orange" : status === "success" ? "primary" : "blue"];
      return { container: { bg: c.tint, color: text, borderLeftColor: c.ink, _dark: { bg: c.tint } }, icon: { color: c.ink }, title: { fontFamily: mono } };
    } } },
  },
};
