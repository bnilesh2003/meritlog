# worklog-skill

A Claude skill that keeps an evidence-based, confidentiality-safe log of your work and turns it into resume bullets (XYZ, CAR), STAR interview stories, or a profile summary.

**To install, tell any Claude Code session:** "Install the skill from <this repo>". It follows [INSTALL.md](INSTALL.md), sets itself up, and is ready to use as `/worklog`.

## What it does

- **extract**: reads your Claude chats one month at a time and records only what they say you did. No invented results or metrics.
- **compile**: turns the log into resume text; missing numbers become `[NEEDS METRIC: …]` questions for you.
- **Confidentiality by default**: entries are written to pass the "would I say this in an interview at a competitor?" test. While reading your chats, Claude collects every sensitive name it meets (customers, colleagues, codenames, hostnames) into a private blocklist, and a validator refuses any log or output that contains one. Nothing about what's sensitive is hard-coded.

## Layout

```
INSTALL.md            steps for the installing agent
install.sh            install/update · --zip for claude.ai · --uninstall
skills/worklog/       the skill (SKILL.md, references/, scripts/worklog.py)
tests/                uv run tests/test_worklog.py
```

Your data is **not** in this repo: it lives in `~/worklog` (`$WORKLOG_HOME`): `config.yaml` (themes + private blocklist, maintained by Claude), `logs/`, `out/`.

## Updating

`/worklog update`, or `git pull && ./install.sh`. Your data home is never touched.
