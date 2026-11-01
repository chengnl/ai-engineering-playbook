#!/usr/bin/env python3
"""Offline Markdown file-link and limited requirement-trace validation, not business review."""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
from evidence import evidence_errors
from project_contract import load_profile, local_path, source_state, text

SKIP = {'.git', '.venv', 'node_modules', '__pycache__', 'var', 'output'}


def check_docs(root):
    root = Path(root).resolve()
    if not root.is_dir():
        return [f"document root missing: {root}"]
    errors = []
    for path in sorted(root.rglob('*.md')):
        if any(part in SKIP for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            errors.append(f"symbolic document skipped: {path}")
            continue
        text = re.sub(r'```.*?```', '', path.read_text(), flags=re.S)
        for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text):
            target = target.strip('<>')
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            if parts.path.startswith('/'):
                errors.append(f"non-portable absolute link: {path}: {target}")
                continue
            candidate = (path.parent / unquote(parts.path)).resolve()
            if not candidate.is_relative_to(root) or not candidate.exists():
                errors.append(f"missing/outside relative target: {path}: {target}")
    return errors


def trace_errors(path, project=None):
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        return [f"cannot read trace: {error}"]
    errors = []
    if not isinstance(data, dict):
        return ['trace must be an object']
    if type(data.get('schema_version')) is not int or data.get('schema_version') != 2:
        errors.append('unsupported schema_version')
    if not isinstance(data.get('id'), str) or not data['id'].strip():
        errors.append('change id is required')
    if not isinstance(data.get('level'), str) or data.get('level') not in {'simplified', 'standard', 'enhanced'}:
        errors.append('invalid level')
    statuses = {'draft', 'ready', 'implementing', 'blocked', 'completed'}
    if not isinstance(data.get('status'), str) or data.get('status') not in statuses:
        errors.append('invalid change status')

    def local_file(value):
        if not isinstance(value, str) or not value:
            return False
        try:
            return bool(local_path(path.parent, value))
        except (OSError, ValueError):
            return False

    if not local_file(data.get('spec')):
        errors.append('spec must reference an existing local file')
    rows = {}
    for key, prefix in [('requirements', 'R'), ('tasks', 'T'), ('acceptance', 'A')]:
        group = data.get(key)
        if not isinstance(group, list) or not group:
            errors.append(f'{key} must be a non-empty list')
            rows[key] = []
            continue
        ids = set()
        rows[key] = []
        for row in group:
            if not isinstance(row, dict):
                errors.append(f'{key}: row must be object')
                continue
            rid = row.get('id')
            if not isinstance(rid, str) or not re.fullmatch(prefix + r'-[0-9]+', rid):
                errors.append(f'{key}: invalid ID')
                continue
            if rid in ids:
                errors.append(f'{key}: duplicate {rid}')
            ids.add(rid)
            rows[key].append(row)
    requirements = {r['id'] for r in rows['requirements']}
    for r in rows['requirements']:
        if not isinstance(r.get('text'), str) or not r['text'].strip():
            errors.append(f"{r['id']}: empty requirement")
    covered = {'tasks': set(), 'acceptance': set()}
    for key in covered:
        for row in rows[key]:
            refs = row.get('requirements')
            if not isinstance(refs, list) or not refs or not all(isinstance(r, str) for r in refs):
                errors.append(f"{row['id']}: requirement references required")
                continue
            if not set(refs) <= requirements:
                errors.append(f"{row['id']}: unknown requirement")
            covered[key].update(refs)
        if requirements - covered[key]:
            errors.append(f'{key}: requirements without coverage: {sorted(requirements-covered[key])}')
    completed = data.get('status') == 'completed'
    expected_source = None
    if project is not None:
        try:
            expected_source = source_state(project, load_profile(project))
        except (OSError, ValueError, TypeError) as error:
            errors.append('project validation failed: ' + str(error))
    elif completed:
        errors.append('completed changes require --project for source/config binding')
    if data.get('status') in ['ready', 'implementing', 'completed']:
        for row in rows['requirements']:
            if not text(row.get('text')):
                errors.append(row['id'] + ': requirement is still a placeholder')
    spec_path = path.parent / data['spec'] if local_file(data.get('spec')) else None
    if spec_path and not spec_path.read_text().strip():
        errors.append('specification cannot be empty')
    for task in rows['tasks']:
        if not isinstance(task.get('status'), str) or task.get('status') not in {'todo', 'doing', 'blocked', 'done'}:
            errors.append(f"{task['id']}: invalid task status")
        if completed and task.get('status') != 'done':
            errors.append(f"{task['id']}: completed change has unfinished task")
    for acceptance in rows['acceptance']:
        result = acceptance.get('result')
        if not isinstance(result, str) or result not in {'not-run', 'passed', 'failed', 'skipped', 'blocked'}:
            errors.append(f"{acceptance['id']}: invalid result")
        evidence = acceptance.get('evidence')
        if not isinstance(evidence, list):
            errors.append(f"{acceptance['id']}: evidence must be list")
            continue
        if (completed or result == 'passed') and not evidence:
            errors.append(f"{acceptance['id']}: evidence required")
        if completed and result != 'passed':
            errors.append(f"{acceptance['id']}: completed change requires passed acceptance")
        for item in evidence:
            if not isinstance(item, dict) or item.get('kind') not in ['automated', 'manual'] or not local_file(item.get('path')):
                errors.append(f"{acceptance['id']}: structured local evidence reference required")
                continue
            record_path = path.parent / item['path']
            record_errors = evidence_errors(record_path, spec_path, expected_source)
            errors += [acceptance['id'] + ': ' + e for e in record_errors]
            try:
                record = json.loads(record_path.read_text())
                if record.get('kind') != item['kind'] or (item['kind'] == 'automated' and (not text(item.get('check_id')) or item.get('check_id') != record.get('command_id'))):
                    errors.append(acceptance['id'] + ': evidence kind/check ID mismatch')
            except (OSError, ValueError, AttributeError):
                pass
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docs', type=Path)
    parser.add_argument('--trace', type=Path)
    parser.add_argument('--project', type=Path, help='validate project readiness and bind completed evidence to current source scope')
    args = parser.parse_args()
    if not args.docs and not args.trace and not args.project:
        parser.error('provide --docs and/or --trace')
    errors = (check_docs(args.docs) if args.docs else []) + (trace_errors(args.trace, args.project) if args.trace else [])
    if args.project and not args.trace:
        try:
            load_profile(args.project)
        except (OSError, ValueError, TypeError) as error:
            errors.append(str(error))
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('PASS: requested structural checks only; business/semantic review not performed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
