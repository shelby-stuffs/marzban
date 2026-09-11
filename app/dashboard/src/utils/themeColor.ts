export const updateThemeColor = (color = "#130a14") => {
  const el = document.querySelector('meta[name="theme-color"]');
  el?.setAttribute("content", color);
};
