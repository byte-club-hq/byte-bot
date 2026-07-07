[DECISIONS]
- 2026-07-07T00:00Z [CODE] File-backed SQLite is the only supported persistence target; URI handling was removed.

[PROGRESS]
- 2026-07-07T00:00Z [CODE] Removed SQLite URI handling and `:memory:` special casing from `DatabaseService`.

[OUTCOMES]
- 2026-07-07T00:00Z [CODE] Tests now use temp file-backed SQLite only; runtime behavior matches file-path persistence only.
