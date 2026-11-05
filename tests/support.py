"""Isolated synthetic project fixtures, never shared business environments."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def command(code='pass', identifier='offline-tests'):
    return {'id': identifier, 'argv': [sys.executable, '-c', code], 'timeout_seconds': 5, 'grace_seconds': 1, 'purpose': 'isolated synthetic regression', 'resources': {'mode': 'none', 'reason': 'only fixture files managed by TemporaryDirectory'}}


def project(root):
    root = Path(root)
    (root / '.engineering/standards').mkdir(parents=True, exist_ok=True)
    for name in ['collaboration', 'testing', 'security-operations', 'documentation']:
        (root / '.engineering/standards' / (name + '.md')).write_text('# Synthetic fixture standard\n')
    (root / 'src').mkdir(exist_ok=True)
    (root / 'src/logic.py').write_text('VALUE = 1\n')
    (root / 'docs').mkdir(exist_ok=True)
    (root / 'docs/README.md').write_text('# Synthetic project knowledge\n')
    cfg = json.loads((ROOT / 'templates/project.json').read_text())
    cfg.update(status='ready', project_name='synthetic-project', business_description='An isolated regression fixture', stack={key: {'technology': 'none', 'reason': 'fixture exercises governance tools only'} for key in ['backend', 'frontend', 'database']}, business_boundaries=['No business data, network or production access'], source_paths=['src'], environment={'classification': 'test', 'label': 'temporary-fixture', 'production_access': 'forbidden'}, environment_policy='Only temporary local synthetic resources', git_policy='No automatic commits or publication', ci_policy='Local regression only', test_resource_cleanup='TemporaryDirectory removes this test-owned root', checks={'offline': [command()]})
    write(root, cfg)
    return cfg


def write(root, cfg):
    (Path(root) / '.engineering/project.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def evidence(root, spec='spec.md'):
    import verify
    result = verify.run_checks(root, 'offline', 'evidence', spec)
    if result:
        raise AssertionError('synthetic evidence command failed')
    path = sorted((Path(root) / 'evidence').glob('*.json'))[-1]
    return {'kind': 'automated', 'check_id': 'offline-tests', 'path': str(path.relative_to(root))}
