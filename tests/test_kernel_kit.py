"""Kernel kit: the campus copy of the kernel tools (.campus-os/kernel/, tools/kernel_kit.py).

Found 2026-10-21 (Email Desk tests in Cowork): the plugin ran in a cloud container that could not
see the campus, so run_ids were typed by hand and no validator or doctor ran. These fixtures prove
the kit runs with the plugin tree GONE, refuses to downgrade, catches damaged copies, and that no
kernel instruction names a tool the kit list does not account for.
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
sys.path.insert(0, str(KERNEL / 'tools'))
import kernel_kit  # noqa: E402

KIT = '.campus-os/kernel'


def importlib_magic():
    import importlib.util
    return importlib.util.MAGIC_NUMBER


class KitList(unittest.TestCase):
    def test_every_listed_file_ships_and_the_manifest_is_current(self):
        for rel in kernel_kit.CORE + kernel_kit.ON_DEMAND + tuple(kernel_kit.PLUGIN_ONLY) + kernel_kit.MAINTAINER_ONLY:
            with self.subTest(rel=rel):
                self.assertTrue((KERNEL / rel).is_file(), rel)
        p = subprocess.run([sys.executable, str(KERNEL / 'tools/kernel_kit.py'), 'manifest', '--check',
                            '--kernel', str(KERNEL)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_every_tool_a_kernel_instruction_names_is_accounted_for(self):
        # A tool named in a skill, canon or contract but missing from every list is the drift that
        # left Cowork campuses without a minter: a new tool nobody copies.
        known = set(kernel_kit.CORE + kernel_kit.ON_DEMAND + tuple(kernel_kit.PLUGIN_ONLY) + kernel_kit.MAINTAINER_ONLY)
        named = {}
        for top in ('skills', 'templates', 'references', 'contracts', 'schemas', 'packs'):
            for path in sorted((KERNEL / top).rglob('*')):
                if path.suffix not in ('.md', '.json') or not path.is_file():
                    continue
                for m in re.finditer(r'\btools/([A-Za-z0-9_-]+\.(?:py|mjs))', path.read_text(encoding='utf-8')):
                    named.setdefault('tools/' + m.group(1), str(path.relative_to(KERNEL)))
        unknown = {t: where for t, where in named.items() if t not in known and t != kernel_kit.MANIFEST}
        self.assertEqual(unknown, {}, 'add each tool to a list in tools/kernel_kit.py')

    def test_founding_and_upgrade_both_write_the_kit(self):
        for rel in ('skills/campus-start/SKILL.md', 'skills/update-workspace/SKILL.md'):
            self.assertIn('.campus-os/kernel/', (KERNEL / rel).read_text(encoding='utf-8'), rel)
        canon = (KERNEL / 'templates/run-id-and-interop.md').read_text(encoding='utf-8')
        self.assertIn('## 0. Where kernel tools run', canon)
        self.assertIn('python3 -I -B {kernel}/tools/mint_run_id.py mint', canon)
        self.assertIn('Always run kit Python tools as `python3 -I -B`', canon)


class KitOnACampus(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='kernel-kit-')
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.kernel = self.base / 'plugin'
        shutil.copytree(KERNEL, self.kernel, ignore=shutil.ignore_patterns('tests', '__pycache__', '.git'))
        self.root = self.base / 'campus'
        (self.root / '.campus-os').mkdir(parents=True)
        (self.root / 'dean').mkdir()
        (self.root / 'shared').mkdir()
        self.version = kernel_kit.kernel_version(self.kernel)
        template = json.loads((self.kernel / 'templates/registry.json').read_text())
        (self.root / 'workspace.json').write_text(json.dumps({'version': self.version}))
        (self.root / 'AGENTS.md').write_text('Read dean/AGENTS.md.\n')
        shutil.copy2(self.kernel / 'templates/dean-CLAUDE.md', self.root / 'dean/AGENTS.md')
        (self.root / '.campus-os/registry.json').write_text(json.dumps(template))
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        self.env.pop('CAMPUS_CONTRACT', None)

    def kit(self, *args, kernel=None):
        tool = (kernel or self.root / KIT) / 'tools/kernel_kit.py'
        return subprocess.run([sys.executable, '-I', str(tool), *map(str, args)], cwd=self.root,
                              env=self.env, capture_output=True, text=True, timeout=30)

    def install(self, tier='all'):
        p = self.kit('install', '--kernel', self.kernel, '--campus-root', self.root, '--tier', tier, kernel=self.kernel)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def test_kit_runs_with_the_plugin_tree_gone(self):
        self.install()
        manifest = (self.kernel / 'tools/kit-manifest.json').read_text()  # what the model reads with file tools
        shutil.rmtree(self.kernel)  # the campus-visible shell cannot see the plugin (Cowork)
        p = self.kit('check', '--campus-root', '.', '--installed-version', self.version, '--tier', 'all', '--json')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)['version'], 'current')
        tools = self.root / KIT / 'tools'
        mint = subprocess.run([sys.executable, '-I', str(tools / 'mint_run_id.py'), 'mint', 'kit-fixture',
                               '--team', 'fixture-team', '--campus-root', '.', '--json'],
                              cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(mint.returncode, 0, mint.stderr)
        run_id = json.loads(mint.stdout)['run_id']
        self.assertRegex(run_id, r'^kit-fixture-\d{8}-\d{9}$')
        found = subprocess.run([sys.executable, '-I', str(tools / 'resolve_context.py'), '--find-campus', '--json'],
                               cwd=self.root / 'shared', env=self.env, capture_output=True, text=True)
        self.assertEqual(json.loads(found.stdout)['campus_root'], str(self.root.resolve()))
        valid = subprocess.run([sys.executable, '-I', str(tools / 'validate_results.py'), '--campus-root', '.', '--json'],
                               cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(json.loads(valid.stdout)['failing'], 0, valid.stdout)
        # -I drops the script folder from sys.path; the doctor must still import its siblings.
        doctor = [sys.executable, '-I', str(tools / 'doctor_evidence.py'), '--campus-root', '.', '--json', '--today', '2026-10-21']
        anchored = subprocess.run(doctor + ['--kit-manifest', '-'], input=manifest,
                                  cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertIn(anchored.returncode, (0, 1), anchored.stderr)
        self.assertEqual(json.loads(anchored.stdout)['kernel_kit']['status'], 'ok')
        # From the kit with no plugin manifest: the kit only matched its own stamp - never "ok".
        alone = subprocess.run(doctor + ['--installed-version', self.version],
                               cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(json.loads(alone.stdout)['kernel_kit']['status'], 'opportunity')

    def test_damaged_copy_is_caught(self):
        self.install(tier='core')
        target = self.root / KIT / 'tools/mint_run_id.py'
        target.write_text(target.read_text() + '\n# edited by hand\n')
        (self.root / KIT / 'schemas/results.schema.json').unlink()
        p = self.kit('check', '--campus-root', '.', '--installed-version', self.version, '--json')
        self.assertEqual(p.returncode, 1)
        r = json.loads(p.stdout)
        self.assertEqual(r['mismatched'], ['tools/mint_run_id.py'])
        self.assertEqual(r['missing'], ['schemas/results.schema.json'])

    def test_version_compare_and_forward_only(self):
        self.install(tier='core')
        r = json.loads(self.kit('check', '--campus-root', '.', '--installed-version', '999.0.0', '--json').stdout)
        self.assertEqual(r['version'], 'stale')
        r = json.loads(self.kit('check', '--campus-root', '.', '--installed-version', '0.0.1', '--json').stdout)
        self.assertEqual(r['version'], 'newer')
        stamp = self.root / KIT / 'KIT.json'
        data = json.loads(stamp.read_text())
        data['kernel_version'] = '999.0.0'
        stamp.write_text(json.dumps(data))
        p = self.kit('install', '--kernel', self.kernel, '--campus-root', self.root, kernel=self.kernel)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn('never downgrade', p.stderr)

    def tamper(self, version=None):
        # What a hostile campus writer does: edit a tool AND recompute its hash in KIT.json.
        import hashlib
        tool = self.root / KIT / 'tools/mint_run_id.py'
        tool.write_text(tool.read_text() + '\nPAYLOAD = True\n')
        stamp = self.root / KIT / 'KIT.json'
        data = json.loads(stamp.read_text())
        data['files']['tools/mint_run_id.py'] = hashlib.sha256(tool.read_bytes()).hexdigest()
        if version:
            data['kernel_version'] = version
        stamp.write_text(json.dumps(data))
        return tool

    def test_recomputed_stamp_does_not_fool_the_plugin_anchored_check(self):
        self.install(tier='core')
        self.tamper()
        alone = json.loads(self.kit('check', '--campus-root', '.', '--json').stdout)
        self.assertTrue(alone['ok'], 'without the plugin manifest only damage is caught, by design')
        p = self.kit('check', '--campus-root', '.', '--json', '--manifest', self.kernel / 'tools/kit-manifest.json',
                     kernel=self.kernel)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)['mismatched'], ['tools/mint_run_id.py'])
        doctor = subprocess.run([sys.executable, str(self.kernel / 'tools/doctor_evidence.py'), '--campus-root',
                                 str(self.root), '--json', '--today', '2026-10-21'],
                                env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(json.loads(doctor.stdout)['kernel_kit']['status'], 'needs-decision')

    def test_planted_newer_stamp_is_not_trusted_and_repair_heals_it(self):
        self.install(tier='core')
        tool = self.tamper(version='999.0.0')
        r = json.loads(self.kit('check', '--campus-root', '.', '--json', '--manifest',
                                self.kernel / 'tools/kit-manifest.json', kernel=self.kernel).stdout)
        self.assertFalse(r['ok'])
        self.assertEqual(r['version'], 'newer')
        refused = self.kit('install', '--kernel', self.kernel, '--campus-root', self.root, kernel=self.kernel)
        self.assertEqual(refused.returncode, 1)
        self.assertIn('--repair', refused.stderr)
        healed = self.kit('install', '--kernel', self.kernel, '--campus-root', self.root, '--repair', kernel=self.kernel)
        self.assertEqual(healed.returncode, 0, healed.stderr)
        self.assertNotIn('PAYLOAD', tool.read_text())
        r = json.loads(self.kit('check', '--campus-root', '.', '--json', '--manifest',
                                self.kernel / 'tools/kit-manifest.json', kernel=self.kernel).stdout)
        self.assertTrue(r['ok'], r)

    def test_install_never_writes_through_a_symlink(self):
        outside = self.base / 'outside'
        outside.mkdir()
        victim = outside / 'victim.txt'
        victim.write_text('owner data\n')
        kit = self.root / KIT
        cases = (('KIT.json', victim), ('tools', outside), ('', outside))
        for rel, target in cases:
            with self.subTest(link=rel or KIT):
                if kit.exists() or kit.is_symlink():
                    shutil.rmtree(kit) if kit.is_dir() and not kit.is_symlink() else kit.unlink()
                link = kit / rel if rel else kit
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target)
                p = self.kit('install', '--kernel', self.kernel, '--campus-root', self.root, kernel=self.kernel)
                self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
                self.assertIn('symlink', p.stderr)
                self.assertEqual(victim.read_text(), 'owner data\n')
                self.assertEqual(sorted(x.name for x in outside.iterdir()), ['victim.txt'])
                link.unlink()

    def test_check_counts_a_linked_kit_file_as_changed(self):
        self.install(tier='core')
        tool = self.root / KIT / 'tools/contract.py'
        tool.unlink()
        tool.symlink_to(self.kernel / 'tools/contract.py')  # same bytes, but not a real kit file
        r = json.loads(self.kit('check', '--campus-root', '.', '--json').stdout)
        self.assertEqual(r['mismatched'], ['tools/contract.py'])

    def anchored_check(self, *extra):
        p = self.kit('check', '--campus-root', '.', '--json', '--manifest', self.kernel / 'tools/kit-manifest.json',
                     *extra, kernel=self.kernel)
        return p.returncode, json.loads(p.stdout)

    def plant_bytecode(self, module, marker):
        # Codex audit F1, probe 2: a cache stamped with the real source's mtime and size, so Python
        # would load it instead of the checked source.
        import importlib._bootstrap_external as ext
        src = self.root / KIT / 'tools' / f'{module}.py'
        st = src.stat()
        code = compile(f'open({str(marker)!r}, "w").write("ran")\n', str(src), 'exec')
        pyc = src.parent / '__pycache__' / f'{module}.{sys.implementation.cache_tag}.pyc'  # where Python looks by default
        pyc.parent.mkdir(exist_ok=True)
        pyc.write_bytes(ext._code_to_timestamp_pyc(code, int(st.st_mtime), st.st_size))
        return pyc

    def test_unlisted_module_fails_the_anchored_check_and_never_runs(self):
        # Codex audit F1, probe 1: a planted stdlib-named module next to the minter.
        self.install(tier='all')
        marker = self.base / 'MODULE_EXECUTED'
        (self.root / KIT / 'tools/secrets.py').write_text(f'open({str(marker)!r}, "w").write("ran")\n')
        rc, r = self.anchored_check('--tier', 'all')
        self.assertEqual(rc, 1)
        self.assertEqual(r['unexpected'], ['tools/secrets.py'])
        # The canon runs kit tools as `python3 -I -B`: the kit folder is never searched first.
        mint = subprocess.run([sys.executable, '-I', '-B', str(self.root / KIT / 'tools/mint_run_id.py'), 'mint', 'x',
                               '--team', 't', '--campus-root', '.'], cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(mint.returncode, 0, mint.stderr)
        self.assertFalse(marker.exists(), 'a planted module ran under -I')
        doctor = subprocess.run([sys.executable, str(self.kernel / 'tools/doctor_evidence.py'), '--campus-root',
                                 str(self.root), '--json', '--today', '2026-10-22'],
                                env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(json.loads(doctor.stdout)['kernel_kit']['status'], 'needs-decision')

    def test_planted_bytecode_fails_the_check_and_is_never_loaded(self):
        self.install(tier='all')
        marker = self.base / 'BYTECODE_EXECUTED'
        pyc = self.plant_bytecode('contract', marker)
        rc, r = self.anchored_check('--tier', 'all')
        self.assertEqual(rc, 1)
        rel = pyc.relative_to(self.root / KIT).as_posix()
        self.assertIn(rel, r['unexpected'])
        self.assertIn('tools/__pycache__/', r['unexpected'])
        # Even if someone skips the check, the kit's importers never read a cache from the kit.
        for tool, args in (('doctor_evidence.py', ['--campus-root', '.', '--json', '--today', '2026-10-22']),
                           ('resolve_context.py', ['--find-campus', '--json'])):
            with self.subTest(tool=tool):
                subprocess.run([sys.executable, '-I', '-B', str(self.root / KIT / 'tools' / tool), *args],
                               cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
                self.assertFalse(marker.exists(), f'{tool} loaded a planted cache')
        self.assertEqual(pyc.read_bytes()[:4], importlib_magic(), 'nothing rewrote the planted cache')

    def test_repair_quarantines_unlisted_files_and_the_kit_checks_again(self):
        self.install(tier='all')
        (self.root / KIT / 'tools/secrets.py').write_text('x = 1\n')
        self.plant_bytecode('contract', self.base / 'never')
        p = self.kit('install', '--kernel', self.kernel, '--campus-root', self.root, '--tier', 'all', '--repair',
                     kernel=self.kernel)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertIn('tools/secrets.py', out['quarantined'])
        self.assertTrue((Path(out['quarantine_dir']) / 'tools/secrets.py').is_file(), 'moved, never deleted')
        rc, r = self.anchored_check('--tier', 'all')
        self.assertEqual(rc, 0, r)
        self.assertEqual(r['unexpected'], [])

    def test_quarantine_never_follows_a_link_out_of_the_campus(self):
        # 5.2.17: a planted link at .campus-os/kernel-quarantine sent repair's moves outside the
        # campus, into a folder the planter chose, under file names the planter chose.
        self.install(tier='core')
        outside = self.base / 'outside'
        outside.mkdir()
        (self.root / KIT / 'tools/authorized_keys').write_text('planted\n')
        (self.root / '.campus-os/kernel-quarantine').symlink_to(outside)
        p = self.kit('install', '--kernel', self.kernel, '--campus-root', self.root, '--repair', kernel=self.kernel)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn('symlink', p.stderr)
        self.assertEqual(list(outside.iterdir()), [], 'nothing was moved outside the campus')
        self.assertTrue((self.root / KIT / 'tools/authorized_keys').is_file(), 'left in place for the owner')
        rc, r = self.anchored_check()
        self.assertEqual(rc, 1)
        self.assertIn('tools/authorized_keys', r['unexpected'])

    def test_each_quarantine_gets_a_fresh_unguessable_folder(self):
        self.install(tier='core')
        dirs = []
        for _ in range(2):
            (self.root / KIT / 'tools/extra.py').write_text('x\n')
            p = self.kit('install', '--kernel', self.kernel, '--campus-root', self.root, kernel=self.kernel)
            self.assertEqual(p.returncode, 0, p.stderr)
            dirs.append(Path(json.loads(p.stdout)['quarantine_dir']))
        self.assertNotEqual(dirs[0], dirs[1])
        for d in dirs:
            self.assertRegex(d.name, r'^\d{8}T\d{6}Z-[0-9a-f]{12}$')
            self.assertEqual(d.parent, (self.root / '.campus-os/kernel-quarantine').resolve())

    def test_a_changed_on_demand_file_fails_even_a_core_check(self):
        # Codex observation 1: the doctor's line said "every file" while checking core only.
        self.install(tier='all')
        weight = self.root / KIT / 'tools/context-weight.mjs'
        weight.write_text(weight.read_text() + '\n// edited\n')
        rc, r = self.anchored_check()
        self.assertEqual(rc, 1)
        self.assertEqual(r['mismatched'], ['tools/context-weight.mjs'])

    def test_a_malformed_stamp_is_reported_not_raised(self):
        self.install(tier='core')
        stamp = self.root / KIT / 'KIT.json'
        data = json.loads(stamp.read_text())
        data['tiers']['core'] = [1, None]
        stamp.write_text(json.dumps(data))
        p = self.kit('check', '--campus-root', '.', '--json')
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertTrue(json.loads(p.stdout)['stamp_invalid'])

    def test_reinstall_copies_only_what_changed(self):
        self.install(tier='core')
        self.assertEqual(self.install(tier='core')['copied'], [])

    def test_doctor_reports_a_missing_kit_as_an_opportunity(self):
        p = subprocess.run([sys.executable, str(self.kernel / 'tools/doctor_evidence.py'), '--campus-root', str(self.root),
                            '--json', '--today', '2026-10-21'], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(json.loads(p.stdout)['kernel_kit']['status'], 'opportunity', p.stderr)


if __name__ == '__main__':
    unittest.main()
