#!/usr/bin/env python3
"""Run reviewed local checks with bounded shutdown, resource hooks and structured evidence."""
import argparse
import json
from pathlib import Path
import signal
import sys
import uuid
from project_contract import load_profile, local_path, sha_file, source_state
from process_runner import execute, utc_now


def evidence_directory(project, relative, config):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or '\0' in relative:
        raise ValueError('evidence directory must be a relative project path')
    root = Path(project).resolve()
    raw = root / relative
    if any(p.is_symlink() for p in [raw, *raw.parents] if p != root and root in p.parents):
        raise ValueError('evidence directory may not use symbolic links')
    output = raw.resolve()
    if output == root or not output.is_relative_to(root):
        raise ValueError('evidence directory escapes project')
    for item in config['source_paths']:
        source = (root / item).resolve()
        if output == source or output.is_relative_to(source):
            raise ValueError('evidence output overlaps fingerprinted sources')
    if output.exists() and not output.is_dir():
        raise ValueError('evidence output is not a directory')
    return output


def run_checks(project, group, evidence_dir='var/check-evidence', spec=None):
    project = Path(project).resolve()
    config = load_profile(project)
    groups = config['checks']
    selected = list(groups) if group == 'all' else [group]
    commands = []
    for name in selected:
        items = groups.get(name)
        if not isinstance(items, list) or not items:
            if group == 'all' and isinstance(items, dict) and 'not_applicable_reason' in items:
                print('NOT_APPLICABLE group=' + name, flush=True)
                continue
            raise ValueError(str(name) + ': requested group is missing or not applicable')
        commands.extend((name, item) for item in items)
    if not commands:
        raise ValueError('no executable checks selected')
    output = evidence_directory(project, evidence_dir, config)
    spec_path = local_path(project, spec) if spec else None
    source = source_state(project, config)
    spec_digest = sha_file(spec_path) if spec_path else None
    output.mkdir(parents=True, exist_ok=True)
    for index, (name, command) in enumerate(commands, 1):
        print(f'RUN {index}/{len(commands)} group={name} id={command["id"]}', flush=True)
        record = {'schema_version': 1, 'kind': 'automated', 'run_id': str(uuid.uuid4()), 'command_id': command['id'], 'group': name, 'purpose': command['purpose'], 'source': source, 'spec_sha256': spec_digest, 'environment': config['environment']}
        execution = execute(command, project)
        record.update(execution=execution, started_at=execution['started_at'], finished_at=execution['finished_at'])
        resources = command['resources']
        outcome = {'mode': resources['mode']}
        # Always run both bounded hooks, including failed start/timeout/interruption.
        if resources['mode'] == 'isolated':
            outcome['ownership'] = resources['ownership']
            outcome['cleanup'] = execute(resources['cleanup'], project)
            outcome['residual_check'] = execute(resources['residual_check'], project)
        record['resources'] = outcome
        result = execution['result']
        if any(outcome.get(h, {}).get('result', 'passed') != 'passed' for h in ['cleanup', 'residual_check']):
            result = 'resource-cleanup-failed'
        if source_state(project, config)['fingerprint'] != source['fingerprint'] or (spec_path and sha_file(spec_path) != spec_digest):
            result = 'inputs-changed'
        record['result'] = result
        record['finished_at'] = utc_now()
        path = output / (command['id'] + '-' + record['run_id'] + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print('EVIDENCE ' + str(path.relative_to(project)), flush=True)
        if result != 'passed':
            print('FAIL: ' + result + '; review evidence and resource ownership', file=sys.stderr)
            return 124 if execution['result'] in ['timed-out', 'interrupted'] else 1
    print(f'PASS: {len(commands)} configured commands and declared resource checks passed; not a business approval')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--group', required=True)
    parser.add_argument('--evidence-dir', default='var/check-evidence')
    parser.add_argument('--spec', help='relative specification path, required for evidence used in completed changes')
    args = parser.parse_args()
    previous = signal.getsignal(signal.SIGTERM)
    def terminate(_signum, _frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, terminate)
    try:
        return run_checks(args.project, args.group, args.evidence_dir, args.spec)
    except (OSError, ValueError, TypeError) as error:
        print(f'Checks unavailable: {error}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 124
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    sys.exit(main())
