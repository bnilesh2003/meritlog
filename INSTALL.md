# Install instructions (for the Claude session doing the install)

The user asked you to install this skill. Do this, in order, with no other changes to their system:

1. **Get the repo.** If you were given a URL, `git clone` it to a stable place (ask the user where; suggest `~/code/worklog-skill`). Updates pull from that path, so don't use a temp dir.
2. **Run the installer** from the repo root: `./install.sh`
   - If it says `uv is required`, ask the user before installing uv (`brew install uv`), then re-run.
   - It copies `skills/worklog` to `~/.claude/skills/worklog` and creates the data home `~/worklog` (`config.yaml`, `logs/`, `out/`). It never overwrites existing data.
3. **Run setup now.** Read `~/.claude/skills/worklog/SKILL.md` and follow **Mode: setup** (themes + blocked terms interview). Its last step runs `doctor`; it should print no `SETUP NEEDED` lines.
4. **Tell the user**:
   - It's installed. In a new Claude Code session (any folder), `/worklog` runs the next useful step; `/worklog extract 2026-10`, `/worklog compile xyz` and `/worklog update` also work.
   - Their data and private blocklist live in `~/worklog`, outside the repo; never commit it.
   - For claude.ai: run `./install.sh --zip` and upload `dist/worklog.zip` under Settings → Capabilities → Skills (an org admin may need to allow custom skills). A claude.ai chat can't install it by itself.

Verify the install (optional): `uv run tests/test_worklog.py` from the repo root should end with `OK`.
