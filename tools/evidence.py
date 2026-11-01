"""Evidence schema and binding checks; metadata is not a trusted signature."""
from datetime import datetime
import json
from pathlib import Path
import re
from project_contract import local_path, sha_file, text


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be text')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return stamp


def evidence_errors(path, spec, expected_source=None):
    try:
        if not Path(path).is_file() or not Path(path).read_text().strip():
            return ['evidence is empty or missing']
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return ['evidence must be a non-empty JSON record']
    if not isinstance(data, dict):
        return ['evidence must be an object']
    errors = []
    if type(data.get('schema_version')) is not int or data.get('schema_version') != 1:
        errors.append('unsupported evidence schema')
    if data.get('kind') not in ['automated', 'manual']:
        errors.append('invalid evidence kind')
    if data.get('result') != 'passed':
        errors.append('evidence did not pass')
    for key in ['run_id', 'purpose']:
        if not text(data.get(key)):
            errors.append('evidence ' + key + ' required')
    try:
        if timestamp(data.get('finished_at')) < timestamp(data.get('started_at')):
            errors.append('evidence time order invalid')
    except (ValueError, TypeError):
        errors.append('evidence timestamps invalid')
    environment = data.get('environment')
    if not isinstance(environment, dict) or environment.get('classification') not in ['test', 'development'] or not text(environment.get('label')):
        errors.append('evidence non-production environment required')
    source = data.get('source')
    if not isinstance(source, dict) or not text(source.get('revision')) or not isinstance(source.get('fingerprint'), str) or not re.fullmatch(r'[a-f0-9]{64}', source['fingerprint']):
        errors.append('evidence source binding required')
    elif expected_source and source['fingerprint'] != expected_source['fingerprint']:
        errors.append('evidence source/config fingerprint is stale')
    if not spec or data.get('spec_sha256') != sha_file(spec):
        errors.append('evidence specification binding is missing or stale')
    if data.get('kind') == 'automated':
        execution = data.get('execution')
        if not isinstance(execution, dict) or type(execution.get('returncode')) is not int or execution.get('returncode') != 0 or execution.get('result') != 'passed' or not isinstance(execution.get('argv'), list) or not execution.get('argv') or not all(isinstance(v, str) and v for v in execution['argv']):
            errors.append('automated evidence must record a successful actual command')
        if not text(data.get('command_id')):
            errors.append('automated evidence command_id required')
        resources = data.get('resources')
        if not isinstance(resources, dict) or resources.get('mode') not in ['none', 'isolated']:
            errors.append('evidence resource result required')
        elif resources['mode'] == 'isolated':
            for name in ['cleanup', 'residual_check']:
                outcome = resources.get(name)
                if not isinstance(outcome, dict) or outcome.get('result') != 'passed' or outcome.get('returncode') != 0:
                    errors.append('evidence resource ' + name + ' did not pass')
    if data.get('kind') == 'manual':
        if not text(data.get('reviewer')) or not text(data.get('observed')) or not isinstance(data.get('steps'), list) or not data['steps'] or not all(text(s) for s in data['steps']):
            errors.append('manual evidence needs reviewer, steps and observed result')
    return errors
