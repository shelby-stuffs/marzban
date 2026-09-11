import { createContext, FC, PropsWithChildren, useContext, useMemo, useState } from "react";
import { fetch } from "service/http";
import { DEFAULT_THEME, getTheme, isThemeId, ThemeId, themes } from "theme/themes";
import { updateThemeColor } from "utils/themeColor";

const STORAGE_KEY = "marzban-dashboard-theme";
type PreferencesResponse = { dashboard_theme: ThemeId };

export const getStoredTheme = (): ThemeId => {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return isThemeId(stored) ? stored : DEFAULT_THEME;
};

export const applyDashboardTheme = (theme: ThemeId) => {
  const definition = getTheme(theme);
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = definition.mode;
  window.localStorage.setItem(STORAGE_KEY, theme);
  updateThemeColor(definition.metaColor);
};

type ThemeContextValue = {
  theme: ThemeId; themes: typeof themes; saving: boolean;
  selectTheme: (theme: ThemeId) => Promise<void>;
  syncAccountTheme: () => Promise<void>;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export const DashboardThemeProvider: FC<PropsWithChildren> = ({ children }) => {
  const [theme, setTheme] = useState<ThemeId>(() => getStoredTheme());
  const [saving, setSaving] = useState(false);

  const setLocalTheme = (next: ThemeId) => { setTheme(next); applyDashboardTheme(next); };

  const syncAccountTheme = async () => {
    const response = await fetch<PreferencesResponse>("/admin/preferences");
    if (isThemeId(response.dashboard_theme)) setLocalTheme(response.dashboard_theme);
  };

  const selectTheme = async (next: ThemeId) => {
    const previous = theme;
    setLocalTheme(next);
    setSaving(true);
    try {
      const response = await fetch<PreferencesResponse>("/admin/preferences", { method: "PUT", body: { dashboard_theme: next } });
      if (isThemeId(response.dashboard_theme)) setLocalTheme(response.dashboard_theme);
    } catch (error) {
      setLocalTheme(previous);
      throw error;
    } finally { setSaving(false); }
  };

  const value = useMemo(() => ({ theme, themes, saving, selectTheme, syncAccountTheme }), [theme, saving]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useDashboardTheme = () => {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useDashboardTheme must be used inside DashboardThemeProvider");
  return value;
};
