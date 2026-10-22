"""Campus finder: the host opened the folder ABOVE the campus (5.2.16).

Found 2026-10-22 on the owner's live install: Cowork mounts `TrainingSites/` and the campus is the
child `TrainingSites/Claude-Cowork/`. Walking up from the mount finds nothing, so every team that
followed the campus rule said "install Campus OS first". The finder now accepts exactly one campus
among the start folder's children, and refuses to guess between two.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
TOOL = KERNEL / "tools" / "resolve_context.py"


def make_campus(folder: Path, entry="CLAUDE.md", in_dean=False):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "workspace.json").write_text("{}")
    (folder / "dean").mkdir(exist_ok=True)
    (folder / ("dean" if in_dean else "") / entry).write_text("entry\n")
    (folder / "shared").mkdir(exist_ok=True)
    return folder


class ChildCampus(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="cos-5216-finder-")
        self.addCleanup(tmp.cleanup)
        self.mount = Path(tmp.name).resolve() / "TrainingSites"
        self.mount.mkdir()
        (self.mount / "inputs").mkdir()  # ordinary sibling folders are not campuses
        (self.mount / "CLAUDE.md").write_text("redirect to Claude-Cowork/\n")  # an entry file alone is not a campus

    def find(self, *extra, start=None):
        p = subprocess.run([sys.executable, "-I", "-B", str(TOOL), "--find-campus", "--json",
                            "--start", str(start or self.mount), *extra], capture_output=True, text=True)
        return p.returncode, json.loads(p.stdout), p.stderr

    def test_one_child_campus_is_found_from_the_mount(self):
        campus = make_campus(self.mount / "Claude-Cowork")
        rc, out, _ = self.find()
        self.assertEqual(rc, 0)
        self.assertEqual(out["campus_root"], str(campus))
        self.assertEqual(out["found"], "child")

    def test_two_child_campuses_are_never_guessed_between(self):
        a = make_campus(self.mount / "campus-a")
        b = make_campus(self.mount / "campus-b", entry="AGENTS.md", in_dean=True)
        rc, out, err = self.find()
        self.assertEqual(rc, 3)
        self.assertIsNone(out["campus_root"])
        self.assertEqual(out["several_campuses"], [str(a), str(b)])
        concept = subprocess.run([sys.executable, "-I", "-B", str(TOOL), "--concept", "icp", "--start", str(self.mount)],
                                 capture_output=True, text=True)
        self.assertEqual(concept.returncode, 3)
        self.assertIn("SEVERAL CAMPUSES", concept.stderr)

    def test_a_campus_above_still_wins_over_children(self):
        outer = make_campus(self.mount)
        make_campus(self.mount / "Claude-Cowork")
        rc, out, _ = self.find(start=self.mount / "inputs")
        self.assertEqual((rc, out["campus_root"], out["found"]), (0, str(outer), "above"))
        rc, out, _ = self.find()
        self.assertEqual((out["campus_root"], out["found"]), (str(outer), "here"))

    def test_hidden_and_linked_children_are_ignored(self):
        real = make_campus(Path(tempfile.mkdtemp(prefix="cos-5216-elsewhere-")))
        self.addCleanup(lambda: __import__("shutil").rmtree(real, True))
        (self.mount / "linked").symlink_to(real)  # a link to a campus elsewhere is never followed
        make_campus(self.mount / ".claude" / "worktree")  # hidden folders, and only ONE level down
        make_campus(self.mount / ".hidden-campus")
        rc, out, _ = self.find()
        self.assertEqual(rc, 3)
        self.assertIsNone(out["campus_root"])
        self.assertNotIn("several_campuses", out)

    def test_only_one_level_down(self):
        make_campus(self.mount / "clients" / "acme")
        rc, out, _ = self.find()
        self.assertEqual((rc, out["campus_root"]), (3, None))

    def test_campus_rule_owner_states_the_child_rule(self):
        canon = (KERNEL / "templates" / "context-files.md").read_text(encoding="utf-8")
        self.assertIn("exactly one campus among its children", canon)


if __name__ == "__main__":
    unittest.main()
