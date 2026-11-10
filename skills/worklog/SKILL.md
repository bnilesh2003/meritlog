---
name: worklog
description: Build and use an evidence-based, confidentiality-safe work log for resume writing. Use when the user asks to set up, extract/log/record the work they did (from Claude chat history, Claude Code sessions, or a claude.ai data export), compile/turn their work log into resume bullets, STAR stories or summaries (XYZ, CAR, STAR), or update/check the worklog skill itself.
argument-hint: "setup | extract [YYYY-MM | from..to] | compile [xyz|car|star|summary|all] [job description] | status | update"
---

# Worklog

| Mode | What it does |
|------|--------------|
| **setup** | One-time interview: themes + private blocklist. Runs automatically when needed. |
| **extract** | Reads chats for a window (default: the next uncovered month) → `logs/worklog-YYYY-MM.md` |
| **compile** | Turns the log into resume text with a strategy → `out/<strategy>-YYYY-MM-DD.md` |
| **status** | Shows coverage, what's due, follow-ups |
| **update** | Pulls the latest skill from its repo and reinstalls |

`<skill>` = this skill's directory. `WL` = `uv run <skill>/scripts/worklog.py`.
The user's data lives in the **data home** (`$WORKLOG_HOME`, default `~/worklog`): `config.yaml`, `logs/`, `out/`. Never write user data inside `<skill>`.

## Step 0, every invocation

Run `WL doctor`. It prints the data home, setup state, and `next to extract`.
- `uv` missing → tell the user to install it (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`), with their OK, then continue.
- Any `SETUP NEEDED` line → do **setup** first, then the requested mode.
- No arguments given → do the most useful next thing: setup if needed, else extract `next to extract`, else status.

## Non-negotiable: confidentiality by default

Read `references/safety.md` **before** writing anything in any mode. Every entry must pass the competitor interview test: would the user comfortably say this, out loud, in an interview at a competitor? If not, generalize it; if it can't be generalized safely, leave it out and add 1 to that file's `omitted`. Never ask the user to paste internal details "for context".

## Mode: setup

1. `WL init` (safe to re-run; never overwrites config).
2. Ask, in one message:
   - Their role and main areas → propose 6-10 **themes**; let them edit.
   - **Blocked terms**: customer/partner names, internal product codenames, internal domains, repo/service names, ticket prefixes. Explain these never leave the machine and make every command refuse output that contains them. The employer's own name is fine on a resume; don't block it unless asked.
3. Write both into `<home>/config.yaml` (YAML lists). Don't echo the blocked terms back in chat beyond a count.
4. `WL doctor` → no `SETUP NEEDED` lines. Ask which month their work history should start from, if extracting next.

## Mode: extract

1. **Window**: the argument, else `next to extract` from doctor. Do one calendar month per file; for a range, loop month by month.
2. **Source**, in this order of preference:
   - A **claude.ai data export** (`conversations.json`) the user points to → filter by message timestamps. Full coverage.
   - In **Claude Code** → `~/.claude/projects/**/*.jsonl`, records whose `timestamp` falls in the window. Read user messages and assistant text; skip tool-output blobs.
   - In **claude.ai** with past-chat tools → list chats by date in the window, then keyword-search for misses. Open each.
   - None available → say so and stop. Never reconstruct work from memory.
3. **Prior state**: if logs exist, `WL compile` and read `<home>/out/current.md` header + manifest (`next_id`, existing ids). Else start at `WL-0001`.
4. **Extract** in the format of `references/schema.md`, using only themes from config:
   - Only what the source explicitly states. No outcome → `result: not stated`. Never invent metrics.
   - The user's actions ≠ your suggestions. Unclear if they acted → `EXPLORED`. "We did X" → `my_role: contributed` unless they said they owned/led it.
   - Continuing an existing id → `op: update`, same id, FULL entry. New work → `op: create`.
   - Skip trivial lookups. Apply safety rules **while** writing.
5. **Write** `<home>/logs/worklog-YYYY-MM.md` with an honest header: `chats_read` = conversations actually opened, `coverage_gaps`, `omitted`.
6. **Gate**: `WL validate`. Fix every ERROR (SENSITIVE included; generalize the text, don't weaken config) and re-run until it passes.
7. **Report**: entries created/updated, coverage gaps, number omitted, the 3 most useful `open_questions`, and anything from `WL due`.

## Mode: compile

1. `WL compile`, then read `<home>/out/current.md` (current state, newest version of each entry).
2. Read `references/strategies.md`; apply the strategy (default `xyz`).
3. **Evidence rules**: bullets only from `CONFIRMED`; `IN_PROGRESS` → "leading/driving" wording; `EXPLORED` → skills context only. Only numbers in `metrics`/`scope`; otherwise `[NEEDS METRIC: <question>]`, never estimate. Every bullet ends with its ids, e.g. `[WL-0012]`.
4. Job description given → rank by relevance; mirror its terms only where an entry genuinely supports them; list unsupported requirements as gaps.
5. Write `<home>/out/<strategy>-YYYY-MM-DD.md`, then `WL scan` it and fix findings. Then do the manual safety pass (combined entries can reveal more than single ones).
6. List the `NEEDS METRIC` questions for the user.

## Mode: status

`WL doctor` and `WL due`; summarize coverage, gaps in months, entries by status, follow-ups due.

## Mode: update

Read `<skill>/.installed-from`; it holds the repo path. Run `git -C <repo> pull --ff-only`, then `<repo>/install.sh`. Report the old and new commit. User data is untouched by design.

## claude.ai (no filesystem)

No data home persists. At the start, ask the user to attach their latest `current.md` (and `config.yaml` if they're comfortable; otherwise ask for themes and blocked terms in chat). Return new files as downloads, and tell them to save them into their data home. If code execution is available, run the script on the uploaded files; otherwise apply the safety checklist by hand and say so.
