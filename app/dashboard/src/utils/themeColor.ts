// The dashboard ships with a single dark theme, so the browser theme color is
// constant. Kept as a function to preserve the existing call site.
export const updateThemeColor = () => {
  const el = document.querySelector('meta[name="theme-color"]');
  el?.setAttribute("content", "#06080b");
};
