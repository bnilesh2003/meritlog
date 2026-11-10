# Install instructions (for the Claude session doing the install)

The user asked you to install this skill. Do this, in order, with no other changes to their system:

1. **Get the repo.** If you were given a URL, `git clone` it to a stable place (ask the user where; suggest `~/code/meritlog`). Updates pull from that path, so don't use a temp dir.
2. **Run the installer** from the repo root: `./install.sh`
   - If it says `uv is required`, ask the user before installing uv (`brew install uv`), then re-run.
   - It copies `skills/meritlog` to `~/.claude/skills/meritlog` and creates the data home `~/meritlog` (`config.yaml`, `logs/`, `out/`). It never overwrites existing data.
3. **Nothing to configure.** The installer's `doctor` output should show no `SETUP NEEDED` lines. Themes and the private blocklist are built by the skill itself on the first `/meritlog extract`.
4. **Tell the user**:
   - It's installed. In a new Claude Code session (any folder), `/meritlog` runs the next useful step; `/meritlog extract 2026-10`, `/meritlog compile xyz` and `/meritlog update` also work.
   - Their data and private blocklist live in `~/meritlog`, outside the repo; never commit it.
   - For claude.ai: run `./install.sh --zip` and upload `dist/meritlog.zip` under Settings → Capabilities → Skills (an org admin may need to allow custom skills). A claude.ai chat can't install it by itself.

Verify the install (optional): `uv run tests/test_meritlog.py` from the repo root should end with `OK`.
