# Tool Guidelines

- Read MEMORY.md at the start of each conversation to load the current list.
- Use Read/Write/Edit for managing the grocery list in MEMORY.md and archiving to HISTORY.md.
- Use Edit to update individual items. Use Write only when rewriting the full list.
- Use Bash to run SQLite commands against `~/.caveclaw/caveclaw.db` for logging and analysis.
- Ensure the `grocery_log` table exists before first use (CREATE TABLE IF NOT EXISTS).
- Do not use WebSearch or other tools unless the user explicitly asks.
