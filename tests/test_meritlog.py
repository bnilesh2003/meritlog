# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = ["pyyaml>=6"]
# ///
"""Tests for the meritlog skill script, synthetic fixtures only.
Run from the repo root:  uv run tests/test_meritlog.py"""
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "meritlog" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import meritlog  # noqa: E402

ENTRY = """\
### {id}: {title}
```yaml
id: {id}
op: {op}
title: {title}
theme: AppSec
category: project
source: [claude_chat]
period: {{ start: 2026-01, end: {end} }}
status: {status}
my_role: owned
context: Synthetic context.
actions:
  - Did a synthetic thing.
result: {result}
metrics: []
evidence: user stated
follow_up_after: {fu}
updated: 2026-01-20
```
"""


def make_file(window, next_id, manifest_rows, entries, chats_read=5):
    rows = "\n".join(f"| {i} | t | AppSec | project | {s} | 2026-01-20 |" for i, s in manifest_rows)
    return f"""---
schema: meritlog/v1
window: {{ from: {window[0]}, to: {window[1]} }}
generated_on: 2026-02-01
next_id: {next_id}
chats_read: {chats_read}
coverage_gaps: []
---

## Manifest
| id | title | theme | category | status | last_updated |
|----|-------|-------|----------|--------|--------------|
{rows}

## Entries

{"".join(entries)}"""


def entry(id, op="create", title="Thing", status="IN_PROGRESS", end="ongoing",
          result="not stated", fu="null"):
    return ENTRY.format(id=id, op=op, title=title, status=status, end=end, result=result, fu=fu)


JAN = ("2026-01-01", "2026-01-31")
FEB = ("2026-02-01", "2026-02-28")


class MeritlogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.home = self.dir / "home"  # data home; logs fixtures live in self.dir

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        (self.dir / name).write_text(text)

    def run_cli(self, *args):
        return meritlog.main(["--home", str(self.home), *args])

    def cfg(self):
        return meritlog.load_config(self.home, meritlog.Report())

    def set_config(self, text):
        self.home.mkdir(exist_ok=True)
        (self.home / "config.yaml").write_text(text)

    def good_pair(self):
        self.write("meritlog-2026-01.md", make_file(
            JAN, "ML-0003", [("ML-0001", "IN_PROGRESS"), ("ML-0002", "EXPLORED")],
            [entry("ML-0001", fu="2026-02"), entry("ML-0002", status="EXPLORED", title="Other")]))
        self.write("meritlog-2026-02.md", make_file(
            FEB, "ML-0004",
            [("ML-0001", "CONFIRMED"), ("ML-0002", "EXPLORED"), ("ML-0003", "CONFIRMED")],
            [entry("ML-0001", op="update", status="CONFIRMED", end="2026-02",
                   result="Rolled out", fu="2026-02"),
             entry("ML-0003", status="CONFIRMED", title="New", result="Done")]))

    # ---- happy path ------------------------------------------------------
    def test_valid_pair_passes_and_latest_wins(self):
        self.good_pair()
        self.assertEqual(self.run_cli("validate", str(self.dir)), 0)
        _, state, rep = meritlog.load_all([str(self.dir)], self.cfg())
        self.assertEqual(rep.errors, [])
        self.assertEqual(state["ML-0001"]["status"], "CONFIRMED")
        self.assertEqual(len(state), 3)

    def test_compile_output_revalidates(self):
        self.good_pair()
        out = self.dir / "out" / "current.md"
        out.parent.mkdir()
        self.assertEqual(self.run_cli("compile", str(self.dir), "-o", str(out)), 0)
        text = out.read_text()
        self.assertIn("next_id: ML-0004", text)
        self.assertIn("| ML-0003 |", text)
        # regression: the snapshot must itself be a valid log (no dangling op: update)
        self.assertNotIn("op: update", text)
        self.assertEqual(self.run_cli("validate", str(out)), 0)

    def test_compiled_mixed_with_monthly_is_error(self):
        self.good_pair()
        out = self.dir / "meritlog-zz-compiled.md"
        self.assertEqual(self.run_cli("compile", str(self.dir), "-o", str(out)), 0)
        self.assertErrors("compiled snapshot mixed")

    # ---- failure modes the LLM is likely to produce ------------------------
    def assertErrors(self, needle):
        _, _, rep = meritlog.load_all([str(self.dir)], self.cfg())
        self.assertTrue(any(needle in e for e in rep.errors),
                        f"expected error containing {needle!r}, got {rep.errors}")

    def test_create_of_existing_id(self):
        self.good_pair()
        p = self.dir / "meritlog-2026-02.md"
        p.write_text(p.read_text().replace("op: update", "op: create"))
        self.assertErrors("already exists")

    def test_update_of_unknown_id(self):
        self.write("meritlog-2026-01.md", make_file(
            JAN, "ML-0002", [("ML-0001", "IN_PROGRESS")], [entry("ML-0001", op="update")]))
        self.assertErrors("never created")

    def test_manifest_dropped_row(self):
        self.good_pair()
        p = self.dir / "meritlog-2026-02.md"
        p.write_text(p.read_text().replace("| ML-0002 | t | AppSec | project | EXPLORED | 2026-01-20 |\n", ""))
        self.assertErrors("manifest is missing ML-0002")

    def test_manifest_status_drift(self):
        self.good_pair()
        p = self.dir / "meritlog-2026-02.md"
        p.write_text(p.read_text().replace("| ML-0003 | t | AppSec | project | CONFIRMED",
                                           "| ML-0003 | t | AppSec | project | IN_PROGRESS"))
        self.assertErrors("disagrees")

    def test_wrong_next_id(self):
        self.write("meritlog-2026-01.md", make_file(
            JAN, "ML-0009", [("ML-0001", "IN_PROGRESS")], [entry("ML-0001")]))
        self.assertErrors("expected ML-0002")

    def test_unresolved_session_end(self):
        self.write("meritlog-2026-01.md", make_file(
            JAN, "ML-0001", [], [entry("ML-TBD")]))
        self.assertErrors("unresolved session-end")

    def test_bad_enum(self):
        self.write("meritlog-2026-01.md", make_file(
            JAN, "ML-0002", [("ML-0001", "DONE")], [entry("ML-0001", status="DONE")]))
        self.assertErrors("status='DONE'")

    def test_window_gap_is_warning(self):
        self.good_pair()
        p = self.dir / "meritlog-2026-02.md"
        p.write_text(p.read_text().replace("from: 2026-02-01", "from: 2026-02-10"))
        _, _, rep = meritlog.load_all([str(self.dir)], self.cfg())
        self.assertTrue(any("window gap" in w for w in rep.warnings))

    def test_research_sources_are_valid(self):
        self.write("meritlog-2026-01.md", make_file(
            JAN, "ML-0002", [("ML-0001", "IN_PROGRESS")],
            [entry("ML-0001").replace("source: [claude_chat]",
                                      "source: [claude_chat, git, connector, local_file]")]))
        _, _, rep = meritlog.load_all([str(self.dir)], self.cfg())
        self.assertEqual(rep.errors, [])

    def test_due_lists_followups(self):
        self.good_pair()
        _, state, _ = meritlog.load_all([str(self.dir)], self.cfg())
        self.assertEqual(state["ML-0001"]["follow_up_after"], "2026-02")

    # ---- safety by default -------------------------------------------------
    def leak(self):
        self.good_pair()
        self.set_config("blocked_terms: [Acme Bank]\n")
        p = self.dir / "meritlog-2026-02.md"
        p.write_text(p.read_text().replace("Rolled out", "Rolled out for acme bank"))

    def test_validate_fails_on_sensitive_hit(self):
        self.leak()
        self.assertErrors("blocked term")
        self.assertEqual(self.run_cli("validate", str(self.dir)), 1)

    def test_compile_refuses_to_write_on_sensitive_hit(self):
        self.leak()
        out = self.dir / "c.md"
        self.assertEqual(self.run_cli("compile", str(self.dir), "-o", str(out)), 1)
        self.assertFalse(out.exists())

    def test_scan_free_text(self):
        self.set_config("blocked_terms: [bastion-07]\n")
        clean, dirty = self.dir / "clean.md", self.dir / "dirty.md"
        clean.write_text("- Reduced triage time ~50% across ~40 services [ML-0001]\n")
        dirty.write_text("- Hardened BASTION-07 access [ML-0002]\n")
        self.assertEqual(self.run_cli("scan", str(clean)), 0)
        self.assertEqual(self.run_cli("scan", str(dirty)), 1)

    # ---- data home + private config ---------------------------------------
    def test_init_creates_home_and_keeps_config(self):
        self.assertEqual(self.run_cli("init"), 0)
        for d in ("logs", "out", "config.yaml"):
            self.assertTrue((self.home / d).exists(), d)
        (self.home / "config.yaml").write_text("themes: [AppSec]\n")
        self.run_cli("init")
        self.assertEqual((self.home / "config.yaml").read_text(), "themes: [AppSec]\n")

    def test_default_paths_use_home(self):
        self.good_pair()
        self.run_cli("init")
        for f in self.dir.glob("meritlog-*.md"):
            f.rename(self.home / "logs" / f.name)
        self.assertEqual(self.run_cli("validate"), 0)
        self.assertEqual(self.run_cli("compile"), 0)
        self.assertTrue((self.home / "out" / "current.md").exists())

    def test_blocked_term_is_whole_word_and_case_insensitive(self):
        self.set_config("blocked_terms: [Falcon]\n")
        hit, miss = self.dir / "hit.md", self.dir / "miss.md"
        hit.write_text("- Launched project falcon securely\n")
        miss.write_text("- Studied falconry\n")
        self.assertEqual(self.run_cli("scan", str(hit)), 1)
        self.assertEqual(self.run_cli("scan", str(miss)), 0)

    def test_blocked_term_fails_validate(self):
        self.good_pair()
        self.set_config("blocked_terms: [Rolled out]\n")
        self.assertEqual(self.run_cli("validate", str(self.dir)), 1)

    def test_nothing_blocked_without_config(self):
        f = self.dir / "t.md"
        f.write_text("- Rolled out to 10.2.3.4 for Acme\n")
        self.assertEqual(self.run_cli("scan", str(f)), 0)

    def test_themes_come_from_config(self):
        self.good_pair()
        self.set_config("themes: [Cloud]\n")
        _, _, rep = meritlog.load_all([str(self.dir)], self.cfg())
        self.assertTrue(any("not in THEMES" in w for w in rep.warnings))

    def test_doctor_reports_setup_needed(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.run_cli("doctor")
        self.assertIn("SETUP NEEDED: no config", buf.getvalue())
        self.run_cli("init")  # empty themes/blocklist are fine: Claude fills them
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.run_cli("doctor")
        self.assertNotIn("SETUP NEEDED", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=1)
