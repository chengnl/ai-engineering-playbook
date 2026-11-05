"""Acceptance regressions for the three v0.1 review findings; no business resources."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify
import check


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / '.engineering').mkdir()

    def test_unsupported_and_incomplete_profile_rejected_before_execution(self):
        config = {'schema_version': 999, 'status': 'ready', 'checks': {'offline': [{'argv': [sys.executable, '-c', "open('should-not-run','w').close()"], 'purpose': 'synthetic', 'timeout_seconds': 2}]}}
        (self.root / '.engineering/project.json').write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            verify.run_checks(self.root, 'offline')
        self.assertFalse((self.root / 'should-not-run').exists())

    def test_completed_empty_legacy_evidence_rejected(self):
        (self.root / 'spec.md').write_text('R-01 read authorized records')
        (self.root / 'empty.md').write_text('')
        data = {'schema_version': 1, 'id': 'review', 'level': 'standard', 'status': 'completed', 'spec': 'spec.md', 'requirements': [{'id': 'R-01', 'text': 'read authorized records'}], 'tasks': [{'id': 'T-01', 'requirements': ['R-01'], 'status': 'done'}], 'acceptance': [{'id': 'A-01', 'requirements': ['R-01'], 'result': 'passed', 'evidence': ['empty.md']}]}
        path = self.root / 'change.json';path.write_text(json.dumps(data))
        self.assertTrue(check.trace_errors(path))


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        from support import project
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.cfg = project(self.root)

    def run_config(self):
        from support import write
        write(self.root, self.cfg)
        return verify.run_checks(self.root, 'offline')

    def test_each_required_field_and_placeholder_rejected(self):
        import copy
        original = copy.deepcopy(self.cfg)
        for key in ['project_name', 'business_description', 'environment_policy', 'git_policy', 'ci_policy', 'test_resource_cleanup', 'knowledge_entry', 'applicable_standards', 'source_paths', 'environment', 'stack']:
            for value in [None, '待填写']:
                self.cfg = copy.deepcopy(original);self.cfg[key] = value
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError):self.run_config()

    def test_explicit_non_applicability_and_all_behavior(self):
        self.cfg['checks']['database'] = {'not_applicable_reason': 'No persistence in this fixture'}
        from support import write
        write(self.root, self.cfg)
        self.assertEqual(0, verify.run_checks(self.root, 'all'))
        with self.assertRaises(ValueError):verify.run_checks(self.root, 'database')

    def test_isolated_resources_require_ownership_and_both_hooks(self):
        self.cfg['checks']['offline'][0]['resources'] = {'mode': 'isolated', 'ownership': 'this fixture only'}
        with self.assertRaises(ValueError):self.run_config()

    def test_production_environment_cannot_execute(self):
        self.cfg['environment']['classification'] = 'production'
        with self.assertRaises(ValueError):self.run_config()

    def test_missing_knowledge_and_standard_rejected(self):
        (self.root / 'docs/README.md').unlink()
        with self.assertRaises(ValueError):self.run_config()

    def test_duplicate_command_ids_rejected(self):
        self.cfg['checks']['offline'].append(self.cfg['checks']['offline'][0].copy())
        with self.assertRaises(ValueError):self.run_config()

    def test_evidence_cannot_overlap_source_or_escape(self):
        from support import write
        write(self.root, self.cfg)
        for target in ['src/evidence', '../outside']:
            with self.assertRaises(ValueError):verify.run_checks(self.root, 'offline', target)


class ResourceLifecycleTests(unittest.TestCase):
    def setUp(self):
        from support import project
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.cfg = project(self.root)

    def run_command(self, code, cleanup=None, residual=None, timeout=5):
        from support import command, write
        item = command(code)
        item['timeout_seconds'] = timeout
        item['resources'] = {'mode': 'isolated', 'ownership': 'owned.resource under this test-only temporary root', 'cleanup': command(cleanup or "from pathlib import Path; Path('owned.resource').unlink(missing_ok=True)"), 'residual_check': command(residual or "from pathlib import Path; assert not Path('owned.resource').exists()")}
        self.cfg['checks']['offline'] = [item]
        write(self.root, self.cfg)
        return verify.run_checks(self.root, 'offline')

    def test_failure_still_cleans_and_checks_residual(self):
        self.assertEqual(1, self.run_command("from pathlib import Path; Path('owned.resource').write_text('synthetic'); raise SystemExit(4)"))
        self.assertFalse((self.root / 'owned.resource').exists())
        record = json.loads(next((self.root / 'var/check-evidence').glob('*.json')).read_text())
        self.assertEqual('passed', record['resources']['cleanup']['result'])
        self.assertEqual('passed', record['resources']['residual_check']['result'])

    @unittest.skipIf(sys.platform == 'win32', 'POSIX graceful process-group behavior')
    def test_timeout_allows_sigterm_handler_before_cleanup_hook(self):
        code="import signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,lambda *_:(Path('grace.marker').write_text('handled'),exit(0))); Path('owned.resource').write_text('synthetic'); time.sleep(30)"
        self.assertEqual(124, self.run_command(code, timeout=1))
        self.assertTrue((self.root / 'grace.marker').exists())
        self.assertFalse((self.root / 'owned.resource').exists())

    @unittest.skipIf(sys.platform == 'win32', 'POSIX escalation')
    def test_ignored_sigterm_escalates_but_cleanup_still_runs(self):
        code="import signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path('owned.resource').write_text('synthetic'); time.sleep(30)"
        self.assertEqual(124, self.run_command(code, timeout=1))
        record = json.loads(next((self.root / 'var/check-evidence').glob('*.json')).read_text())
        self.assertEqual('forced', record['execution']['termination'])
        self.assertFalse((self.root / 'owned.resource').exists())

    def test_cleanup_failure_cannot_pass_and_residual_still_runs(self):
        self.assertEqual(1, self.run_command("from pathlib import Path; Path('owned.resource').write_text('synthetic')", cleanup='raise SystemExit(5)', residual="from pathlib import Path; Path('residual.ran').write_text('yes'); assert not Path('owned.resource').exists()"))
        self.assertTrue((self.root / 'residual.ran').exists())

    def test_residual_failure_cannot_pass(self):
        self.assertEqual(1, self.run_command('pass', residual='raise SystemExit(6)'))

    def test_unconfirmed_shutdown_still_runs_hooks_and_cannot_pass(self):
        from unittest.mock import patch
        import process_runner
        original = process_runner.stop_process
        def denied_after_test_child_exit(process, grace):
            original(process, grace)  # This synthetic test never leaks a running child.
            raise PermissionError('synthetic unconfirmed shutdown')
        with patch.object(process_runner, 'stop_process', denied_after_test_child_exit):
            self.assertEqual(1, self.run_command("from pathlib import Path; import time; Path('owned.resource').write_text('synthetic'); time.sleep(30)", timeout=1))
        self.assertFalse((self.root / 'owned.resource').exists())
        record = json.loads(next((self.root / 'var/check-evidence').glob('*.json')).read_text())
        self.assertEqual('termination-failed', record['execution']['result'])
        self.assertEqual('unconfirmed', record['execution']['termination'])
        self.assertEqual('passed', record['resources']['cleanup']['result'])
        self.assertEqual('passed', record['resources']['residual_check']['result'])
        self.assertNotEqual('passed', record['result'])

    def test_missing_executable_still_runs_hooks(self):
        from support import write
        self.cfg['checks']['offline'][0].update(argv=['/definitely/not/a/real/program'], resources={'mode':'isolated','ownership':'test-owned marker','cleanup':{'argv':[sys.executable,'-c',"from pathlib import Path; Path('cleanup.ran').touch()"],'timeout_seconds':3},'residual_check':{'argv':[sys.executable,'-c','pass'],'timeout_seconds':3}})
        write(self.root,self.cfg)
        self.assertEqual(1,verify.run_checks(self.root,'offline'))
        self.assertTrue((self.root/'cleanup.ran').exists())


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        from support import project
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.cfg = project(self.root)
        (self.root/'spec.md').write_text('# Authorized read\nR-01 read only owned records\n')
        self.data = json.loads((ROOT/'templates/change.json').read_text())
        self.data.update(id='complete-demo',status='completed')
        self.data['requirements'][0]['text']='Read only owned records'
        self.data['tasks'][0]['status']='done'
        self.data['acceptance'][0]['result']='passed'
        self.path=self.root/'change.json'

    def evidence(self):
        from support import evidence
        reference=evidence(self.root)
        self.data['acceptance'][0]['evidence']=[reference]
        self.path.write_text(json.dumps(self.data))
        return self.root/reference['path']

    def errors(self):
        self.path.write_text(json.dumps(self.data))
        return check.trace_errors(self.path,self.root)

    def test_actual_generated_evidence_completes_change(self):
        self.evidence();self.assertEqual([],self.errors())

    def test_empty_and_plain_text_evidence_rejected(self):
        record=self.evidence()
        for content in ['', 'claimed passed without a record']:
            record.write_text(content);self.assertTrue(self.errors())

    def test_missing_metadata_and_failure_evidence_rejected(self):
        record=self.evidence();original=json.loads(record.read_text())
        for key in ['source','started_at','finished_at','environment','execution','run_id']:
            mutated=original.copy();mutated.pop(key);record.write_text(json.dumps(mutated));self.assertTrue(self.errors(),key)
        original['result']='failed';record.write_text(json.dumps(original));self.assertTrue(self.errors())

    def test_source_config_and_spec_drift_rejected(self):
        self.evidence()
        source=self.root/'src/logic.py';old=source.read_text();source.write_text('VALUE=2\n');self.assertTrue(self.errors());source.write_text(old)
        spec=self.root/'spec.md';spec.write_text('changed scope');self.assertTrue(self.errors())

    def test_changed_configuration_invalidates_old_evidence(self):
        from support import write
        self.evidence();self.cfg['ci_policy']='Changed local policy';write(self.root,self.cfg);self.assertTrue(self.errors())

    def test_project_context_required_for_completed(self):
        self.evidence();self.assertTrue(check.trace_errors(self.path))

    def test_wrong_check_id_and_placeholder_requirement_rejected(self):
        self.evidence();self.data['acceptance'][0]['evidence'][0]['check_id']='different';self.assertTrue(self.errors())
        self.data['requirements'][0]['text']='待填写';self.assertTrue(self.errors())


class ProcessProbeTests(unittest.TestCase):
    @unittest.skipIf(sys.platform == 'win32', 'POSIX group liveness probe')
    def test_transient_probe_denial_waits_for_confirmed_exit(self):
        from unittest.mock import Mock, patch
        import process_runner
        process = Mock(pid=12345)
        process.poll.return_value = 0
        with patch.object(process_runner.os, 'killpg', side_effect=[None, PermissionError(), ProcessLookupError()]) as kill:
            self.assertEqual('graceful', process_runner.stop_process(process, 1))
        self.assertEqual(3, kill.call_count)
        process.wait.assert_called_once()

    @unittest.skipIf(sys.platform == 'win32', 'POSIX group signal authorization')
    def test_probe_and_final_signal_denial_never_report_graceful_exit(self):
        from unittest.mock import Mock, patch
        import process_runner
        process = Mock(pid=12345)
        process.poll.return_value = None
        # Initial TERM is allowed. Repeated probe denial and denied final KILL
        # cannot be converted into a successful shutdown.
        def deny_after_term(_pid, signum):
            import signal
            if signum != signal.SIGTERM:
                raise PermissionError('synthetic denial')
        with patch.object(process_runner.os, 'killpg', side_effect=deny_after_term), patch.object(process_runner.time, 'monotonic', side_effect=[0, 0, 0, 2]):
            with self.assertRaises(PermissionError):
                process_runner.stop_process(process, 1)
        process.wait.assert_not_called()


class InterruptAndDriftTests(unittest.TestCase):
    def setUp(self):
        from support import project
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.cfg=project(self.root)

    @unittest.skipIf(sys.platform=='win32','POSIX supervisor SIGTERM contract')
    def test_terminating_verifier_still_cleans_owned_resources(self):
        import subprocess,time
        from support import command,write
        item=command("from pathlib import Path; import time; Path('owned.resource').write_text('synthetic'); Path('started').touch(); time.sleep(30)")
        item['resources']={'mode':'isolated','ownership':'this unique temporary root only','cleanup':command("from pathlib import Path; Path('owned.resource').unlink(missing_ok=True)"),'residual_check':command("from pathlib import Path; assert not Path('owned.resource').exists()")}
        self.cfg['checks']['offline']=[item];write(self.root,self.cfg)
        process=subprocess.Popen([sys.executable,str(ROOT/'tools/verify.py'),'--project',str(self.root),'--group','offline'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+5
            while not (self.root/'started').exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(0.02)
            self.assertTrue((self.root/'started').exists())
            process.terminate();self.assertEqual(124,process.wait(timeout=10))
            self.assertFalse((self.root/'owned.resource').exists())
            record=json.loads(next((self.root/'var/check-evidence').glob('*.json')).read_text())
            self.assertEqual('interrupted',record['execution']['result'])
            self.assertEqual('passed',record['resources']['cleanup']['result'])
        finally:
            if process.poll() is None:process.kill();process.wait()

    def test_commands_mutating_declared_source_do_not_pass(self):
        from support import command,write
        self.cfg['checks']['offline']=[command("from pathlib import Path; Path('src/logic.py').write_text('VALUE = 99')")]
        write(self.root,self.cfg)
        self.assertEqual(1,verify.run_checks(self.root,'offline'))
        record=json.loads(next((self.root/'var/check-evidence').glob('*.json')).read_text())
        self.assertEqual('inputs-changed',record['result'])
