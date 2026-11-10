---
name: meritlog
description: Build and use an evidence-based, confidentiality-safe work log for resume writing. Use when the user asks to set up, extract/log/record the work they did (from Claude chat history, Claude Code sessions, or a claude.ai data export), compile/turn their work log into resume bullets, STAR stories or summaries (XYZ, CAR, STAR), or update/check the meritlog skill itself.
argument-hint: "setup | extract [YYYY-MM | from..to] | compile [xyz|car|star|summary|all] [job description] | status | update"
---

# Meritlog

| Mode | What it does |
|------|--------------|
| **setup** | Creates the data home. Runs automatically when needed; asks the user nothing. |
| **extract** | Reads chats for a window (default: the next uncovered month) → `logs/meritlog-YYYY-MM.md` |
| **compile** | Turns the log into resume text with a strategy → `out/<strategy>-YYYY-MM-DD.md` |
| **status** | Shows coverage, what's due, follow-ups |
| **update** | Pulls the latest skill from its repo and reinstalls |

`<skill>` = this skill's directory. `ML` = `uv run <skill>/scripts/meritlog.py`.
The user's data lives in the **data home** (`$MERITLOG_HOME`, default `~/meritlog`): `config.yaml`, `logs/`, `out/`. Never write user data inside `<skill>`.

## Step 0, every invocation

Run `ML doctor`. It prints the data home, setup state, and `next to extract`.
- `uv` missing → tell the user to install it (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`), with their OK, then continue.
- Any `SETUP NEEDED` line → run `ML init`, then the requested mode.
- No arguments given → do the most useful next thing: setup if needed, else extract `next to extract`, else status.

## Non-negotiable: confidentiality by default

Read `references/safety.md` **before** writing anything in any mode. Every entry must pass the competitor interview test: would the user comfortably say this, out loud, in an interview at a competitor? If not, generalize it; if it can't be generalized safely, leave it out and add 1 to that file's `omitted`. Never ask the user to paste internal details "for context".

## Mode: setup

`ML init` (safe to re-run; never overwrites config). Nothing is asked up front: themes and the blocklist are built by you during extract. If no logs exist yet, ask only which month their work history should start from.

## Config is yours to maintain

`<home>/config.yaml` has two lists that you keep current; the script just enforces them.
- **blocked_terms**: every sensitive name you meet while reading, as it actually appeared: customer and partner names, colleagues' names and handles, internal product or project codenames, hostnames, internal domains and URLs, repo/service/cluster names, ticket-key prefixes (e.g. `SEC-`), Slack channels. Add them **before** writing entries, so the validator catches any that slip through. Never add secrets, keys or tokens (that would store them); just never write them anywhere. The employer's own name and public tech (AWS, Kubernetes…) are not blocked. Mention only the count of new terms in chat, never the terms.
- **themes**: if empty, derive 6-10 from the work you find (e.g. "Application Security", "Cloud Security", "Detection & Response"). Reuse them every month; add one only when work clearly fits none, and say so in the report.

## Mode: extract

1. **Window**: the argument, else `next to extract` from doctor. Do one calendar month per file; for a range, loop month by month.
2. **Source**, in this order of preference:
   - A **claude.ai data export** (`conversations.json`) the user points to → filter by message timestamps. Full coverage.
   - In **Claude Code** → `~/.claude/projects/**/*.jsonl`, records whose `timestamp` falls in the window. Read user messages and assistant text; skip tool-output blobs.
   - In **claude.ai** with past-chat tools → list chats by date in the window, then keyword-search for misses. Open each.
   - None available → say so and stop. Never reconstruct work from memory.
3. **Prior state**: if logs exist, `ML compile` and read `<home>/out/current.md` header + manifest (`next_id`, existing ids). Else start at `ML-0001`.
4. **Update config** (see above): add new sensitive names to `blocked_terms`, fill `themes` if empty.
5. **Extract** in the format of `references/schema.md`, using only themes from config:
   - Only what the source explicitly states. No outcome → `result: not stated`. Never invent metrics.
   - The user's actions ≠ your suggestions. Unclear if they acted → `EXPLORED`. "We did X" → `my_role: contributed` unless they said they owned/led it.
   - Continuing an existing id → `op: update`, same id, FULL entry. New work → `op: create`.
   - Skip trivial lookups. Apply safety rules **while** writing.
6. **Write** `<home>/logs/meritlog-YYYY-MM.md` with an honest header: `chats_read` = conversations actually opened, `coverage_gaps`, `omitted`.
7. **Gate**: `ML validate`. Fix every ERROR (SENSITIVE included; generalize the text, never remove a term from config to make it pass) and re-run until it passes. Then re-read the file yourself against `references/safety.md`: the blocklist only catches names, not descriptions of weaknesses or architecture.
8. **Report**: entries created/updated, themes used or added, count of new blocked terms, coverage gaps, number omitted, the 3 most useful `open_questions`, and anything from `ML due`.

## Mode: compile

1. `ML compile`, then read `<home>/out/current.md` (current state, newest version of each entry).
2. Read `references/strategies.md`; apply the strategy (default `xyz`).
3. **Evidence rules**: bullets only from `CONFIRMED`; `IN_PROGRESS` → "leading/driving" wording; `EXPLORED` → skills context only. Only numbers in `metrics`/`scope`; otherwise `[NEEDS METRIC: <question>]`, never estimate. Every bullet ends with its ids, e.g. `[ML-0012]`.
4. Job description given → rank by relevance; mirror its terms only where an entry genuinely supports them; list unsupported requirements as gaps.
5. Write `<home>/out/<strategy>-YYYY-MM-DD.md`, then `ML scan` it and fix findings. Then do the manual safety pass (combined entries can reveal more than single ones).
6. List the `NEEDS METRIC` questions for the user.

## Mode: status

`ML doctor` and `ML due`; summarize coverage, gaps in months, entries by status, follow-ups due.

## Mode: update

Read `<skill>/.installed-from`; it holds the repo path. Run `git -C <repo> pull --ff-only`, then `<repo>/install.sh`. Report the old and new commit. User data is untouched by design.

## claude.ai (no filesystem)

No data home persists. At the start, ask the user to attach their latest `current.md` and `config.yaml` if they have them; otherwise build both from the chats as above. Return new files as downloads, and tell them to save them into their data home. If code execution is available, run the script on the uploaded files; otherwise apply the safety checklist by hand and say so.
