"""5.2.10 - co-primary reaches every contract, and the pack plumbing a second pack needs.
platform: claude-code; seat: m4-claude-code
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

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
PIN = 'a1dc48e68138490d522c04cbf5822214c6eb1202'


class CoPrimaryReachesEveryContract(unittest.TestCase):
    """The resolver sends a non-clock-owner primary to its own shard. Every
    written contract has to say the same thing."""

    def test_contract_names_the_clock_owner_ledger(self):
        ledger = json.loads((KERNEL / 'contracts/campus.json').read_text())['seat']['ledger']
        self.assertEqual(ledger['clock_owner'], 'dean/.activity.jsonl')
        self.assertEqual(ledger['co_primary'], 'dean/.activity.{seat}.jsonl')
        self.assertIn('clock_owner', ledger['write_rule'])
        # readers (doctor_evidence) still find the shared ledger by this key
        self.assertEqual(ledger['primary'], ledger['clock_owner'])

    def test_contract_agrees_with_the_resolver(self):
        src = (KERNEL / 'tools/resolve-seat.py').read_text()
        self.assertIn("ledger='dean/.activity.jsonl' if owns_clock else f'dean/.activity.{seat}.jsonl'", src)

    def test_no_assigned_client_defaults_to_satellite(self):
        clients = json.loads((KERNEL / 'contracts/campus.json').read_text())['hosts']['clients']
        self.assertEqual({v['seat_default_role'] for v in clients.values()}, {'primary-eligible'})
        table = (KERNEL / 'contracts/campus-contract.md').read_text()
        for client in clients:
            self.assertRegex(table, rf'\| `{re.escape(client)}` \|[^\n]*\| primary-eligible \|')
        self.assertIn('| primary, not clock owner | `dean/.activity.{seat}.jsonl` |', table)

    def test_ledger_canon_sends_every_role_to_the_returned_ledger(self):
        canon = (KERNEL / 'templates/ledger-paths.md').read_text()
        self.assertNotIn('Primary: `dean/.activity.jsonl`.', canon)
        self.assertIn('Use the returned `ledger` exactly, whatever your role.', canon)
        self.assertIn('`owns_clock`', canon)

    def test_adapters_and_brain_templates_do_not_grant_the_shared_ledger(self):
        agents = (KERNEL / 'templates/clients/AGENTS.md').read_text()
        self.assertNotRegex(agents, r'You may APPEND to\s+`dean/\.activity\.jsonl`')
        self.assertIn('Only the clock-owner client appends to `dean/.activity.jsonl`.', agents)
        for name in ('templates/dean-CLAUDE.md', 'templates/dean-CODEX.md'):
            body = (KERNEL / name).read_text()
            self.assertNotRegex(body, r'completed workflow to\s+`dean/\.activity\.jsonl`:', name)
            self.assertIn('.campus-os/ledger-paths.md', body, name)


class PackPlumbing(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='phase7-packs-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.kernel = self.tmp / 'kernel'
        shutil.copytree(KERNEL, self.kernel, ignore=shutil.ignore_patterns('tests', '__pycache__', '.git'))
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        self.active = json.loads((self.kernel / 'packs/active.json').read_text())['active_pack']
        self.make_second_pack()

    def cli(self, *args, tree=None):
        return subprocess.run([sys.executable, str((tree or self.kernel) / 'tools/build_niche.py'), *args],
                              env=self.env, capture_output=True, text=True, timeout=60)

    def make_second_pack(self, **extra):
        """A fixture pack that renames departments and borrows one skill."""
        base = json.loads((self.kernel / 'packs' / self.active / 'pack.json').read_text())
        self.borrowed = base['domain_skills'][0]
        pack = dict(base, pack='fixture', label='Fixture', domain_skills=[], shared_skills=[self.borrowed], hires=[])
        pack['managers'] = [dict(m, display_name=f"Fixture {m['id']}") for m in base.get('managers', [])]
        pack.update(extra)
        d = self.kernel / 'packs/fixture'
        d.mkdir(exist_ok=True)
        (d / 'pack.json').write_text(json.dumps(pack, indent=2))
        return pack

    def failures(self, p):
        return re.findall(r'^FAIL: (NICHE-[0-9A-Z]+):', p.stdout, re.M)

    # -- item 2: the active-pack pointer ------------------------------------
    def test_no_skill_spells_a_pack_folder(self):
        p = self.cli('--only', 'NICHE-025')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        start = self.kernel / 'skills/campus-start/SKILL.md'
        self.assertIn('`packs/active.json` -> `active_pack`', start.read_text())
        start.write_text(start.read_text() + f'\nRead `packs/{self.active}/pack.json`.\n')
        p = self.cli('--only', 'NICHE-025')
        self.assertEqual(self.failures(p), ['NICHE-025'], p.stdout)
        self.assertIn('skills/campus-start/SKILL.md', p.stdout)

    def test_pointer_must_name_a_real_pack(self):
        args = ('--pack', self.active, '--only', 'NICHE-025')
        (self.kernel / 'packs/active.json').write_text('{"active_pack": "ghost"}')
        self.assertEqual(self.failures(self.cli(*args)), ['NICHE-025'])
        (self.kernel / 'packs/active.json').unlink()
        self.assertEqual(self.failures(self.cli(*args)), ['NICHE-025'])

    def test_gate_defaults_to_the_active_pack(self):
        (self.kernel / 'packs/active.json').write_text('{"active_pack": "fixture"}')
        p = self.cli('--only', 'NICHE-001')
        self.assertEqual(p.stdout, "OK: pack 'fixture' conformant\n")

    # -- item 3: a second in-tree pack passes the label gate ------------------
    def test_second_in_tree_pack_is_conformant(self):
        p = self.cli('--pack', 'fixture', '--check')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.cli('--pack', self.active, '--check').returncode, 0)

    def test_label_drift_is_still_caught_for_the_active_pack(self):
        reg = self.kernel / 'templates/registry.json'
        data = json.loads(reg.read_text())
        next(t for t in data['teams'] if t.get('type') == 'department')['label'] = 'Drifted'
        reg.write_text(json.dumps(data, indent=2))
        self.assertEqual(self.failures(self.cli('--pack', self.active, '--only', 'NICHE-024')), ['NICHE-024'])

    def test_assembled_pack_derives_its_own_registry_template(self):
        out = self.tmp / 'built'
        p = self.cli('--pack', 'fixture', '--assemble', str(out))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads((out / 'packs/active.json').read_text()), {'active_pack': 'fixture'})
        self.assertEqual([d.name for d in (out / 'packs').iterdir() if d.is_dir()], ['fixture'])
        labels = {t['team']: t['label'] for t in json.loads((out / 'templates/registry.json').read_text())['teams']
                  if t.get('type') == 'department'}
        renamed = {k: v for k, v in labels.items() if v == f'Fixture {k}'}
        self.assertTrue(renamed, labels)
        # the built tree is conformant on its own terms, with no --pack argument
        p = self.cli('--check', tree=out)
        self.assertEqual(p.stdout, "OK: pack 'fixture' conformant\n", p.stdout + p.stderr)

    def test_active_pack_round_trip_is_file_identical(self):
        out = self.tmp / 'same'
        self.assertEqual(self.cli('--pack', self.active, '--assemble', str(out)).returncode, 0)
        shutil.rmtree(self.kernel / 'packs/fixture')
        others = [d for d in (self.kernel / 'packs').iterdir() if d.is_dir() and d.name != self.active]
        for d in others:
            shutil.rmtree(d)
        diff = subprocess.run(['diff', '-rq', str(self.kernel), str(out)], capture_output=True, text=True)
        self.assertEqual(diff.stdout, '')

    # -- item 4: shared_skills[] ---------------------------------------------
    def test_borrowed_skill_survives_assembly_and_unborrowed_is_dropped(self):
        owner = json.loads((self.kernel / 'packs' / self.active / 'pack.json').read_text())
        others = [s for s in owner['domain_skills'] if s != self.borrowed]
        out = self.tmp / 'borrow'
        self.assertEqual(self.cli('--pack', 'fixture', '--assemble', str(out)).returncode, 0)
        self.assertTrue((out / 'skills' / self.borrowed / 'SKILL.md').is_file())
        for s in others:
            self.assertFalse((out / 'skills' / s).exists(), s)

    def test_shared_skills_rejects_bad_entries(self):
        for bad, why in ((['no-such-skill'], 'does not exist'), (['campus-doctor'], 'kernel skill'),
                         ([self.borrowed, self.borrowed], 'twice'), ('class-manager', 'must be a list')):
            with self.subTest(bad=bad):
                self.make_second_pack(shared_skills=bad)
                p = self.cli('--pack', 'fixture', '--only', 'NICHE-026')
                self.assertEqual(set(self.failures(p)), {'NICHE-026'}, p.stdout)
                self.assertIn(why, p.stdout)

    def test_pack_without_the_new_keys_is_unchanged(self):
        pack = self.make_second_pack()
        for key in ('shared_skills', 'hires'):
            pack.pop(key)
        (self.kernel / 'packs/fixture/pack.json').write_text(json.dumps(pack))
        self.assertEqual(self.cli('--pack', 'fixture', '--only', 'NICHE-026,NICHE-027').returncode, 0)

    # -- item 5: hires[] -------------------------------------------------------
    def hire(self, **over):
        h = {'hire': 'demo', 'repo': 'https://github.com/example/demo', 'pin': PIN,
             'license': 'MIT', 'permission': 'draft-only'}
        h.update(over)
        return {k: v for k, v in h.items() if v is not None}

    def test_valid_hire_passes(self):
        self.make_second_pack(hires=[self.hire()])
        p = self.cli('--pack', 'fixture', '--only', 'NICHE-027')
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_hires_gate_rejects_unsafe_manifests(self):
        cases = ((self.hire(pin='main'), '40-character'), (self.hire(permission='publish'), 'draft-only'),
                 (self.hire(license=None), 'missing `license`'), (self.hire(repo='git@github.com:x/y'), 'https'))
        for manifest, why in cases:
            with self.subTest(why=why):
                self.make_second_pack(hires=[manifest])
                p = self.cli('--pack', 'fixture', '--only', 'NICHE-027')
                self.assertEqual(set(self.failures(p)), {'NICHE-027'}, p.stdout)
                self.assertIn(why, p.stdout)
        self.make_second_pack(hires=[self.hire(), self.hire()])
        self.assertIn('declared twice', self.cli('--pack', 'fixture', '--only', 'NICHE-027').stdout)


if __name__ == '__main__':
    unittest.main()
