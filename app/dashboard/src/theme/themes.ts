export const THEME_IDS = ["terminal-green", "glamour-pink", "cyber-violet", "airy-light"] as const;
export type ThemeId = (typeof THEME_IDS)[number];

export type ThemeDefinition = {
  id: ThemeId; name: string; description: string; mode: "dark" | "light";
  preview: [string, string, string]; metaColor: string;
};

export const DEFAULT_THEME: ThemeId = "glamour-pink";
export const themes: ThemeDefinition[] = [
  { id: "terminal-green", name: "Terminal Green", description: "Graphite console with phosphor-green accents", mode: "dark", preview: ["#06080b", "#10161a", "#00e08c"], metaColor: "#06080b" },
  { id: "glamour-pink", name: "Glamour Pink", description: "Airy rose glass with soft lilac light", mode: "dark", preview: ["#130a14", "#1d111f", "#f653ad"], metaColor: "#130a14" },
  { id: "cyber-violet", name: "Cyber Violet", description: "Midnight indigo with electric-violet glow", mode: "dark", preview: ["#090817", "#141126", "#9b7cff"], metaColor: "#090817" },
  { id: "airy-light", name: "Airy Light", description: "Clean pearl canvas with calm blue accents", mode: "light", preview: ["#f7f9ff", "#ffffff", "#5577ee"], metaColor: "#f7f9ff" },
];

export const isThemeId = (value: unknown): value is ThemeId =>
  typeof value === "string" && (THEME_IDS as readonly string[]).includes(value);

export const getTheme = (id: ThemeId) => themes.find((item) => item.id === id) ?? themes[1];
