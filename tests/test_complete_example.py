import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class CompleteExampleTests(unittest.TestCase):
    def test_feature_and_real_failing_then_fixed_regression(self):
        spec=importlib.util.spec_from_file_location('run_demo',ROOT/'examples/complete/run_demo.py')
        demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
        with tempfile.TemporaryDirectory() as temporary:
            project=demo.run_demo(Path(temporary).resolve()/'demo')
            for name in ['scoped-list','page-size']:
                data=json.loads((project/'specs/changes'/name/'change.json').read_text())
                self.assertEqual('completed',data['status'])
            results=[json.loads(p.read_text())['result'] for p in (project/'specs/changes/page-size/evidence').glob('*.json')]
            self.assertIn('failed',results);self.assertIn('passed',results)
            with self.assertRaises(ValueError):demo.run_demo(project)
        self.assertFalse(Path(temporary).exists())
