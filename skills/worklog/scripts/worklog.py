#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = ["pyyaml>=6"]
# ///
"""Validate, compile and safety-check worklog/v1 files.

Usage (run with uv, no install needed):
  uv run worklog.py init                     # create the data home (safe to re-run)
  uv run worklog.py doctor                   # setup status + what to extract next
  uv run worklog.py validate [files-or-dir...]
  uv run worklog.py compile  [files-or-dir...] [-o out.md]
  uv run worklog.py due      [files-or-dir...] [--today YYYY-MM-DD]
  uv run worklog.py scan     <text-file>...  # e.g. compiled resume bullets

Data home: --home, else $WORKLOG_HOME, else ~/worklog. It holds config.yaml
(themes + your private blocklist), logs/ and out/. Paths default to <home>/logs
and <home>/out/current.md. The skill itself holds no user data, so it can be
reinstalled or updated without touching the log.

Files are processed in order of header `window.from`. Later entries override
earlier ones by id (append-only event log).

Safety by default: validate/compile/due FAIL if any built-in or configured
sensitive pattern matches an entry; scan applies the same patterns to free text.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# ---------------------------------------------------------------- schema ----
ID_RE = re.compile(r"^WL-(\d{4})$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
OPS = {"create", "update"}
CATEGORIES = {"project", "collaboration_mentorship", "design_docs", "org_building",
              "incident_response", "learning", "outside_work"}
SOURCES = {"claude_chat", "claude_code", "user_recalled", "session_end"}
STATUSES = {"CONFIRMED", "IN_PROGRESS", "EXPLORED", "ABANDONED"}
ROLES = {"owned", "led", "contributed", "assisted", "unclear"}
REQUIRED = ["id", "op", "title", "theme", "category", "source", "period", "status",
            "my_role", "context", "actions", "result", "evidence", "updated"]
# Generic patterns that must never appear in a log entry or compiled output,
# whatever the employer. Org-specific terms (customers, codenames, internal
# domains) live in the user's config.yaml, never in this file.
# This is the deterministic backstop to references/safety.md, not a replacement.
Pattern = tuple[str, re.Pattern[str]]
BUILTIN_PATTERNS: list[Pattern] = [
    ("IPv4 address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("AWS ARN", re.compile(r"\barn:aws[a-z-]*:")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,})")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("JWT", re.compile(r"\beyJ[\w-]{10,}\.[\w-]{10,}\.")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("internal hostname", re.compile(r"\b[\w-]+(?:\.[\w-]+)*\.(?:internal|corp|intranet|lan)\b", re.I)),
    ("credential assignment", re.compile(r"\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S{6,}", re.I)),
]

CONFIG_NAME = "config.yaml"
CONFIG_TEMPLATE = """\
# worklog config. PRIVATE: it may list customer names and codenames.
# Never commit or share this file. The skill repo does not contain it.

# 6-10 themes; every entry's `theme` must be one of these.
themes: []
#  - Application Security
#  - Cloud Security

# Plain words or phrases that must never appear in the log (case-insensitive,
# whole-word). Customer/partner names, internal codenames, internal domains,
# repo or service names, ticket-key prefixes like "SEC-".
blocked_terms: []

