**Step 5 — Commit all file changes directly to `main`**

All files changed in Routine 2 are `.tsv` files. Per the repo commit policy, TSV files
are non-executable and commit directly to `main` — no PR is needed or appropriate,
regardless of how many files are touched together.

Use `push_files` to commit all changed files in a single commit to `main`:

- `live_shows_current.tsv` — row updated: `Status` → `attended`, spending filled,
  `Setlist.fm URL` filled, `Notes / Memories` filled, `Artist Interaction` filled
- `artists.tsv` — always included; apply counting policy below
- `autograph_books_combined.tsv` — `RHBS Signed` / `APS Signed` set to `Yes`
  and/or `Hat Notes` updated if applicable (omit file if no change)

Note: `spending.tsv` is already committed directly to `main` in Step 3 — do not
include it again here.

Commit message format: `post-show: [Artist] [YYYY-MM-DD]`

**If the commit fails:** present each changed file in the conversation for
download and manual check-in.

