"""Campus AI OS 5.2.11 - no shipped write instruction sends a non-clock primary to the shared ledger.

Codex re-audit of 5.2.10 (2026-09-23): an assigned Claude Code or Codex client resolves
`role: primary`, `owns_clock: false`, yet the sanctioned team-plugin wording in
`templates/ledger-paths.md`, `/campus-first-win` and `/full-onboarding` still told it to
append to `dean/.activity.jsonl`. These fixtures run the real resolver for that client and
check the shipped instruction surface against its answer.

platform: claude-code; seat: m4-claude-code
"""
import importlib.util
import os
import re
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
RESOLVER = KERNEL / "tools" / "resolve-seat.py"
MID = "b" * 64
CO_PRIMARY = {
    "schema_version": 2, "seat": "owner", "role": "primary", "client": "claude-cowork",
    "machine_id": MID, "clock_owner": "claude-cowork",
    "clients": {"claude-cowork": {"seat": "owner", "role": "primary"},
                "codex": {"seat": "codex", "role": "primary"},
                "claude-code": {"seat": "host-code", "role": "primary"}},
}
SHARED = "dean/.activity.jsonl"
# A line that names the shared ledger as the place to write, with no clock-owner qualifier.
WRITE_VERB = re.compile(r"\b(log|append|write)\b[^.\n]{0,80}\bto\b[^.\n]{0,20}`?dean/\.activity\.jsonl`?", re.I)


def resolver():
    spec = importlib.util.spec_from_file_location("resolve_seat_5211", RESOLVER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def shipped_text_files():
    for p in KERNEL.rglob("*"):
        rel = p.relative_to(KERNEL).as_posix()
        if p.is_file() and p.suffix in (".md", ".json") and not rel.startswith(("tests/", "__pycache__")) and rel != "CHANGELOG.md":
            yield rel, p.read_text(encoding="utf-8", errors="replace")


class NonClockPrimaryLedger(unittest.TestCase):
    def setUp(self):
        self.r = resolver()

    def test_non_clock_primaries_resolve_their_own_shard(self):
        for client, seat in (("codex", "codex"), ("claude-code", "host-code")):
            out = self.r.resolve(CO_PRIMARY, client, MID)
            self.assertEqual(out["role"], "primary")
            self.assertFalse(out["owns_clock"])
            self.assertEqual(out["ledger"], f"dean/.activity.{seat}.jsonl")
        self.assertEqual(self.r.resolve(CO_PRIMARY, "claude-cowork", MID)["ledger"], SHARED)

    def test_sanctioned_team_wording_follows_the_clock(self):
        text = (KERNEL / "templates" / "ledger-paths.md").read_text(encoding="utf-8")
        self.assertIn("clock-owner seat: `dean/.activity.jsonl`; every other seat: `dean/.activity.{seat}.jsonl`", text)
        self.assertNotIn("(primary seat:", text)

    def test_flagged_skills_write_the_resolved_ledger(self):
        for rel in ("skills/campus-first-win/SKILL.md", "skills/full-onboarding/SKILL.md"):
            text = (KERNEL / rel).read_text(encoding="utf-8")
            self.assertIn("the ledger your seat resolves to", text, rel)
            self.assertNotRegex(text, r"Log the run to `?dean/\.activity\.jsonl", rel)

    def test_no_shipped_instruction_writes_the_shared_ledger_unqualified(self):
        offenders = []
        for rel, text in shipped_text_files():
            for line in text.splitlines():
                if WRITE_VERB.search(line) and not re.search(r"clock[- ]owner|owns_clock|resolves? to|never|NEVER", line):
                    offenders.append(f"{rel}: {line.strip()[:140]}")
        self.assertEqual(offenders, [], "write instructions that ignore owns_clock:\n" + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
