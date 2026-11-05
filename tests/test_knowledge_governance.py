"""New knowledge scaffolding and non-destructive adoption; no application resources."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load('bootstrap')
check = load('check')


class KnowledgeBootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.dest = self.base / 'project'

    def test_new_project_has_versioned_classification_and_valid_local_links(self):
        bootstrap.bootstrap(self.dest, 'synthetic')
        self.assertEqual([], check.check_docs(self.dest))
        expected = {'modules', 'ai', 'operations', 'guides', 'experiments', 'architecture',
                    'plans', 'acceptance', 'releases', 'deployment', 'incidents'}
        self.assertEqual(expected, {p.name for p in (self.dest / 'docs').iterdir() if p.is_dir()})
        self.assertTrue((self.dest / '.engineering/standards/documentation.md').exists())
        self.assertFalse((self.dest / 'docs/database.md').exists(), 'No invented database knowledge')
        manifest = json.loads((self.dest / '.engineering/manifest.json').read_text())
        for path in (self.dest / 'docs').rglob('*.md'):
            key = str(path.relative_to(self.dest))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest['files'][key])
        config = json.loads((self.dest / '.engineering/project.json').read_text())
        self.assertIn('documentation', config['applicable_standards'])

    def test_v02_schema_two_profile_remains_valid_without_new_standard_selection(self):
        from support import project, write
        from project_contract import load_profile
        config = project(self.dest)
        config['playbook_version'] = '0.2.0'
        config['applicable_standards'].remove('documentation')
        (self.dest / '.engineering/standards/documentation.md').unlink()
        write(self.dest, config)
        loaded = load_profile(self.dest)
        self.assertEqual('ready', loaded['status'])
        self.assertEqual(2, loaded['schema_version'])

    def test_existing_docs_are_preserved_byte_for_byte_without_auto_classification(self):
        docs = self.dest / 'docs'
        (docs / 'legacy').mkdir(parents=True)
        data = {'README.md': b'# Original entry\n', 'legacy/record.md': b'Original facts\n'}
        for name, content in data.items():
            (docs / name).write_bytes(content)
        bootstrap.bootstrap(self.dest, 'existing')
        for name, content in data.items():
            self.assertEqual(content, (docs / name).read_bytes())
        self.assertFalse((docs / 'modules').exists())
        self.assertEqual({'README.md', 'legacy/record.md'},
                         {str(p.relative_to(docs)) for p in docs.rglob('*') if p.is_file()})

    def test_existing_docs_without_entry_get_only_non_assumptive_entry(self):
        docs = self.dest / 'docs'
        docs.mkdir(parents=True)
        (docs / 'original.md').write_text('keep')
        bootstrap.bootstrap(self.dest, 'existing')
        self.assertEqual({'README.md', 'original.md'}, {p.name for p in docs.iterdir()})
        self.assertEqual('keep', (docs / 'original.md').read_text())
        self.assertEqual([], check.check_docs(self.dest))

    def test_docs_file_or_symlink_is_rejected_before_any_governance_write(self):
        for link in [False, True]:
            with self.subTest(link=link):
                dest = self.base / ('link' if link else 'file')
                dest.mkdir()
                if link:
                    other = self.base / 'other'
                    other.mkdir()
                    (other / 'README.md').write_text('existing entry')
                    (dest / 'docs').symlink_to(other, target_is_directory=True)
                else:
                    (dest / 'docs').write_text('not a directory')
                with self.assertRaises(ValueError):
                    bootstrap.bootstrap(dest, 'existing')
                self.assertFalse((dest / '.engineering').exists())

    def test_failure_in_a_nested_index_rolls_back_only_initializer_files(self):
        self.dest.mkdir()
        marker = self.dest / 'keep.txt'
        marker.write_text('keep')
        original = Path.open

        def fail_index(path, mode='r', *args, **kwargs):
            if str(path).endswith('docs/experiments/README.md') and mode == 'xb':
                raise OSError('synthetic nested-index failure')
            return original(path, mode, *args, **kwargs)

        with patch.object(Path, 'open', fail_index):
            with self.assertRaises(OSError):
                bootstrap.bootstrap(self.dest, 'synthetic')
        self.assertEqual(['keep.txt'], sorted(p.name for p in self.dest.iterdir()))
