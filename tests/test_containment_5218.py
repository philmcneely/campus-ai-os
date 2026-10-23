"""Runtime writers stay inside the campus; stamped edits survive; cloud kit rule matches the checker (5.2.18).

From the Codex audit of the public 5.2.17 (`outputs/2026-10/reports/2026-10-22-campus-ai-os-github-audit.md`):
F1 the minter, the registration-spec writer and the Campus Map followed a planted link out of the campus;
F3 an edit made to a generated spec without touching its stamp read "current" and the next refresh erased it;
F4 the Cowork kit rule demanded every manifest file although founding copies the core tier only.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
TOOLS = KERNEL / "tools"
SPEC = ".campus-os/registration-block-spec.md"
SENTINEL = "outside sentinel - must not change\n"


def py(*args, cwd=None):
    return subprocess.run([sys.executable, "-I", "-B", *map(str, args)], cwd=cwd, capture_output=True, text=True, timeout=60)


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="cos-5218-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.root = self.base / "campus"
        (self.root / ".campus-os").mkdir(parents=True)
        (self.root / "dean").mkdir()
        (self.root / "workspace.json").write_text("{}")
        (self.root / "CLAUDE.md").write_text("entry\n")
        self.outside = self.base / "outside"
        self.outside.mkdir()

    def outside_listing(self):
        return sorted(str(p.relative_to(self.outside)) for p in self.outside.rglob("*"))


class MinterContainment(Base):
    def mint(self, *extra):
        return py(TOOLS / "mint_run_id.py", "mint", "audit", "--team", "audit-team", "--campus-root", self.root, "--json", *extra)

    def test_ordinary_mint_still_works(self):
        p = self.mint()
        self.assertEqual(p.returncode, 0, p.stderr)
        run_dir = Path(json.loads(p.stdout)["run_dir"])
        self.assertTrue((run_dir / "results.json").is_file())
        self.assertIn(self.root, run_dir.resolve().parents)

    def test_a_linked_outputs_folder_is_refused(self):
        (self.root / "outputs").symlink_to(self.outside)
        p = self.mint()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("link-in-path", p.stderr)
        self.assertEqual(self.outside_listing(), [])

    def test_a_link_deeper_in_the_path_is_refused(self):
        p = self.mint()  # creates outputs/{month}/runs/audit-team/audit/...
        team = Path(json.loads(p.stdout)["run_dir"]).parent.parent
        shutil.rmtree(team)
        team.symlink_to(self.outside)
        p = self.mint()
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(self.outside_listing(), [])

    def test_standalone_runs_are_contained_too(self):
        (self.root / "teams-shared").symlink_to(self.outside)
        p = self.mint("--standalone")
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(self.outside_listing(), [])


class SpecWriter(Base):
    def materialize(self, *extra):
        return py(TOOLS / "materialize_registration_spec.py", "--campus-root", self.root, *extra)

    def test_a_dangling_spec_link_is_refused_and_nothing_is_created_outside(self):
        (self.root / SPEC).symlink_to(self.outside / "planted.md")
        p = self.materialize()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(self.outside_listing(), [])

    def test_a_linked_campus_os_folder_is_refused(self):
        shutil.rmtree(self.root / ".campus-os")
        (self.root / ".campus-os").symlink_to(self.outside)
        p = self.materialize()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(self.outside_listing(), [])

    def edit_stamped_spec(self):
        self.assertEqual(self.materialize().returncode, 0)
        spec = self.root / SPEC
        text = spec.read_text()
        text = re.sub(r'("department"\s*:\s*")([^"]+)', lambda m: m.group(1) + m.group(2) + " | owner-delivery", text, count=1)
        spec.write_text(text + "\nOwner note: keep this line.\n")  # first line (the stamp) untouched
        return spec

    def test_an_edit_under_an_intact_stamp_is_seen(self):
        self.edit_stamped_spec()
        p = self.materialize("--check", "--json")
        self.assertEqual(p.returncode, 1)
        out = json.loads(p.stdout)
        self.assertEqual(out["state"], "hand-edited")
        self.assertTrue(out["edited_after_stamp"])

    def test_refresh_refuses_without_overrides_then_keeps_the_edit_after_capture(self):
        spec = self.edit_stamped_spec()
        refused = self.materialize()
        self.assertEqual(refused.returncode, 1, refused.stdout)
        self.assertIn("Owner note: keep this line.", spec.read_text(), "refusal left the edit in place")
        # --capture-notes writes the overrides and then refreshes in the same run
        self.assertEqual(self.materialize("--capture-notes").returncode, 0)
        backups = sorted((self.root / ".campus-os").glob("registration-block-spec.md.bak-*"))
        self.assertEqual(len(backups), 1, "the edited copy is backed up before it is replaced")
        self.assertIn("Owner note: keep this line.", backups[0].read_text())
        refreshed = spec.read_text()
        self.assertIn("owner-delivery", refreshed)
        self.assertIn("Owner note: keep this line.", refreshed)
        self.assertEqual(json.loads(self.materialize("--check", "--json").stdout)["state"], "current")

    def test_an_older_stamp_without_a_body_hash_is_still_checked(self):
        self.assertEqual(self.materialize().returncode, 0)
        spec = self.root / SPEC
        text = re.sub(r" \| body_sha256=[0-9a-f]{64}", "", spec.read_text(), count=1)  # a 5.2.17-era stamp
        spec.write_text(text)
        self.assertEqual(json.loads(self.materialize("--check", "--json").stdout)["state"], "current")
        spec.write_text(text + "\nOwner note under an old stamp.\n")
        self.assertEqual(json.loads(self.materialize("--check", "--json").stdout)["state"], "hand-edited")


@unittest.skipIf(shutil.which("node") is None, "node not available")
class MapWriter(Base):
    def build(self, out):
        env = dict(os.environ, CAMPUS_ROOT=str(self.root), CAMPUS_MAP_OUT=str(out))
        return subprocess.run(["node", str(KERNEL / "campus-map" / "generate.mjs"), "--no-remote-fonts"],
                              env=env, capture_output=True, text=True, timeout=60)

    def test_a_linked_map_folder_is_refused(self):
        (self.outside / "campus-map.html").write_text(SENTINEL)
        (self.root / "campus-map").symlink_to(self.outside)
        r = self.build(self.root / "campus-map")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual((self.outside / "campus-map.html").read_text(), SENTINEL)

    def test_a_linked_map_file_is_replaced_not_written_through(self):
        (self.outside / "victim.html").write_text(SENTINEL)
        (self.root / "campus-map").mkdir()
        (self.root / "campus-map" / "campus-map.html").symlink_to(self.outside / "victim.html")
        r = self.build(self.root / "campus-map")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.outside / "victim.html").read_text(), SENTINEL)
        self.assertFalse((self.root / "campus-map" / "campus-map.html").is_symlink())


class CloudKitRule(Base):
    """F4: the written Cowork rule and kernel_kit.check accept and reject the same kits."""

    def cloud_rule(self, manifest):
        # The canon's inline listing, then its rule: core required, on-demand optional but must match.
        kit = self.root / ".campus-os/kernel"
        lines = {}
        for folder, dirs, files in os.walk(kit):
            for name in dirs + files:
                p = Path(folder) / name
                if p.is_symlink():
                    lines[str(p.relative_to(kit))] = "LINK"
                elif p.is_file():
                    lines[str(p.relative_to(kit))] = __import__("hashlib").sha256(p.read_bytes()).hexdigest()
        lines.pop("KIT.json", None)
        files, tiers = manifest["files"], manifest["tiers"]
        extra = [r for r in lines if r not in files]
        wrong = [r for r, h in lines.items() if r in files and h != files[r]]
        missing_core = [r for r in tiers["core"] if r not in lines]
        return not (extra or wrong or missing_core)

    def test_core_only_and_full_kits_pass_both_and_a_changed_on_demand_file_fails_both(self):
        manifest = json.loads((TOOLS / "kit-manifest.json").read_text())
        canon = (KERNEL / "templates" / "run-id-and-interop.md").read_text(encoding="utf-8")
        self.assertIn("a `tiers.on_demand` file may", canon)
        for tier in ("core", "all"):
            with self.subTest(tier=tier):
                shutil.rmtree(self.root / ".campus-os/kernel", ignore_errors=True)
                self.assertEqual(py(TOOLS / "kernel_kit.py", "install", "--kernel", KERNEL, "--campus-root", self.root,
                                    "--tier", tier).returncode, 0)
                checked = json.loads(py(TOOLS / "kernel_kit.py", "check", "--campus-root", self.root, "--manifest",
                                        TOOLS / "kit-manifest.json", "--json").stdout)
                self.assertTrue(checked["ok"], checked)
                self.assertTrue(self.cloud_rule(manifest))
        weight = self.root / ".campus-os/kernel/tools/context-weight.mjs"
        weight.write_text(weight.read_text() + "\n// changed\n")
        checked = json.loads(py(TOOLS / "kernel_kit.py", "check", "--campus-root", self.root, "--manifest",
                                TOOLS / "kit-manifest.json", "--json").stdout)
        self.assertFalse(checked["ok"])
        self.assertFalse(self.cloud_rule(manifest))


class MarketplaceCatalogs(unittest.TestCase):
    """F2: the public repo is a marketplace for both hosts; the buyer's file carries no catalog."""

    def test_both_catalogs_name_the_root_plugin_and_use_accepted_values(self):
        claude = json.loads((KERNEL / ".claude-plugin" / "marketplace.json").read_text())
        codex = json.loads((KERNEL / ".agents" / "plugins" / "marketplace.json").read_text())
        manifest = json.loads((KERNEL / ".claude-plugin" / "plugin.json").read_text())
        # README: `/plugin install campus-ai-os@campus-ai-os` -> marketplace name and plugin name
        for cat in (claude, codex):
            self.assertEqual(cat["name"], "campus-ai-os")
            self.assertEqual([p["name"] for p in cat["plugins"]], [manifest["name"]])
        self.assertEqual(claude["plugins"][0]["source"], "./")
        self.assertEqual(codex["plugins"][0]["source"], {"source": "path", "path": "./"})
        policy = codex["plugins"][0]["policy"]
        self.assertIn(policy["installation"], {"AVAILABLE", "NOT_AVAILABLE", "INSTALLED_BY_DEFAULT"})
        if "authentication" in policy:  # Codex CLI 0.163 accepts only these two
            self.assertIn(policy["authentication"], {"ON_INSTALL", "ON_USE"})
        for cat in (claude, codex):
            self.assertNotIn("version", json.dumps(cat), "no second version home outside the lockstep")

    def test_the_buyer_file_carries_no_catalog(self):
        sys.path.insert(0, str(TOOLS))
        import package
        names = {rel.as_posix() for _, rel in package.collect(KERNEL)}
        self.assertIn(".claude-plugin/plugin.json", names)
        self.assertNotIn(".claude-plugin/marketplace.json", names)
        self.assertNotIn(".agents/plugins/marketplace.json", names)


if __name__ == "__main__":
    unittest.main()
