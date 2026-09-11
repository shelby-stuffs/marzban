# Dashboard theme combiner

The dashboard now ships with four runtime themes: Terminal Green, Glamour Pink, Cyber Violet, and Airy Light.

- Open **Appearance** in the sidebar to switch themes without reloading.
- The selected theme is saved through `GET/PUT /api/admin/preferences` and follows the administrator account.
- A local cache is used only to prevent a flash before account preferences load.
- Shared Chakra and CSS variables style the dashboard; Monaco keeps a dark, readable palette for every theme.

Database migration `themecomb001` creates `admin_preferences`. Run the normal Alembic upgrade during deployment.
