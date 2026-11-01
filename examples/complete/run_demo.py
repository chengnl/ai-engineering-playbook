#!/usr/bin/env python3
"""Create a NEW synthetic project, exercise feature and bug-fix SDD, and generate real demo evidence."""
import argparse
import copy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from bootstrap import bootstrap
from verify import run_checks
from check import trace_errors


def check_command(identifier, pattern):
    return {'id':identifier,'argv':[sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v'],'timeout_seconds':30,'grace_seconds':2,'purpose':'Synthetic teaching project behavior regression','resources':{'mode':'none','reason':'Pure in-memory fixture assertions; project directory owned by demo caller'}}


def run_demo(destination):
    root=Path(destination).absolute()
    if root.exists() and any(root.iterdir()):
        raise ValueError('demo requires a new or empty destination; existing project content is never replaced')
    bootstrap(root,'sdd-teaching-project')
    for folder in ['src','tests','specs/changes/scoped-list','specs/changes/page-size']:
        (root/folder).mkdir(parents=True,exist_ok=True)
    (root/'src/access.py').write_text('def scoped_records(records, managed_ids):\n    return [record for record in records if record["owner_id"] in managed_ids]\n')
    (root/'tests/test_access.py').write_text('''import unittest
from src.access import scoped_records
class AccessTests(unittest.TestCase):
    def test_only_managed_records(self):
        self.assertEqual([{'owner_id':'a'}], scoped_records([{'owner_id':'a'},{'owner_id':'b'}], {'a'}))
    def test_empty_scope_returns_nothing(self):
        self.assertEqual([], scoped_records([{'owner_id':'b'}], set()))
''')
    (root/'src/paging.py').write_text('def page_size(value):\n    return min(value, 50)\n')
    (root/'tests/test_paging.py').write_text('''import unittest
from src.paging import page_size
class PagingTests(unittest.TestCase):
    def test_zero_and_negative_normalized(self):
        self.assertEqual(1,page_size(0))
        self.assertEqual(1,page_size(-3))
    def test_upper_bound(self):
        self.assertEqual(50,page_size(100))
''')
    cfg=json.loads((root/'.engineering/project.json').read_text())
    cfg.update(status='ready',business_description='A synthetic read-scope and paging teaching fixture; not an HTTP service',stack={'backend':{'technology':'Python 3 standard library CLI fixture'},'frontend':{'technology':'none','reason':'No Web interface in this teaching project'},'database':{'technology':'none','reason':'All records are synthetic in-memory values'}},source_paths=['src','tests'],business_boundaries=['Only synthetic owner IDs; no real accounts, database, network or paid model'],environment={'classification':'test','label':'isolated-sdd-demo','production_access':'forbidden'},environment_policy='Run only in this caller-owned synthetic project directory',git_policy='No automated Git changes or publication',ci_policy='Manual local execution only',test_resource_cleanup='Caller owns demo directory; tests use memory only and temporary integration callers remove their root',checks={'offline':[check_command('scope-tests','test_access.py')],'regression':[check_command('paging-tests','test_paging.py')]})
    (root/'.engineering/project.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
    (root/'docs/README.md').write_text('# Teaching fixture knowledge\n\nOnly managed synthetic records are returned; empty scope returns nothing. Page size is normalized to 1..50. This is not production authorization or HTTP validation.\n')
    feature=root/'specs/changes/scoped-list';bugfix=root/'specs/changes/page-size'
    (feature/'spec.md').write_text('# Scoped synthetic list\nR-01 Only managed owner IDs appear.\nR-02 Empty scope returns no records.\nA-01/A-02 execute the two AccessTests.\nDesign: pure filtering, no persistence or public HTTP.\n')
    (bugfix/'spec.md').write_text('# Page-size bug fix\nR-01 Zero/negative sizes normalize to one, sizes over fifty normalize to fifty.\nReproduce with test_zero_and_negative_normalized, then repair and rerun.\nNo API, database or production changes.\n')
    # First establish a real failing regression, keep its failed evidence as historical facts.
    failed=run_checks(root,'regression','specs/changes/page-size/evidence','specs/changes/page-size/spec.md')
    if failed!=1:
        raise RuntimeError('bug reproduction did not fail as expected')
    (root/'src/paging.py').write_text('def page_size(value):\n    return max(1, min(value, 50))\n')
    completed=[]
    for directory,group,identifier,requirements in [(feature,'offline','scope-tests',[{'id':'R-01','text':'Return managed synthetic records only'},{'id':'R-02','text':'Empty scope returns no records'}]),(bugfix,'regression','paging-tests',[{'id':'R-01','text':'Normalize synthetic page sizes to 1..50'}])]:
        relative=str(directory.relative_to(root))
        if run_checks(root,group,relative+'/evidence',relative+'/spec.md'):
            raise RuntimeError('repaired teaching regression did not pass')
        records=[]
        for path in (directory/'evidence').glob('*.json'):
            data=json.loads(path.read_text())
            if data['result']=='passed':records.append((data['finished_at'],path))
        path=max(records)[1]
        trace={'schema_version':2,'id':directory.name,'level':'standard','status':'completed','spec':'spec.md','requirements':requirements,'tasks':[{'id':'T-01','requirements':[r['id'] for r in requirements],'status':'done'}],'acceptance':[{'id':'A-'+str(index+1).zfill(2),'requirements':[requirement['id']],'result':'passed','evidence':[{'kind':'automated','check_id':identifier,'path':str(path.relative_to(directory))}]} for index,requirement in enumerate(requirements)]}
        target=directory/'change.json';target.write_text(json.dumps(trace,ensure_ascii=False,indent=2))
        errors=trace_errors(target,root)
        if errors:raise RuntimeError('; '.join(errors))
        (directory/'acceptance.md').write_text('# Actual teaching acceptance\n\nCommands executed on synthetic data only. Structured evidence links appear in change.json. A completed record proves these fixture commands passed, not real HTTP/database/production security.\n')
        completed.append(str(target.relative_to(root)))
    print(json.dumps({'project':str(root),'completed_demo_changes':completed,'business_application':False},ensure_ascii=False))
    return root


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',type=Path,required=True);args=parser.parse_args()
    try:run_demo(args.destination)
    except (OSError,ValueError,RuntimeError) as error:
        print(str(error),file=sys.stderr);return 2
    return 0


if __name__=='__main__':sys.exit(main())