# Optional regexes for anything a plain term can't express.
sensitive_patterns: []
#  - { label: "Jira key", regex: "\\bSEC-\\d+\\b" }
"""

FENCE_RE = re.compile(r"^```ya?ml\s*\n(.*?)^```", re.M | re.S)
FRONT_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
ROW_RE = re.compile(r"^\|\s*(WL-\d{4})\s*\|(.*)\|\s*$", re.M)


# ----------------------------------------------------------------- model ----
@dataclass
class LogFile:
    path: Path
    header: dict
    entries: list[dict]
    manifest: dict[str, list[str]]  # id -> remaining cells


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"ERROR   {where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"WARN    {where}: {msg}")

    def print(self) -> None:
        for line in self.warnings + self.errors:
            print(line, file=sys.stderr)
        print(f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)", file=sys.stderr)


def norm(v):
    """YAML turns 2026-10-02 into a date; we want strings everywhere."""
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [norm(x) for x in v]
    return v


def id_num(wid: str) -> int:
    m = ID_RE.match(wid or "")
    return int(m.group(1)) if m else -1


def fmt_id(n: int) -> str:
    return f"WL-{n:04d}"


# ---------------------------------------------------------------- parsing ---
def parse_file(path: Path, rep: Report) -> LogFile | None:
    text = path.read_text(encoding="utf-8")
    m = FRONT_RE.match(text)
    if not m:
        rep.err(path.name, "missing YAML front-matter header")
        return None
    try:
        header = norm(yaml.safe_load(m.group(1)) or {})
    except yaml.YAMLError as e:
        rep.err(path.name, f"header is not valid YAML: {e}")
        return None

    body = text[m.end():]
    head_part, _, entries_part = body.partition("## Entries")
    if not entries_part:
        entries_part, head_part = body, ""
    entries = []
    for i, block in enumerate(FENCE_RE.findall(entries_part), 1):
        try:
            data = yaml.safe_load(block)
        except yaml.YAMLError as e:
            rep.err(path.name, f"entry block #{i} is not valid YAML: {e}")
            continue
        if isinstance(data, dict):
            entries.append(norm(data))
        else:
            rep.err(path.name, f"entry block #{i} is not a mapping")

    manifest = {wid: [c.strip() for c in rest.split("|")]
                for wid, rest in ROW_RE.findall(head_part)}
    return LogFile(path, header, entries, manifest)


def expand(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in map(Path, paths):
        out.extend(sorted(p.glob("worklog-*.md")) if p.is_dir() else [p])
    return out


def resolve_home(arg: Path | None) -> Path:
    return (arg or Path(os.environ.get("WORKLOG_HOME") or Path.home() / "worklog")).expanduser()


def compile_user_pattern(label: str, regex: str, rep: Report) -> Pattern | None:
    """Turn one `sensitive_patterns` item from config.yaml into a Pattern.

    Returning None drops the pattern; rep.err makes every command fail.
    """
    # TODO(human): decide what happens when the user's regex is invalid.
    return (label, re.compile(regex, re.I))


@dataclass
class Config:
    themes: set[str] = field(default_factory=set)
    patterns: list[Pattern] = field(default_factory=lambda: list(BUILTIN_PATTERNS))
    found: bool = False


def load_config(home: Path, rep: Report) -> Config:
    cfg = Config()
    path = home / CONFIG_NAME
    if not path.exists():
        return cfg
    cfg.found = True
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        rep.err(CONFIG_NAME, f"not valid YAML: {e}")
        return cfg
    cfg.themes = {str(t).strip() for t in data.get("themes") or [] if str(t).strip()}
    for term in data.get("blocked_terms") or []:
        term = str(term).strip()
        if term:
            cfg.patterns.append(("blocked term", re.compile(
                rf"(?<!\w){re.escape(term)}(?!\w)", re.I)))
    for item in data.get("sensitive_patterns") or []:
        if not isinstance(item, dict) or not item.get("regex"):
            rep.err(CONFIG_NAME, f"sensitive_patterns item needs a regex: {item!r}")
            continue
        if (pat := compile_user_pattern(str(item.get("label") or "custom pattern"),
                                        str(item["regex"]), rep)):
            cfg.patterns.append(pat)
    return cfg


# ------------------------------------------------------------- validation ---
def check_entry(e: dict, where: str, themes: set[str], rep: Report) -> None:
    wid = e.get("id", "?")
    w = f"{where} {wid}"
    if wid == "WL-TBD":
        rep.err(w, "unresolved session-end entry; give it a real id")
        return
    if not ID_RE.match(str(wid)):
        rep.err(w, "id must look like WL-0001")
    for k in REQUIRED:
        if e.get(k) in (None, "", []):
            rep.err(w, f"missing required field '{k}'")

    def enum(key, allowed):
        v = e.get(key)
        if v is not None and v not in allowed:
            rep.err(w, f"{key}={v!r} not in {sorted(allowed)}")

    enum("op", OPS)
    enum("category", CATEGORIES)
    enum("status", STATUSES)
    enum("my_role", ROLES)
    src = e.get("source") or []
    for s in src if isinstance(src, list) else [src]:
        if s not in SOURCES:
            rep.err(w, f"source {s!r} not in {sorted(SOURCES)}")

    period = e.get("period") or {}
    if not isinstance(period, dict) or not MONTH_RE.match(str(period.get("start", ""))):
        rep.err(w, "period.start must be YYYY-MM")
    elif period.get("end") != "ongoing" and not MONTH_RE.match(str(period.get("end", ""))):
        rep.err(w, "period.end must be YYYY-MM or 'ongoing'")

    fu = e.get("follow_up_after")
    if fu is not None and not MONTH_RE.match(str(fu)):
        rep.err(w, "follow_up_after must be YYYY-MM or null")

    if themes and e.get("theme") and e["theme"] not in themes:
        rep.warn(w, f"theme {e['theme']!r} not in THEMES list")
    if e.get("status") == "CONFIRMED" and not e.get("evidence"):
        rep.warn(w, "CONFIRMED without evidence")
    if e.get("metrics") and str(e.get("result", "")).lower() == "not stated":
        rep.warn(w, "has metrics but result is 'not stated'; double-check provenance")


def build_state(files: list[LogFile], themes: set[str], rep: Report) -> dict[str, dict]:
    """Replay files in order; return id -> current entry. Records problems in rep."""
    state: dict[str, dict] = {}
    prev_to: str | None = None
    for f in files:
        name = f.path.name
        h = f.header
        if h.get("schema") != "worklog/v1":
            rep.err(name, f"schema must be worklog/v1 (got {h.get('schema')!r})")
        win = h.get("window") or {}
        if not win.get("from") or not win.get("to"):
            rep.err(name, "header.window.from/to missing")
        elif prev_to:
            expected = (dt.date.fromisoformat(prev_to) + dt.timedelta(days=1)).isoformat()
            if win["from"] > expected:
                rep.warn(name, f"window gap: previous file ended {prev_to}, this starts {win['from']}")
            elif win["from"] < expected:
                rep.warn(name, f"window overlaps previous file (ended {prev_to})")
        prev_to = win.get("to") or prev_to
        for gap in h.get("coverage_gaps") or []:
            rep.warn(name, f"declared coverage gap: {gap}")
        if h.get("file_type") == "compiled":
            if len(files) > 1:
                rep.err(name, "compiled snapshot mixed with monthly files; "
                              "keep compiled output outside the logs folder")
        elif not h.get("chats_read"):
            rep.warn(name, "chats_read missing or 0; was anything actually searched?")

        seen_here: set[str] = set()
        for e in f.entries:
            check_entry(e, name, themes, rep)
            wid = e.get("id")
            if not wid or not ID_RE.match(str(wid)):
                continue
            if wid in seen_here:
                rep.err(f"{name} {wid}", "id appears twice in the same file")
            seen_here.add(wid)
            if e.get("op") == "create" and wid in state:
                rep.err(f"{name} {wid}", "op: create but id already exists (should be update?)")
            if e.get("op") == "update" and wid not in state:
                rep.err(f"{name} {wid}", "op: update but id was never created")
            state[wid] = e

        expected_next = fmt_id(max(map(id_num, state), default=0) + 1)
        if h.get("next_id") != expected_next:
            rep.err(name, f"next_id is {h.get('next_id')!r}, expected {expected_next}")
    return state


def check_manifest(latest: LogFile, state: dict[str, dict], rep: Report) -> None:
    name = latest.path.name
    listed, actual = set(latest.manifest), set(state)
    for wid in sorted(actual - listed):
        rep.err(name, f"manifest is missing {wid} ({state[wid].get('title')})")
    for wid in sorted(listed - actual):
        rep.err(name, f"manifest lists {wid} but no entry exists")
    for wid in sorted(listed & actual):
        if state[wid].get("status") not in latest.manifest[wid]:
            rep.err(name, f"manifest status for {wid} disagrees with entry ({state[wid].get('status')})")


def load_all(paths: list[str], cfg: Config, rep: Report | None = None
             ) -> tuple[list[LogFile], dict, Report]:
    rep = rep or Report()
    files = [f for p in expand(paths) if (f := parse_file(p, rep))]
    files.sort(key=lambda f: str((f.header.get("window") or {}).get("from", "")))
    if not files:
        rep.err("input", "no worklog files found")
        return files, {}, rep
    state = build_state(files, cfg.themes, rep)
    check_manifest(files[-1], state, rep)
    for hit in find_sensitive(state, cfg.patterns):
        rep.err("SENSITIVE", hit)
    return files, state, rep


# ---------------------------------------------------------------- output ----
def render(files: list[LogFile], state: dict[str, dict]) -> str:
    ids = sorted(state, key=id_num)
    header = {
        "schema": "worklog/v1",
        "file_type": "compiled",
        "compiled_from": [f.path.name for f in files],
        "window": {"from": files[0].header["window"]["from"],
                   "to": files[-1].header["window"]["to"]},
        "generated_on": dt.date.today().isoformat(),
        "next_id": fmt_id(max(map(id_num, ids), default=0) + 1),
    }
    out = ["---", yaml.safe_dump(header, sort_keys=False).strip(), "---", "",
           "## Manifest (cumulative, all ids ever)",
           "| id | title | theme | category | status | last_updated |",
           "|----|-------|-------|----------|--------|--------------|"]
    for wid in ids:
        e = state[wid]
        out.append(f"| {wid} | {e.get('title', '')} | {e.get('theme', '')} | "
                   f"{e.get('category', '')} | {e.get('status', '')} | {e.get('updated', '')} |")
    out += ["", "## Entries", ""]
    for wid in ids:
        # A snapshot is self-contained: every entry is a create of its current state.
        e = state[wid] | {"op": "create"}
        out += [f"### {wid}: {e.get('title', '')}", "```yaml",
                yaml.safe_dump(e, sort_keys=False, allow_unicode=True, width=88).strip(),
                "```", ""]
    return "\n".join(out)


def walk_strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from walk_strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from walk_strings(x)


def scan_text(where: str, s: str, patterns: list[Pattern]) -> list[str]:
    return [f"{where}: {label}: …{s[max(0, m.start() - 20):m.end() + 20]}…"
            for label, pat in patterns for m in pat.finditer(s)]


def find_sensitive(state: dict[str, dict], patterns: list[Pattern]) -> list[str]:
    return [hit for wid in sorted(state, key=id_num)
            for s in walk_strings(state[wid]) for hit in scan_text(wid, s, patterns)]


# ------------------------------------------------------------------- CLI ----
def cmd_init(home: Path) -> int:
    for d in (home, home / "logs", home / "out"):
        d.mkdir(parents=True, exist_ok=True)
    home.chmod(0o700)  # the config lists customer names and codenames
    cfg = home / CONFIG_NAME
    if cfg.exists():
        print(f"kept existing {cfg}", file=sys.stderr)
    else:
        cfg.write_text(CONFIG_TEMPLATE, encoding="utf-8")
        cfg.chmod(0o600)
        print(f"created {cfg}", file=sys.stderr)
    print(f"data home ready: {home}", file=sys.stderr)
    return 0


def cmd_doctor(home: Path) -> int:
    """Machine-readable status lines the skill reads before every run."""
    rep = Report()
    cfg = load_config(home, rep)
    logs = sorted((home / "logs").glob("worklog-*.md")) if (home / "logs").is_dir() else []
    needs = []
    if not cfg.found:
        needs.append("no config: run `init`, then the setup interview")
    else:
        if not cfg.themes:
            needs.append("themes empty: ask the user for 6-10 themes")
        if len(cfg.patterns) == len(BUILTIN_PATTERNS):
            needs.append("blocked_terms empty: ask for customers, codenames, internal domains")
    print(f"home: {home}")
    print(f"config: {'ok' if cfg.found else 'missing'} "
          f"({len(cfg.themes)} themes, {len(cfg.patterns) - len(BUILTIN_PATTERNS)} private patterns)")
    print(f"logs: {len(logs)} file(s)")
    if logs:
        _, state, lrep = load_all([str(home / "logs")], cfg)
        last_to = max(str((f.header.get("window") or {}).get("to", ""))
                      for f in (parse_file(p, Report()) for p in logs) if f)
        print(f"entries: {len(state)}; last covered day: {last_to}; "
              f"validate: {'FAIL' if lrep.errors else 'ok'}")
        if last_to:
            nxt = dt.date.fromisoformat(last_to) + dt.timedelta(days=1)
            if nxt.replace(day=1) < dt.date.today().replace(day=1):
                print(f"next to extract: {nxt:%Y-%m}")
    else:
        print("next to extract: baseline (ask the user which month their work started)")
    for n in needs + rep.errors:
        print(f"SETUP NEEDED: {n}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", type=Path, default=None,
                    help="data home (default: $WORKLOG_HOME or ~/worklog)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("doctor")
    for name in ("validate", "compile", "due"):
        p = sub.add_parser(name)
        p.add_argument("paths", nargs="*")
        if name == "compile":
            p.add_argument("-o", "--output", type=Path, default=None)
        if name == "due":
            p.add_argument("--today", default=dt.date.today().isoformat())
    sub.add_parser("scan").add_argument("paths", nargs="+")
    args = ap.parse_args(argv)
    home = resolve_home(args.home)

    if args.cmd == "init":
        return cmd_init(home)
    if args.cmd == "doctor":
        return cmd_doctor(home)

    rep = Report()
    cfg = load_config(home, rep)
    if args.cmd == "scan":
        hits = [h for p in map(Path, args.paths)
                for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                for h in scan_text(f"{p.name}:{n}", line, cfg.patterns)]
        for h in hits:
            print(f"SENSITIVE {h}", file=sys.stderr)
        rep.print()
        print(f"{len(hits)} finding(s)", file=sys.stderr)
        return 1 if hits or rep.errors else 0

    files, state, rep = load_all(args.paths or [str(home / "logs")], cfg, rep)
    rep.print()
    if rep.errors:
        return 1

    if args.cmd == "validate":
        print(f"OK: {len(files)} file(s), {len(state)} entries", file=sys.stderr)
    elif args.cmd == "compile":
        out = args.output or home / "out" / "current.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(files, state), encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    elif args.cmd == "due":
        month = args.today[:7]
        for wid in sorted(state, key=id_num):
            fu = state[wid].get("follow_up_after")
            if fu and fu <= month:
                print(f"{wid} | {state[wid].get('title')} | follow up since {fu} | "
                      f"status {state[wid].get('status')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
