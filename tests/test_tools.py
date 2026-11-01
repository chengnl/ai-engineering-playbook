import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / f'{name}.py')
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


bootstrap = module('bootstrap')
check = module('check')
verify = module('verify')


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.dest = self.base / 'project'

    def test_new_project_is_pinned_and_does_not_run_or_init_git(self):
        result = bootstrap.bootstrap(self.dest, 'sample')
        self.assertTrue(result['needs_adaptation'])
        self.assertFalse((self.dest / '.git').exists())
        cfg = json.loads((self.dest / '.engineering/project.json').read_text())
        self.assertEqual(cfg['project_name'], 'sample')
        self.assertEqual(cfg['status'], 'needs-adaptation')
        manifest = json.loads((self.dest / '.engineering/manifest.json').read_text())
        self.assertEqual(manifest['playbook_version'], (ROOT / 'VERSION').read_text().strip())
        self.assertEqual([], check.check_docs(self.dest))
        self.assertFalse((self.dest / '.github').exists())

    def test_existing_agent_entry_is_not_overwritten_or_partially_adopted(self):
        self.dest.mkdir()
        (self.dest / 'AGENTS.md').write_text('existing rules')
        with self.assertRaises(ValueError):
            bootstrap.bootstrap(self.dest, 'sample')
        self.assertEqual('existing rules', (self.dest / 'AGENTS.md').read_text())
        self.assertFalse((self.dest / '.engineering').exists())

    def test_existing_project_and_readmes_preserved_with_snippet(self):
        (self.dest / 'docs').mkdir(parents=True)
        for name in ['AGENTS.md', 'README.md', 'docs/README.md', 'app.py']:
            (self.dest / name).write_text('original ' + name)
        bootstrap.bootstrap(self.dest, 'sample', True)
        for name in ['AGENTS.md', 'README.md', 'docs/README.md', 'app.py']:
            self.assertEqual('original ' + name, (self.dest / name).read_text())
        self.assertTrue((self.dest / '.engineering/AGENTS.snippet.md').exists())

    def test_second_run_does_not_overwrite_local_adaptation(self):
        bootstrap.bootstrap(self.dest, 'sample')
        profile = self.dest / '.engineering/project.json'
        profile.write_text('local edits')
        with self.assertRaises(ValueError):
            bootstrap.bootstrap(self.dest, 'another')
        self.assertEqual('local edits', profile.read_text())

    def test_destination_symlink_and_nested_symlink_rejected(self):
        self.dest.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            bootstrap.bootstrap(self.dest / 'nested', 'sample')

    def test_existing_docs_symlink_rejected_before_writing(self):
        self.dest.mkdir()
        (self.dest / 'docs').symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            bootstrap.bootstrap(self.dest, 'sample')
        self.assertFalse((self.dest / '.engineering').exists())

    def test_mid_write_failure_rolls_back_own_files_and_preserves_existing(self):
        self.dest.mkdir()
        (self.dest / 'docs').mkdir()
        marker = self.dest / 'business.txt'
        marker.write_text('keep')
        original = Path.open

        def fail_manifest(path, mode='r', *args, **kwargs):
            if path.name == 'manifest.json' and mode == 'xb':
                raise OSError('synthetic write failure')
            return original(path, mode, *args, **kwargs)

        with patch.object(Path, 'open', fail_manifest):
            with self.assertRaises(OSError):
                bootstrap.bootstrap(self.dest, 'sample')
        self.assertEqual('keep', marker.read_text())
        self.assertEqual(['business.txt', 'docs'], sorted(p.name for p in self.dest.iterdir()))

    def test_existing_initializer_lock_is_not_removed(self):
        self.dest.mkdir()
        lock = self.dest / '.playbook-init.lock'
        lock.write_text('another initializer')
        with self.assertRaises(FileExistsError):
            bootstrap.bootstrap(self.dest, 'sample')
        self.assertEqual('another initializer', lock.read_text())

    def test_invalid_name_rejected(self):
        with self.assertRaises(ValueError):
            bootstrap.bootstrap(self.dest, 'bad\nname')


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        (self.base / 'spec.md').write_text('# feature')
        (self.base / 'evidence.md').write_text('synthetic fixture, not a production result')
        self.data = json.loads((ROOT / 'templates/change.json').read_text())
        self.path = self.base / 'change.json'

    def errors(self, data=None):
        self.path.write_text(json.dumps(self.data if data is None else data))
        return check.trace_errors(self.path)

    def test_draft_requires_structure_but_not_passed_evidence(self):
        self.assertEqual([], self.errors())

    def test_completed_requires_done_and_passed_evidence(self):
        self.data['status'] = 'completed'
        self.assertTrue(self.errors())
        self.data['tasks'][0]['status'] = 'done'
        self.data['acceptance'][0].update(result='passed', evidence=['evidence.md'])
        self.assertEqual([], self.errors())

    def test_unknown_and_uncovered_requirements_rejected(self):
        self.data['tasks'][0]['requirements'] = ['R-99']
        self.assertTrue(any('unknown' in e for e in self.errors()))
        self.assertTrue(any('without coverage' in e for e in self.errors()))

    def test_duplicate_ids_rejected(self):
        self.data['requirements'].append(copy.deepcopy(self.data['requirements'][0]))
        self.assertTrue(any('duplicate' in e for e in self.errors()))

    def test_missing_outside_and_symlink_evidence_rejected(self):
        self.data['acceptance'][0].update(result='passed', evidence=['../outside.md'])
        self.assertTrue(self.errors())
        (self.base / 'link.md').symlink_to(self.base / 'evidence.md')
        self.data['acceptance'][0]['evidence'] = ['link.md']
        self.assertTrue(self.errors())

    def test_malformed_json_and_wrong_root_do_not_crash(self):
        self.path.write_text('{broken')
        self.assertTrue(check.trace_errors(self.path))
        self.assertTrue(self.errors([]))

    def test_invalid_status_types_return_errors(self):
        for key in ['status', 'level']:
            data = copy.deepcopy(self.data)
            data[key] = []
            self.assertTrue(self.errors(data))
        self.data['acceptance'][0]['result'] = []
        self.assertTrue(self.errors())

    def test_skipped_acceptance_cannot_complete(self):
        self.data.update(status='completed')
        self.data['tasks'][0]['status'] = 'done'
        self.data['acceptance'][0].update(result='skipped', evidence=['evidence.md'])
        self.assertTrue(self.errors())

    def test_file_links_missing_absolute_and_encoded_paths(self):
        page = self.base / 'README.md'
        (self.base / 'with space.md').write_text('# target')
        page.write_text('[valid](with%20space.md) [external](https://example.invalid)')
        self.assertEqual([], check.check_docs(self.base))
        page.write_text('[missing](missing.md) [absolute](/tmp/file)')
        self.assertEqual(2, len(check.check_docs(self.base)))


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        (self.base / '.engineering').mkdir()
        self.cfg = {'status': 'ready', 'checks': {'offline': []}}

    def write(self):
        (self.base / '.engineering/project.json').write_text(json.dumps(self.cfg))

    def command(self, code):
        return {'argv': [sys.executable, '-c', code], 'timeout_seconds': 5, 'purpose': 'isolated synthetic test'}

    def test_unconfigured_and_unadapted_project_cannot_pass(self):
        self.write()
        with self.assertRaises(ValueError):
            verify.run_checks(self.base, 'offline')
        self.cfg.update(status='needs-adaptation')
        self.cfg['checks']['offline'] = [self.command('pass')]
        self.write()
        with self.assertRaises(ValueError):
            verify.run_checks(self.base, 'offline')

    def test_success_runs_in_project_directory(self):
        self.cfg['checks']['offline'] = [self.command("from pathlib import Path; Path('marker').write_text('ok')")]
        self.write()
        self.assertEqual(0, verify.run_checks(self.base, 'offline'))
        self.assertEqual('ok', (self.base / 'marker').read_text())

    def test_nonzero_stops_following_commands(self):
        self.cfg['checks']['offline'] = [self.command('raise SystemExit(3)'), self.command("open('bad','w').close()")]
        self.write()
        self.assertEqual(1, verify.run_checks(self.base, 'offline'))
        self.assertFalse((self.base / 'bad').exists())

    def test_all_preflight_rejects_missing_group_before_any_command(self):
        self.cfg['checks'] = {'offline': [self.command("open('bad','w').close()")], 'database': []}
        self.write()
        with self.assertRaises(ValueError):
            verify.run_checks(self.base, 'all')
        self.assertFalse((self.base / 'bad').exists())

    def test_shell_string_and_unbounded_timeout_rejected(self):
        for command in [{'argv': 'echo unsafe', 'timeout_seconds': 5, 'purpose': 'test'}, {'argv': ['echo'], 'timeout_seconds': 0, 'purpose': 'test'}]:
            self.cfg['checks']['offline'] = [command]
            self.write()
            with self.assertRaises(ValueError):
                verify.run_checks(self.base, 'offline')

    def test_timeout_is_nonzero(self):
        command = self.command('import time; time.sleep(20)')
        command['timeout_seconds'] = 1
        self.cfg['checks']['offline'] = [command]
        self.write()
        self.assertEqual(124, verify.run_checks(self.base, 'offline'))

    def test_non_object_configuration_is_rejected(self):
        (self.base / '.engineering/project.json').write_text('[]')
        with self.assertRaises(ValueError):
            verify.run_checks(self.base, 'offline')

    def test_cli_missing_profile_returns_nonzero(self):
        result = subprocess.run([sys.executable, str(ROOT / 'tools/verify.py'), '--project', str(self.base / 'missing'), '--group', 'offline'], capture_output=True)
        self.assertEqual(2, result.returncode)


if __name__ == '__main__':
    unittest.main()
